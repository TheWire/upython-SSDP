import os
try:
    from micropython import const
    upython = True
except:
    upython = False
    
if upython:
    os.uname().sysname
    import uasyncio as asyncio
    class TimeoutError(Exception):
        pass
else:
    import asyncio
    
import socket
import struct
import re
import errno

SSDP_IP = "239.255.255.250"
SSDP_PORT = 1900

SERVER_NAME = "uPython-SSDP UPnP/2.0"
DEVICE_PROFILE = """
<root xmlns="urn:schemas-upnp-org:device-1-0">
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <device>
        <friendlyName>My SSDP Device</friendlyName>
        <manufacturer>My Name</manufacturer>
        <modelName>Device MK1</modelName>
        <modelNumber>1</modelNumber>
    </device>
</root>   
"""

class Device_Config:
    
    def __init__(self, msg = {}, uuid="", urn="MyDevice", ip="127.0.0.1",
     tcp_server_enabled=True, tcp_location=None, port=80, device_profile=None, device_profile_path=None):
        self.ip = ip
        self.tcp_server_enabled = tcp_server_enabled
        self.port = port
        self.msg = msg
        self.urn = urn
        self.device_profile = device_profile
        self.device_profile_path = device_profile_path
        if device_profile_path is not None and self.__path_exists(device_profile_path):
            self.device_profile_path = device_profile_path
        elif device_profile is not None:
            self.device_profile = device_profile
        else:
            self.device_profile = DEVICE_PROFILE
        
        self.msg["HOST"] = f"{SSDP_IP}:{SSDP_PORT}"
        if tcp_server_enabled:
             self.msg["LOCATION"] = f"http://{ip}:{port}/device.xml"
        elif not tcp_server_enabled and tcp_location:
            self.msg["LOCATION"] = tcp_location
        else:
            self.msg["LOCATION"] = f"http://{ip}:{port}"
        if uuid != "":
            self.msg["USN"] = f"uuid:{uuid}::{urn}"
        else:
            self.msg["USN"] = f"{urn}"
        self.msg["SERVER"] = SERVER_NAME
        self.msg["CACHE-CONTROL"] = "max-age=1800"
        self.msg["ST"] = self.urn
    
        
    def __path_exists(self, path):
        try:
            file = open(path)
        except:
            print("unable to open device profile file")
            return False
        return True
        
    def message(self, type="MULTICAST"):
        if type == "MULTICAST":
            str = "NOTIFY * HTTP/1.1\r\n"
        elif type == "UNICAST":
            str = "HTTP/1.1 200 OK\r\n"
        else:
            raise(SSDP_Exception("invalid cast type argument"))
        for key, value in self.msg.items():
            if key == "HOST" and type == "UNICAST": continue
            str += "%s: %s\r\n" % (key, value)
            
        str += "\r\n"
        return str.encode('ASCII')


class SSDP_Server:
    
    IP = "0.0.0.0"
    IP_BYTES = b'\x00\x00\x00\x00'
    SSDP_IP_BYTES = b'\xef\xff\xff\xfa'
    
    def __init__(self, device_config=Device_Config()):
        if type(device_config) is not Device_Config:
            raise SSDP_Exception("Device_Config type required")
        self.device_config = device_config
        self.ip = device_config.ip
        self.tcp_port = device_config.port
        self.__listen_task = None
        self.__broadcast_task = None
        
    async def listen(self):
        if self.__listen_task != None:
            raise SSDP_Exception("ssdp server already started")
        self.__listen_task = asyncio.create_task(self.__listen())
        if self.device_config.tcp_server_enabled:
            self.__tcp_server = await asyncio.start_server(self.__serve_device_profile, host = self.IP, port = self.tcp_port)
        print("SSDP server started")

    async def broadcast(self, interval=5):
        if self.__broadcast_task != None:
            raise SSDP_Exception("ssdp broadcast already started")
        self.__broadcast_task = asyncio.create_task(self.__broadcast(interval))

    async def stop_listen(self):
        if self.__listen_task:
            self.__listen_task.cancel()
            self.__listen_task = None

    async def stop_broadcast(self):
        if self.__broadcast_task:
            self.__broadcast_task.cancel()
            self.__broadcast_task = None

    async def stop_tcp_server(self):
        if self.device_config.tcp_server_enabled:
            self.__tcp_server.close()
            await self.__tcp_server.wait_closed()


    async def stop(self):
        self.stop_listen()
        self.stop_tcp_server()
        self.stop_broadcast()

    async def __broadcast(self, interval=5):
        while True:
            self.__send_multicast()
            await asyncio.sleep(interval)
        
    async def __listen(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s = struct.pack("4s4s", self.SSDP_IP_BYTES, self.IP_BYTES)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, s)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.IP, SSDP_PORT))
        self.sock.settimeout(0.1)
        while True:
            try:
                data, address = self.sock.recvfrom(1024)
                if self.__parse_request(data):
                    self.__send_response(address)
            except TimeoutError:
                pass
            except OSError as ose:
                if ose.errno != errno.ETIMEDOUT and str(ose) != "timed out":                  
                    print(ose)
                    raise(ose)
            await asyncio.sleep(0.05)
        
    async def __serve_device_profile(self, reader, writer):
        read = await reader.read(1024)
        writer.write(b"HTTP/1.0 200 OK\r\n")
        writer.write(b"Content-Type: application/xml\r\n\r\n")
        if self.device_config.device_profile_path is not None:
            file = open(self.device_config.device_profile_path)
            writer.write(file.read())
        else:
            writer.write(bytes(self.device_config.device_profile, "utf-8"))

        await writer.drain()
        writer.close()
        await writer.wait_closed()


    def __send_response(self, address):
        self.__send_multicast()
        self.__send_unicast(address)
                    
    def __send_multicast(self):
        #multicast
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s = struct.pack("4s4s", self.SSDP_IP_BYTES, self.IP_BYTES)
        send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, s)
        send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        send_sock.sendto(self.device_config.message(type="MULTICAST"), (SSDP_IP, SSDP_PORT))
        send_sock.close()

    def __send_unicast(self, address):
        #unicast
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_sock.sendto(self.device_config.message(type="UNICAST"), address)
        send_sock.close()
        
    def __parse_request(self, data):
        request = data.decode().split("\r\n")
        if len(request) < 3: return False
        if re.match("^(M\-SEARCH)", request[0]) is None: return False
        headers = {}
        for line in request[1:]:
            parts = line.split(":", 1)
            if len(parts) == 2:
                headers[parts[0].upper()] = parts[1].strip()  
        if ("MAN", '"ssdp:discover"') not in headers.items():
            return False
        if headers['ST'] is None:
            return False
        elif headers['ST'] != "ssdp:all" and headers['ST'] != self.device_config.urn:
            return False
        return True
        
    
  
class SSDP_Exception(Exception):
    pass

