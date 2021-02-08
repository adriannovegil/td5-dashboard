import os
import sys
import time
from pyftdi.ftdi import Ftdi
import pyftdi.serialext

serial_port = 'ftdi://ftdi:232:A50285BI/1'
interframe_delay=0.01
debug = 5;

def fast_init():
    # Open a serial port on the second FTDI device interface (IF/2) @ 3Mbaud
    port = pyftdi.serialext.serial_for_url(serial_port, baudrate=300, timeout=0.1)
    command=b"\x00"
    port.write(command) #Send a 25ms pulse
    time.sleep(0.05)
    port.close()

def send_packet(data, res_size):
    global debug
    time.sleep(interframe_delay)

    lendata=len(data)

    modulo=0
    for i in range(0,lendata):
        modulo = modulo + data[i]
    modulo = modulo % 256

    to_send = data + bytes(modulo)
    port.write(to_send)
    time.sleep(interframe_delay)

    ignore = len(to_send)
    read_val = port.read(len(to_send) + res_size)

    read_val_s = read_val[0:ignore]
    if debug > 2:
        sys.stdout.write("Data Sent: %s." % ":".join("{:02x}".format(c) for c in read_val_s))
    read_val_r = read_val[ignore:]
    if debug > 2:
        sys.stdout.write("Data Received: %s." % ":".join("{:02x}".format(c) for c in read_val_r))

    modulo=0
    for i in range(0,len(read_val_r)-1):
        modulo = modulo + ord(read_val_r[i])
    modulo = modulo % 256

    if (len(read_val_r)>2):
        if (modulo!=ord(read_val_r[len(read_val_r)-1])): #Checksum error
            read_val_r=""
            if debug > 1:
                sys.stdout.write("Checksum ERROR")

    return read_val_r

os.system("clear")
sys.stdout.write("")
sys.stdout.write("")
sys.stdout.write("\t\t Land Rover Td5 Storm - Dignostic tool")
sys.stdout.write("")
sys.stdout.write("niting...")

Ftdi.show_devices()

fast_init()

port = pyftdi.serialext.serial_for_url(serial_port, baudrate=10400, timeout=0.1) #CP210x must be configured for

time.sleep(0.1)
response=send_packet(b"\x81\x13\xF7\x81",5)         #Init Frame
time.sleep(0.1)
response=send_packet(b"\x02\x10\xA0",3)             #Start Diagnostics
time.sleep(0.1)
response=send_packet(b"\x02\x27\x01",6)             #Seed Request

if (len(response)==6):
    key_ans=seed_key(response)
    response=send_packet(key_ans,4)                 #Seed Request

time.sleep(0.1)
response=send_packet(b"\x02\x21\x02",15)            #Start Diagnostics

time.sleep(2)

#Start requesting data

ser.close()
