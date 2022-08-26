import uasyncio
import socket
import struct

SERVER_NAME = "UPnP/1.0" #placeholder

class Response:
    
    def __init__(self, msg = {}, uuid="", location = ""):
        self.msg = msg
        if location is not "": self.msg["LOCATION"] = location
        if uuid is not "": self.msg["USN"] = "uuid: %s" % usn
        if "SERVER" not in self.msg: msg["SERVER"] = SERVER_NAME
        if "CACHE-CONTROL" not in self.msg: self.msg["CACHE-CONTROL"] = "max-age=1800"
        if "ST" not in self.msg: self.msg["ST"] = "upnp:rootdevice" #placeholder
        
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
    
    def __init__(self, response=Response()):
        if type(response) is not Response:
            raise SSDP_Exception("Response type required")
        self.response = response
        
    async def listen(self):
        uasyncio.create_task(self.__listen())
        
    async def __listen(self):
        print("listenning")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            s = struct.pack("4s4s", self.SSDP_IP_BYTES, self.IP_BYTES)
            print("after struct %s" % struct)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, s)
            self.sock.bind((self.IP, self.SSDP_PORT))
            self.sock.settimeout(5)
            while True:
                try:
                    data, address = self.sock.recvfrom(1024)
                    self.__parse_response(data)
                    self.__send_response(address)
                except OSError as ose:
                    print(ose)
                except Exception as e:
                    raise e
                uasyncio.sleep_ms(1)
        except Exception as e:
            raise e
                    
    def __send_response(self, address):
        print("responding")
        print(self.response)
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_sock.sendto(self.response.to_bytes(), address)
        send_sock.close()
        
    def __parse_response(self, data):
        response = data.decode().split('\r\n')
#         print(response)
        
    
  
class SSDP_Exception(Exception):
    pass
