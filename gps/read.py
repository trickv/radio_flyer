#!/usr/bin/env python

import time
import smbus
import pynmea2
# TODO: might want to try smbus2? https://github.com/kplindegaard/smbus2/

BUS = None
I2C_ADDRESS = 0x42
DEBUG = False

# Sources:
# http://ava.upuaut.net/?p=768
# https://stackoverflow.com/questions/28867795/reading-i2c-data-from-gps
# https://github.com/tuupola/micropython-gnssl76l/blob/master/gnssl76l.py

class BadDataException(Exception):
    """
    Raised when bad data has been read from the I2C bus and should probably be discarded.
    """
    pass

def connect_bus():
    global BUS
    BUS = smbus.SMBus(1)

def read_gps(i2c_address):
    global DEBUG
    response_bytes = []
    gibberish = False
    while True:
        byte = BUS.read_byte(i2c_address)
        if byte == 255: # this means that the ublox device reports no data available
            return False
        elif byte > 127:
            # TODO: This (for me) is a symptom of i2c bus problems.
            # Continue reading until the buffer is exhausted and then throw.
            if DEBUG:
                print("py_ublox_i2c: Unprintable char int={0}, chr={1}".format(byte, chr(byte)))
            gibberish = True
        elif byte == 10: # new line character
            break
        else:
            response_bytes.append(byte)
    if gibberish:
        if DEBUG:
            print("py_ublox_i2c: Not returning gibberish")
        raise BadDataException("Not returning gibberish i2c data")
    response_chars = ''.join(chr(byte) for byte in response_bytes)
    if DEBUG:
        print("py_ublox_i2c: GPS sentence: %s" % response_chars)
    msg = pynmea2.parse(response_chars, check=True)
    return(msg)

def simple_read_demo():
    connect_bus()
    global DEBUG
    DEBUG = True
    read_interval = 0.1
    while True:
        try:
            gps_location = read_gps(I2C_ADDRESS)
        except BadDataException:
            time.sleep(read_interval)
            continue
        except IOError:
            print("IOError on read, sleeping")
            time.sleep(read_interval)
            continue
        if gps_location:
            print(repr(gps_location))
        else:
            print("No data, sleeping a bit")
            time.sleep(read_interval)

if __name__ == "__main__":
    simple_read_demo()
