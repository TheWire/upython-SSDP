# Micropython Library for Simple Service Detection Protocol (SSDP)

Library to allow Micropython device to be automatically found using the
Simple Service Detection Protocol (SSDP) which is part of Universal Plug and Play (UPnP). Listens for multicast on 239.255.255.250 port 1900.

Tested on ESP32. Raspberry Pi Pico W currently not supported due to limitation of Micropython on that device.

## Example Usage
```
import ssdp
import uasyncio

def main_loop(server):
    await server.listen()
    while True:
        await uasyncio.sleep(1)

server = ssdp.SSDP_Server()
uasyncio.run(main_loop(server))
```

## Configuration

ssdp server can be passed a Device_Config argument

```
ssdp.SSDP_Server(Device_Config())
```

#### Example Config

```
Device_Config(
    msg = {}, # ssdp response message
    uuid="", # unique id for your device
    urn="MyDevice", #you device name used for detection
    # Config TCP device profile server
    ip="127.0.0.1",
    port=80, 
    device_profile="", # XML device profile string
    device_profile_path="device_profile.xml" # alternate path to device profile xml file
)
```

