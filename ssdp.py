import uasyncio
import socket
import struct
import re
import errno

SERVER_NAME = "UPnP/1.0" #placeholder
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


class Response:
    
    def __init__(self, msg = {}, uuid="", device_profile=None, device_profile_path=None):
        self.ip = '0.0.0.0'
        self.port = 80
        self.msg = msg
        self.set_location(self.ip, self.port)
        self.device_profile = device_profile
        self.device_profile_path = device_profile_path
        if device_profile_path is not None and self.__path_exists(device_profile_path):
            self.device_profile_path = device_profile_path
        elif device_profile is not None:
            self.device_profile = device_profile
        else:
            self.device_profile = DEVICE_PROFILE
        
        
        if uuid is not "": self.msg["USN"] = "uuid: %s" % uuid
        if "SERVER" not in self.msg: msg["SERVER"] = SERVER_NAME
        if "CACHE-CONTROL" not in self.msg: self.msg["CACHE-CONTROL"] = "max-age=1800"
        if "ST" not in self.msg: self.msg["ST"] = "upnp:rootdevice" #placeholder
    
    def set_location(self, ip, port):
        self.msg["LOCATION"] = "http://%s:%d/device.xml" % (ip, port)
        
    def set_port(self, port):
        self.port = port
        self.set_location(self.ip, self.port)
        
    def set_ip(self, ip):
        self.ip = ip
        self.set_location(self.ip, self.port)
        
    def __path_exists(self, path):
        try:
            file = open(path)
        except:
            print("unable to open device profile file")
            return False
        return True
        
    def __str__(self):
        str = "HTTP/1.1 200 OK\r\n"
        for key, value in self.msg.items():
            str += "%s: %s\r\n" % (key, value)
            
        str += "\r\n"
        return str
    
    def to_bytes(self):
        return self.__str__().encode('ASCII')

class SSDP_Server:
    
    IP = "0.0.0.0"
    IP_BYTES = b'\x00\x00\x00\x00'
    SSDP_IP = "239.255.255.250"
    SSDP_IP_BYTES = b'\xef\xff\xff\xfa'
    SSDP_PORT = 1900
    
    def __init__(self, ip, response=Response(), tcp_port=80):
        if type(response) is not Response:
            raise SSDP_Exception("Response type required")
        self.response = response
        self.ip = ip
        self.tcp_port = tcp_port
        self.response.set_port(tcp_port)
        self.response.set_ip(self.ip)
        
    async def listen(self):
        uasyncio.create_task(self.__listen())
        await uasyncio.start_server(self.__serve_device_profile, host = self.IP, port = self.tcp_port)
        print("SSDP server started")
        while True:
            await uasyncio.sleep_ms(500)
        
    async def __listen(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s = struct.pack("4s4s", self.SSDP_IP_BYTES, self.IP_BYTES)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, s)
        self.sock.bind((self.IP, self.SSDP_PORT))
        self.sock.settimeout(5)
        while True:
            try:
                data, address = self.sock.recvfrom(1024)
                if self.__parse_response(data):
                    self.__send_response(address)
            except OSError as e:
                if e.errno != errno.ETIMEDOUT:
                    raise(e)
            await uasyncio.sleep_ms(50)
        
    async def __serve_device_profile(self, reader, writer):
        read = await reader.read(1024)
        writer.write("HTTP/1.0 200 OK\r\n")
        writer.write("Content-Type: application/xml\r\n\r\n")
        if self.response.device_profile_path is not None:
            file = open(self.response.device_profile_path)
            writer.write(file.read())
        else:
            writer.write(self.response.device_profile)

        await writer.drain()
        writer.close()
        await writer.wait_closed()
            
                    
    def __send_response(self, address):
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_sock.sendto(self.response.to_bytes(), address)
        send_sock.close()
        
    def __parse_response(self, data):
        response = data.decode().split("\r\n")
        if len(response) < 3: return False
        if re.match("^(M\-SEARCH)", response[0]) is None: return False
        headers = {}
        for line in response[1:]:
            parts = line.split(":", 1)
            if len(parts) == 2:
                headers[parts[0].upper()] = parts[1].strip()  
        if ("MAN", '"ssdp:discover"') not in headers.items():
            return False
        if headers['ST'] is None:
            return False
        elif headers['ST'] != "ssdp:all" and headers['ST'] != "upnp:rootdevice":
            return False
        return True
        
    
  
class SSDP_Exception(Exception):
    pass
