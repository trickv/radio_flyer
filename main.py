#!/usr/bin/env python3

import time

import py_ublox_i2c.read
import py_ublox_i2c.configure_serial
import utils
import transmitter

callsign = "RADIOFLYER"

ublox_i2c_address = 0x42 # FIXME should be in lib
BUS = None

def main ():
    # read state from disk, if this is mid flight?
    utils.enable_relay_uart_to_gps()
    py_ublox_i2c.configure_serial.configure()
    utils.disable_relay_uart_to_gps()
    transmitter = transmitter.Transmitter()
    transmitter.open_uart()
    transmitter.enable_tx()
    # open i2c (?)
    py_ublox_i2c.read.connect_bus()
    while True:
        # save state
        # read bme280
        # take photo - maybe in another process?
        gps_location = py_ublox_i2c.read.read_gps(ublox_i2c_address)
        if not gps_location:
            print("no fix?")
            time.sleep(0.1)
            continue
        sentence = [callsign]
        sentence.append(gps_location['lat'])
        sentence.append(gps_location['lon'])
        sentence.append(gps_location['alt'])
        sentence_string = ",".join(sentence)
        # CHECKSUM!

if __name__ == "__main__":
    main()
        transmitter.send_sentence(sentence_string)
