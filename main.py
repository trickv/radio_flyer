#!/usr/bin/env python3

import py_ublox_i2c
import utils

if __name__ == "__main__":
    utils.enable_relay_uart_to_gps()
    # configure gps over uart
    utils.disable_relay_uart_to_gps()
    # configure uart for 50 baud
    # enable mtx2 gpio pin
    # open i2c (?)
    while True:
        # save state
        # read bme280
        # take photo
        # read gps coords
        # build sentence
        # send sentence
