import os
import sys
import time
from pyftdi.ftdi import Ftdi
import pyftdi.serialext

serial_port = "ftdi://ftdi:232:A50285BI/1"
interframe_delay = 0.01
debug = 5

rpm = 0


def fast_init():
    # Open a serial port on the second FTDI device interface (IF/2) @ 3Mbaud
    port = pyftdi.serialext.serial_for_url(serial_port, baudrate=300, timeout=0.1)
    command = b"\x00"
    port.write(command)  # Send a 25ms pulse
    time.sleep(0.05)
    port.close()


def send_packet(data, res_size):
    global debug
    time.sleep(interframe_delay)

    lendata = len(data)

    modulo = 0
    for i in range(0, lendata):
        modulo = modulo + data[i]
    modulo = modulo % 256

    to_send = data + bytes(modulo)
    port.write(to_send)
    time.sleep(interframe_delay)

    ignore = len(to_send)
    read_val = port.read(len(to_send) + res_size)

    read_val_s = read_val[0:ignore]
    if debug > 2:
        print("Data Sent: %s." % ":".join("{:02x}".format(c) for c in read_val_s))
    read_val_r = read_val[ignore:]
    if debug > 2:
        print("Data Received: %s." % ":".join("{:02x}".format(c) for c in read_val_r))

    modulo = 0
    for i in range(0, len(read_val_r) - 1):
        modulo = modulo + ord(read_val_r[i])
    modulo = modulo % 256

    if len(read_val_r) > 2:
        if modulo != ord(read_val_r[len(read_val_r) - 1]):  # Checksum error
            read_val_r = ""
            if debug > 1:
                print("Checksum ERROR")

    return read_val_r


def seed_key(read_val_r):
    seed = read_val_r[3:5]
    if debug > 1:
        print("\tSeed is: %s." % ":".join("{:02x}".format(ord(c)) for c in seed))

    seed_int = ord(seed[0]) * 256 + ord(seed[1])
    if debug > 1:
        print("\tSeed integer: %s." % seed_int)

    seed = seed_int

    count = (
        (seed >> 0xc & 0x8) + (seed >> 0x5 & 0x4) + (seed >> 0x3 & 0x2) + (seed & 0x1)
    ) + 1

    idx = 0
    while idx < count:
        tap = ((seed >> 1) ^ (seed >> 2) ^ (seed >> 8) ^ (seed >> 9)) & 1
        tmp = (seed >> 1) | (tap << 0xf)
        if (seed >> 0x3 & 1) and (seed >> 0xd & 1):
            seed = tmp & ~1
        else:
            seed = tmp | 1

        idx = idx + 1

    if seed < 256:
        high = 0x00
        low = seed
    else:
        high = seed / 256
        low = seed % 256

    key = chr(high) + chr(low)
    if debug > 1:
        print("\tKey hex: %s." % ":".join("{:02x}".format(ord(c)) for c in key))

    key_answer = b"\x04\x27\x02" + key

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

port = pyftdi.serialext.serial_for_url(
    serial_port, baudrate=10400, timeout=0.1
)  # CP210x must be configured for

time.sleep(0.1)
response = send_packet(b"\x81\x13\xF7\x81", 5)  # Init Frame
time.sleep(0.1)
response = send_packet(b"\x02\x10\xA0", 3)  # Start Diagnostics
time.sleep(0.1)
response = send_packet(b"\x02\x27\x01", 6)  # Seed Request

if len(response) == 6:
    key_ans = seed_key(response)
    response = send_packet(key_ans, 4)  # Seed Request

time.sleep(0.1)
response = send_packet(b"\x02\x21\x02", 15)  # Start Diagnostics

time.sleep(2)

# Start requesting data
# Start requesting data
while True:
    os.system("clear")
    print("\t\t Td5 Storm")
    print(" ")
    rpm = get_rpm()
    print("\t RPM: ", str(rpm))

port.close()
