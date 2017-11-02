#!/usr/bin/env python

import time
import smbus
import pynmea2
# TODO: might want to try smbus2? https://github.com/kplindegaard/smbus2/

BUS = None
I2C_ADDRESS = 0x42
GPS_READ_INTERVAL = 0.1
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
        "GSV",
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


def read_gps(i2c_address):
    response_bytes = []
    gibberish = False
    while True:
        byte = BUS.read_byte(i2c_address)
        if byte == 255:
            return False
        elif byte > 126: # TODO: This (for me) is a symptom of i2c bus problems. Throw?
            print("Unprintable char int={0}, chr={1}".format(byte, chr(byte)))
            gibberish = True
        elif byte == 10: # new line character
            break
        else:
            response_bytes.append(byte)
    if gibberish:
        print("Not returning gibberish")
        return False
    response_chars = ''.join(chr(byte) for byte in response_bytes)
    print("LINE: %s" % response_chars)
    msg = pynmea2.parse(response_chars, check=True)
    return(msg)

def __read_gps_i2c_blockread(i2c_address):
    """
    This should perform better and worked in some of my tests, but seems to be throwing
    a lot more I/O errors now. So use read_gps instead, which reads 1 byte at a time.
    """
    response_bytes = []
    while True: # Newline, or bad char.
        block = BUS.read_i2c_block_data(i2c_address, 0, 16)
        last_byte = block[-1]
        if last_byte == 255:
            return False
        elif last_byte > 126: # TODO: This (for me) is a symptom of i2c bus problems. Throw?
            print("Unprintable char int={0}, chr={1}".format(last_byte, chr(last_byte)))
            return False
        elif last_byte == 10: # new line character
            break
        else:
            response_bytes = response_bytes + block
    response_chars = ''.join(chr(byte) for byte in response_bytes)
    print("LINE: %s" % response_chars)
    msg = pynmea2.parse(response_chars, check=True)
    return(msg)

def simple_read_demo():
    connect_bus()
    #initialize_ublox(I2C_ADDRESS)
    while True:
        gps_location = read_gps(I2C_ADDRESS)
        if gps_location:
            print(gps_location)
        else:
            print("Sleep 0.1")
            time.sleep(GPS_READ_INTERVAL)

if __name__ == "__main__":
    simple_read_demo()
