#!/usr/bin/env python3

import py_ublox_i2c
import utils
import transmitter

callsign = "MCNAIR"

if __name__ == "__main__":
    # read state from disk, if this is mid flight?
    utils.enable_relay_uart_to_gps()
    py_ublox_i2c.configure_serial.configure()
    utils.disable_relay_uart_to_gps()
    transmitter = transmitter.Transmitter()
    transmitter.open_uart()
    transmitter.enable_tx()
    # open i2c (?)
    while True:
        # save state
        # read bme280
        # take photo - maybe in another process?
        gps_location = py_ublox_i2c.read.read_gps()
        sentence = [callsign]
        sentence.append(gps_location.lat, gps_location.lon, alt)
        sentence_string = sentence.join(',')
        transmitter.send_sentence(sentence_string)
