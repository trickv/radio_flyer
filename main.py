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

coordinate_precision = 6

def main ():
    # read state from disk, if this is mid flight?
    utils.enable_relay_uart_to_gps()
    py_ublox_i2c.configure_serial.configure_for_flight()
    utils.disable_relay_uart_to_gps()
    transmitter = transmitter_class.Transmitter()
    transmitter.open_uart()
    transmitter.enable_tx()
    py_ublox_i2c.read.connect_bus()
    status = []
    num_gps_reads = 0
    while True:
        # save state
        # read bme280
        # take photo - maybe in another process?
        gps_location = None
        try:
            num_gps_reads += 1
            gps_location = py_ublox_i2c.read.read_gps(ublox_i2c_address)
        except py_ublox_i2c.read.BadDataException:
            print("!", end="")
            time.sleep(0.5)
            continue
        except KeyError:
            status.append("KeyError on read_gps: %s;" % exception)
        except IOError as exception:
            status.append("IOError on read_gps: %s;" % exception)
        except pynmea2.nmea.ParseError as exception:
            status.append("ParseError on read_gps: %s;" % exception)
        if not gps_location:
            print(".", end="")
            time.sleep(0.5)
            continue
        sentence = [callsign]
        if gps_location.sentence_type == 'GGA':
            sentence.append(str(gps_location.timestamp.isoformat()))
            sentence.append(str(round(gps_location.latitude, coordinate_precision))) # FIXME: what does dl-fldigi require? see serenity code.
            sentence.append(str(round(gps_location.longitude, coordinate_precision)))
            sentence.append(str(int(round(gps_location.altitude, 0))))
            sentence.append(str(int(gps_location.num_sats)))
            sentence.append(str(num_gps_reads))
        else:
            print("WTF?!?!: %s %s" % (gps_location, repr(gps_location)))
            sentence.append("0")
            sentence.append("0")
            sentence.append("0")
            sentence.append("0")
            sentence.append("0")
            status.append("gps_location type %s" % gps_location.sentence_type)
        sentence.append(";".join(status))
        sentence_string = ",".join(sentence)
        # TODO: CHECKSUM!
        sentence_string += "\n"
        print("")
        transmitter.send_sentence(sentence_string)
        num_gps_reads = 0
        status = []


if __name__ == "__main__":
    main()
