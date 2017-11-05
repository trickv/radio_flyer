#!/usr/bin/env python3

import time

import pynmea2
import crcmod

import py_ublox_i2c.read
import py_ublox_i2c.configure_serial
import utils
import transmitter as transmitter_class

callsign = "RADIOFLYER"

ublox_i2c_address = 0x42 # FIXME should be in lib
BUS = None

crc16f = crcmod.predefined.mkCrcFun('crc-ccitt-false')

coordinate_precision = 6
        
packet_template = "{callsign},{time},{lat},{lon},{alt},{num_sats},{num_gps_reads}"
# TODO: should I send \r\n or can we just all be unix friends from now on?
sentence_template = "$${0}*{1:X}\n"

def main ():
    # read state from disk, if this is mid flight?
    utils.enable_relay_uart_to_gps()
    py_ublox_i2c.configure_serial.configure_for_flight()
    utils.disable_relay_uart_to_gps()
    transmitter = transmitter_class.Transmitter()
    transmitter.open_uart()
    transmitter.enable_tx()
    py_ublox_i2c.read.connect_bus()
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
        except KeyError as exception:
            print(exception)
        except IOError as exception:
            print(exception)
        except pynmea2.nmea.ParseError as exception:
            print(exception)
        if not gps_location:
            print(".", end="")
            time.sleep(0.5)
            continue
        packet_params = {
            'callsign': callsign,
            'num_gps_reads': num_gps_reads,
        }
        if gps_location.sentence_type == 'GGA':
            packet_params.update({
                'time': gps_location.timestamp.isoformat(),
                'lat': round(gps_location.latitude, coordinate_precision), # FIXME: what does dl-fldigi require? see serenity code.
                'lon': round(gps_location.longitude, coordinate_precision),
                'alt': int(round(gps_location.altitude, 0)),
                'num_sats': int(gps_location.num_sats),
            })
        else:
            # Oh shit, the GPS is sending things I don't know how to handle, so TX it as-is and move on
            crazy = "%s: Unexpected GPS data: %s %s\n" % (callsign, gps_location, repr(gps_location))
            transmitter.send(crazy)
            continue
        packet = packet_template.format(**packet_params)
        # TODO: CHECKSUM!
        checksum = crc16f(packet.encode('ascii'))
        sentence = sentence_template.format(packet, checksum)
        print("")
        transmitter.send(sentence)
        num_gps_reads = 0


if __name__ == "__main__":
    main()
