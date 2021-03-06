import os
import sys
import time
from pyftdi.ftdi import Ftdi
import pyftdi.serialext
import binascii

MAX_ATTEMPTS = 5
ATTEMPT_DELAY = 3  # 2s

serial_port = "ftdi://ftdi:232:A50285BI/1"
connected = False
interframe_delay = 0.01
debug = 5

b_voltage = 0
rpm = 0
rpm_error = 0


def pause(delay, step_size):
    """Pause"""
    end_time = time.monotonic() + delay
    while time.monotonic() <= end_time:
        time.sleep(step_size)


def open_uart_connection():
    """Open the UART connection"""
    port = pyftdi.serialext.serial_for_url(serial_port, baudrate=360, timeout=0.1)
    # port = pyftdi.serialext.serial_for_url(serial_port, baudrate=300, timeout=0.1)
    command = b"\x00"
    port.write(command)  # Send a 25ms pulse
    time.sleep(0.025)
    port.close()
    port = None


def open_ecu_connection():
    """Init ECU connection"""
    global port
    global connected

    attempt = 0

    port = pyftdi.serialext.serial_for_url(serial_port, baudrate=10400, timeout=0.1)
    while attempt < MAX_ATTEMPTS:
        # >> 81 13 F7 81 0C
        # << 81 13 F7 81 0C 03 C1 57 8F AA
        # >> 02 10 A0 B2
        # << 02 10 A0 B2 01 50 51
        # >> 02 27 01 2A
        time.sleep(0.1)
        response = send_packet(b"\x81\x13\xF7\x81\x0C", 7)  # Init Frame
        time.sleep(0.1)
        response = send_packet(b"\x02\x10\xA0\xB2", 3)  # Start Diagnostics
        time.sleep(0.1)
        response = send_packet(b"\x02\x27\x01\x2A", 6)  # Seed Request

        if len(response) == 6:
            key_ans = seed_key(response)
            time.sleep(0.1)
            response = send_packet(key_ans, 4)  # Seed Request
            if len(response) == 4:
                connected = True

        if connected:
            break
        pause(ATTEMPT_DELAY, 0.01)
        attempt += 1

    # fast_init failed
    if not connected:
        port.close()
        port = None


def start_ecu_logger():
    """Start ECU logger"""

    time.sleep(0.1)
    response = send_packet(b"\x02\x21\x20", 15)  # Start Diagnostics

    # Start requesting data
    # Start requesting data
    while True:
        os.system("clear")
        print("")
        print("")
        print("\t\t Land Rover Td5 - Dignostic tool")
        print(" ")
        print("\t Battery voltage: ", str(b_voltage), " Volt")
        print("\t RPM: ", str(rpm))
        print("\t RPM Error: ", str(rpm_error))
        b_voltage = get_bvolt()
        rpm = get_rpm()
        rpm_error = get_rpm_error()

def send_packet(data, res_size):
    """Send packet to the ECU"""
    global debug
    time.sleep(interframe_delay)

    lendata = len(data)

    modulo = 0
    for i in range(0, lendata):
        modulo = modulo + data[i]
    modulo = modulo % 256

    to_send = data + chr(modulo).encode("latin1")
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
        if modulo != read_val_r[len(read_val_r) - 1]:  # Checksum error
            read_val_r = ""
            if debug > 1:
                print("Checksum ERROR")

    return read_val_r


def seed_key(read_val_r):
    seed = read_val_r[3:5]
    if debug > 1:
        print(("\tSeed is: %s." % binascii.b2a_hex(seed)))
    seed_int = seed[0] * 256 + seed[1]
    if debug > 1:
        print(("\tSeed integer: %s." % seed_int))

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

    key = chr(int(high)).encode("latin1") + chr(int(low)).encode("latin1")
    if debug > 1:
        print(("\tKey hex: %s." % binascii.b2a_hex(key)))

    key_answer = (
        b"\x04\x27\x02"
        + chr(int(high)).encode("latin1")
        + chr(int(low)).encode("latin1")
    )

    return key_answer


def get_rpm():
    global rpm
    response = send_packet(b"\x02\x21\x09", 6)
    # response = send_packet(b"\x02\x21\x09\x00", 6)
    if len(response) < 6:
        # rpm=0
        i = 0
    else:
        rpm = response[3] * 256 + response[4]
    return rpm


def get_rpm_error():
    global rpm_error
    response = send_packet(b"\x02\x21\x21", 6)
    # response = send_packet(b"\x02\x21\x21\x00", 6)
    if len(response) < 6:
        # rpm=0
        i = 0
    else:
        rpm_error = response[3] * 256 + response[4]

    if rpm_error > 32768:
        rpm_error = rpm_error - 65537
    return rpm_error


def get_bvolt():
    global b_voltage
    response = send_packet(b"\x02\x21\x10", 8)
    # response = send_packet(b"\x02\x21\x10\x00", 8)
    if len(response) < 8:
        # b_voltage=0
        i = 0
    else:
        b_voltage = response[3] * 256 + response[4]
        b_voltage = float(b_voltage) / 1000

if __name__ == "__main__":
    """Main function"""
    
    os.system("clear")
    print("")
    print("")
    print("\t\t Land Rover Td5 - Dignostic tool")
    print("")
    print("Initing...")

    Ftdi.show_devices()

    open_uart_connection()
    open_ecu_connection()
    start_ecu_logger()
