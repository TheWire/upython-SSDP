import uasyncio
import socket

SERVER_NAME = "UPnP/1.0" #placeholder

class Response:
    
    def __init___(self, msg = {}, uuid="", location = "", ):
        self.msg = msg
        if location is not "": self.msg["LOCATION"] = location
        if uuid is not "": self.msg["USN"] = "uuid: %s" % usn
        if "SERVER" not in self.msg: msg["SERVER"] = SERVER_NAME
        if "CACHE-CONTROL" not in self.msg: msg["CACHE-CONTROL"] = "max-age=1800"
        if "ST" not in self.msg: self.msg["ST"] = "upnp:rootdevice" #placeholder
        
    def __str__(self):
        str = "HTTP/1.1 200 OK\r\n"
        for key, value in self.msg:
            str += "%s: %s\r\n" % (key, value)
            
        str += "\r\n"
        return str

class SSDP_Server:
    
    IP = "192.168.0.37"
    SSDP_IP = "239.255.255.250"
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
            self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1) 
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, b'\xef\xff\xff\xfa\x00\x00\x00\x00')

            self.sock.bind((self.IP, self.SSDP_PORT))
            self.sock.settimeout(5)
            while True:
                try:
                    data, address = self.sock.recvfrom(1024)
                    print(data)
                    print("after data")
                    self.__parse_response(data)
                    self.__send_response(address)
                except Exception as e:
                    print(e)
                uasyncio.sleep_ms(1)
        except Exception as e:
            print(e)
                    
    def __send_response(self, address):
        print(self.response)
        self.sock.sendto(bytes(self.response), address)
        self.sock.close()
        
    def __parse_response(self, data):
        response = data.decode().split('\r\n')
        print(response)
        
    
  
class SSDP_Exception(Exception):
    pass
