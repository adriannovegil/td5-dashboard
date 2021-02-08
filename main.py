import os
import sys
import time
from pyftdi.ftdi import Ftdi
import pyftdi.serialext
import binascii

serial_port = "ftdi://ftdi:232:A50285BI/1"
interframe_delay = 0.01
debug = 5

rpm = 0


def fast_init():
    port = pyftdi.serialext.serial_for_url(serial_port, baudrate=360, timeout=0.1)
    #port = pyftdi.serialext.serial_for_url(serial_port, baudrate=300, timeout=0.1)
    command = b"\x00"
    port.write(command)  # Send a 25ms pulse
    time.sleep(0.025)
    port.close()


def send_packet(data, res_size):
    global debug
    time.sleep(interframe_delay)

    lendata = len(data)

    modulo = 0
    for i in range(0, lendata):
        modulo = modulo + data[i]
    modulo = modulo % 256

    to_send=data+chr(modulo).encode('latin1')
    port.write(to_send)
    time.sleep(interframe_delay)

    ignore = len(to_send)
    read_val = port.read(len(to_send) + res_size)

    read_val_s = read_val[0:ignore]
    if debug > 2:
        print(("Data Sent: %s." % binascii.b2a_hex(read_val_s)))
    read_val_r = read_val[ignore:]
    if debug > 2:
        print(("Data Received: %s." % binascii.b2a_hex(read_val_r)))

    modulo = 0
    for i in range(0, len(read_val_r) - 1):
        modulo = modulo + read_val_r[i]
    modulo = modulo % 256

    if len(read_val_r) > 2:
        if (modulo!=read_val_r[len(read_val_r)-1]): #Checksum error
            read_val_r = ""
            if debug > 1:
                print("Checksum ERROR")

    return read_val_r


def seed_key(read_val_r):
    seed = read_val_r[3:5]
    if debug > 1:
        print(("\tSeed is: %s." % binascii.b2a_hex(seed)))
    seed_int=seed[0]*256+seed[1]
    if debug > 1:
        print(("\tSeed integer: %s." % seed_int))

    seed=seed_int

    count = ((seed >> 0xC & 0x8) + (seed >> 0x5 & 0x4) + (seed >> 0x3 & 0x2) + (seed & 0x1)) + 1

    idx = 0
    while (idx < count):
            tap = ((seed >> 1) ^ (seed >> 2 ) ^ (seed >> 8 ) ^ (seed >> 9)) & 1
            tmp = (seed >> 1) | ( tap << 0xF)
            if (seed >> 0x3 & 1) and (seed >> 0xD & 1):
                    seed = tmp & ~1
            else:
                    seed = tmp | 1

            idx = idx + 1

    if (seed<256):
        high=0x00
        low=seed
    else:
        high=seed/256
        low=seed%256

    key=chr(int(high)).encode('latin1')+chr(int(low)).encode('latin1')
    if debug > 1:
        print(("\tKey hex: %s." % binascii.b2a_hex(key)))

    key_answer=b"\x04\x27\x02"+chr(int(high)).encode('latin1')+chr(int(low)).encode('latin1')

    return key_answer


def get_rpm():
    global rpm
    response = send_packet(b"\x02\x21\x09", 6)
    if len(response) < 6:
        # rpm=0
        i = 0
    else:
        rpm = ord(response[3]) * 256 + ord(response[4])

    return rpm


os.system("clear")
print("")
print("")
print("\t\t Land Rover Td5 Storm - Dignostic tool")
print("")
print("Initing...")

Ftdi.show_devices()

fast_init()

port = pyftdi.serialext.serial_for_url(serial_port, baudrate=10400, timeout=0.1)

if debug > 2:
    print("Init Frame")
time.sleep(0.1)
response = send_packet(b"\x81\x13\xF7\x81", 5)  # Init Frame

if debug > 2:
    print("Start Diagnostics")
time.sleep(0.1)
response = send_packet(b"\x02\x10\xA0", 3)  # Start Diagnostics

if debug > 2:
    print("Seed Request I")
time.sleep(0.1)
response = send_packet(b"\x02\x27\x01", 6)  # Seed Request

if (len(response)==6):
    if debug > 2:
        print("Seed Request II")
    key_ans = seed_key(response)
    response = send_packet(key_ans, 4)  # Seed Request

if debug > 2:
    print("Start Diagnostics")
time.sleep(0.2)

time.sleep(0.1)
response=send_packet(b"\x02\x21\x20",15)             #Start Diagnostics
#response = send_packet(b"\x02\x21\x02", 15)         # Start Diagnostics
#response=send_packet(b"\x02\x3e\x01",3)             #Start outputs

time.sleep(0.5)

# Start requesting data
# Start requesting data
while True:
    os.system("clear")
    print("\t\t Td5 Storm")
    print(" ")
    print("\t RPM: ", str(rpm))
    rpm = get_rpm()
    #time.sleep(0.5)

port.close()
