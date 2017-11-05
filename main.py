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
        
operational_packet_template = "{callsign},{time},{lat},{lon},{alt},{num_sats},{num_gps_reads}"
no_fix_packet_template = "{callsign},NOFIX,{time},{num_sats},{num_gps_reads},{uptime}"
# TODO: should I send \r\n or can we just all be unix friends from now on?
sentence_template = "$${0}*{1:X}\n"

def uptime():  
    with open('/proc/uptime', 'r') as uptime_file:
        uptime = int(float(uptime_file.readline().split()[0]))
        return uptime

def configure_ublox():
    utils.enable_relay_uart_to_gps()
    py_ublox_i2c.configure_serial.configure_for_flight()
    utils.disable_relay_uart_to_gps()

def main ():
    # read state from disk, if this is mid flight?
    configure_ublox()
    transmitter = transmitter_class.Transmitter()
    transmitter.open_uart()
    transmitter.enable_tx()
    transmitter.send("Worlds best tracker software. Buy bitcoin!\n\n")
    transmitter.send("Thanks to my lovely wife Sarah.\n\n")
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
            print("K", end="")
        except IOError as exception:
            print("I", end="")
        except pynmea2.nmea.ParseError as exception:
            print("P", end="")
        if not gps_location:
            print(".", end="")
            time.sleep(0.5)
            continue
        packet_params = {
            'callsign': callsign,
            'num_gps_reads': num_gps_reads,
        }
        if gps_location.sentence_type == 'GGA':
            timestamp = gps_location.timestamp.isoformat() if gps_location.timestamp else "00:00:00"
            packet_params.update({
                'num_sats': int(gps_location.num_sats),
                'time': timestamp,
            })
            if gps_location.gps_qual == 0:
                packet_template = no_fix_packet_template
                packet_params.update({
                    'uptime': uptime()
                })
            else:
                packet_template = operational_packet_template
                packet_params.update({
                    'alt': int(round(gps_location.altitude, 0)),
                    'lat': round(gps_location.latitude, coordinate_precision), # FIXME: what does dl-fldigi require? see serenity code.
                    'lon': round(gps_location.longitude, coordinate_precision),
                })
        else:
            # Oh shit, the GPS is sending things I don't know how to handle, so TX it as-is and move on
            crazy = "%s: Unexpected GPS data: %s\n" % (callsign, gps_location)
            transmitter.send(crazy)
            if gps_location.sentence_type in ("GLL", "GSA", "RMC", "GSV", "VTG"):
                # either the initial config of the ublox didn't work, or it's been reset.
                # closing the uart should block until it's done spooling data.
                transmitter.send("%s: Re-configuring ublox...\n" % callsign)
                transmitter.close_uart()
                print("UART closed, go go go")
                configure_ublox()
                transmitter.open_uart()
            continue
        packet = packet_template.format(**packet_params)
        checksum = crc16f(packet.encode('ascii'))
        sentence = sentence_template.format(packet, checksum)
        print("")
        transmitter.send(sentence)
        num_gps_reads = 0


if __name__ == "__main__":
    main()
