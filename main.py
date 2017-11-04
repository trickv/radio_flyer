#!/usr/bin/env python3

import time

import pynmea2
import py_ublox_i2c.read
import py_ublox_i2c.configure_serial
import utils
import transmitter as transmitter_class

callsign = "RADIOFLYER"

ublox_i2c_address = 0x42 # FIXME should be in lib
BUS = None

def main ():
    # read state from disk, if this is mid flight?
    utils.enable_relay_uart_to_gps()
    py_ublox_i2c.configure_serial.configure_for_flight()
    utils.disable_relay_uart_to_gps()
    transmitter = transmitter_class.Transmitter()
    transmitter.open_uart()
    transmitter.enable_tx()
    # open i2c (?)
    py_ublox_i2c.read.connect_bus()
    status = ""
    while True:
        # save state
        # read bme280
        # take photo - maybe in another process?
        """
LINE: $GNGGA,003156.00,,,,,0,00,99.99,,,,,,*79
TX: RADIOFLYER,0.0,0.0,None

LINE: $GNGLL,,,,,003156.00,V,N*55
Traceback (most recent call last):
  File "/home/pi/radio_flyer/env/lib/python3.4/site-packages/pynmea2/nmea.py", line 153, in __getattr__
    i = t.name_to_idx[name]
KeyError: 'altitude'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "./main.py", line 45, in <module>
    main()
  File "./main.py", line 37, in main
    sentence.append(str(gps_location.altitude))
  File "/home/pi/radio_flyer/env/lib/python3.4/site-packages/pynmea2/nmea.py", line 155, in __getattr__
    raise AttributeError(name)
AttributeError: altitude

        """
        try:
            gps_location = py_ublox_i2c.read.read_gps(ublox_i2c_address)
        except  KeyError:
            status = "KeyError on read_gps;"
        if not gps_location:
            print("no fix?")
            time.sleep(0.1)
            continue
        sentence = [callsign]
        if type(gps_location) == pynmea2.types.talker.GGA:
            sentence.append(str(gps_location.latitude))
            sentence.append(str(gps_location.longitude))
            sentence.append(str(gps_location.altitude))
        else:
            sentence.append("0")
            sentence.append("0")
            sentence.append("0")
            status += "gps_location type %s;" % type(gps_location)
        sentence.append(status)
        sentence_string = ",".join(sentence)
        # CHECKSUM!
        sentence_string += "\n"
        transmitter.send_sentence(sentence_string)
        status = ""


if __name__ == "__main__":
    main()
