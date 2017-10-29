#!/usr/bin/env python

import time
import json
import smbus
# TODO: pynmea2 parses NMEA strings: https://github.com/Knio/pynmea2/
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
        fop = ''.join(unichr(byte) for byte in chunk)
        print("sending chunk (len %d(: %s" % (len(chunk), fop))
        BUS.write_i2c_block_data(i2c_address, position, chunk)
        position += len(chunk)

def parse_response(gps_chars):
    if DEBUG:
        print("LINE: %s" % gps_chars)
    if "*" not in gps_chars:
        return False

    star_split = gps_chars.split('*')
    if len(star_split) != 2:
        emsg = "too many stars: %s" % gps_chars
        raise Exception(emsg)
    gps_str, chk_sum = star_split
    gps_components = gps_str.split(',')
    gps_start = gps_components[0]
    gps_data = {
        'strType': None,
        'fixTime': None,
        'lat': None,
        'latDir': None,
        'lon': None,
        'lonDir': None,
        'fixQual': None,
        'numSat': None,
        'horDil': None,
        'alt': None,
        'altUnit': None,
        'galt': None,
        'galtUnit': None,
        'DPGS_updt': None,
        'DPGS_ID': None
    }
    if gps_start == "$GNGGA": # GNGGA means US+Russian systems used, this is a hack
        chk_val = 0
        for char in gps_str[1:]: # Remove the $
            chk_val ^= ord(char)
        if chk_val == int(chk_sum, 16):
            for i, k in enumerate(
                    ['strType', 'fixTime',
                     'lat', 'latDir', 'lon', 'lonDir',
                     'fixQual', 'numSat', 'horDil',
                     'alt', 'altUnit', 'galt', 'galtUnit',
                     'DPGS_updt', 'DPGS_ID']):
                gps_data[k] = gps_components[i]
            return(gps_data)
        else:
            print("py_ublox_i2c: Invalid chksum: %s" % gps_chars)

def read_gps(i2c_address):
    response_bytes = []
    while True:
        byte = BUS.read_byte(i2c_address)
        if byte == 255:
            return False
        elif byte > 126: # TODO: This (for me) is a symptom of i2c bus problems. Throw?
            print("Unprintable char int={0}, chr={1}".format(byte, chr(byte)))
        elif byte == 10: # new line character
            break
        else:
            response_bytes.append(byte)
    response_chars = ''.join(chr(byte) for byte in response_bytes)
    return(parse_response(response_chars))

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
        elif last_byte == 10: # new line character
            break
        else:
            response_bytes = response_bytes + block
    response_chars = ''.join(chr(byte) for byte in response_bytes)
    return(parse_response(response_chars))

if __name__ == "__main__":
    connect_bus()
    #initialize_ublox(I2C_ADDRESS)
    gps_location = None
    while True:
        gps_location = read_gps(I2C_ADDRESS)
        if gps_location:
            print(json.dumps(gps_location, indent=2))
