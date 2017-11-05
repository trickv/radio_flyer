#!/usr/bin/env python

import time
import smbus

BUS = None
I2C_ADDRESS = 0x42
DEBUG = True

# Sources:
# http://ava.upuaut.net/?p=768
# https://stackoverflow.com/questions/28867795/reading-i2c-data-from-gps
# https://github.com/tuupola/micropython-gnssl76l/blob/master/gnssl76l.py


def connect_bus():
    global BUS
    BUS = smbus.SMBus(1)

def initialize_ublox(i2c_address):
    """
    None of this code works for me.
    I ended up having to initialize the GPS over serial, as writes
    to i2c seem to be ignored. I must be doing it wrong.
    """
    disable_template = "PUBX,40,%s,0,0,0,0"
    messages_disable = [
        "GLL",
        "GSA",
        "RMC",
        "GSV",
        "VTG",
    ]
    for message in messages_disable:
        disable_command = disable_template % message
        checksum_int = 0
        for character in disable_command:
            checksum_int ^= ord(character)
        disable_command = "$%s*%x" % (disable_command, checksum_int)
        print("Sending command: %s" % disable_command)
        _send_command_string_bitwise(i2c_address, disable_command)

def _send_command_string_bitwise(i2c_address, message):
    message = [ord(i) for i in message]
    message.append(10)
    for current in message:
        BUS.write_byte(i2c_address, current)
    time.sleep(1)

def _send_command_string(i2c_address, message):
    message = [ord(i) for i in message]
    message.append(10)
    chunks = []
    while message:
        chunks.append(message[:16])
        message = message[16:]
    position = 0
    for chunk in chunks:
        fop = ''.join(chr(byte) for byte in chunk)
        print("sending chunk (len %d): %s" % (len(chunk), fop))
        BUS.write_i2c_block_data(i2c_address, position, chunk)
        position += len(chunk)
    time.sleep(1)


def _serenity_hack_initialize_ublox(i2c_address):
    # following is from https://github.com/Chetic/Serenity/blob/master/Serenity.py#L13
    set_nmea_off = bytearray.fromhex("B5 62 06 00 14 00 01 00 00 00 D0 08 00 00 80 25 00 00 07 00 01 00 00 00 00 00 A0 A9")
    set_nmea_off = list(set_nmea_off)
    chunks = []
    while set_nmea_off:
        chunks.append(set_nmea_off[:16])
        set_nmea_off = set_nmea_off[16:]
    position = 0
    for chunk in chunks:
        fop = ''.join(chr(byte) for byte in chunk)
        print("sending chunk (len %d(: %s" % (len(chunk), fop))
        BUS.write_i2c_block_data(i2c_address, position, chunk)
        position += len(chunk)


def configure_example():
    connect_bus()
    initialize_ublox(I2C_ADDRESS)

if __name__ == "__main__":
    configure_example()
