import time
import json
import smbus
import logging
# TODO: pynmea2 parses NMEA strings: https://github.com/Knio/pynmea2/
# FIXME: Enable flight mode
# TODO: disable unnecessary strings by sending $PUBX strings

BUS = None
address = 0x42
gpsReadInterval = 0.1
LOG = logging.getLogger()

# GUIDE
# http://ava.upuaut.net/?p=768

GPSDAT = {
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

def connectBus():
    global BUS
    BUS = smbus.SMBus(1)

def parseResponse(gpsChars):
    if "*" not in gpsChars:
        return False

    gpsStr, chkSum = gpsChars.split('*')
    gpsComponents = gpsStr.split(',')
    gpsStart = gpsComponents[0]
    if (gpsStart == "$GNGGA"):
        chkVal = 0
        for ch in gpsStr[1:]: # Remove the $
            chkVal ^= ord(ch)
        if (chkVal == int(chkSum, 16)):
            for i, k in enumerate(
                ['strType', 'fixTime',
                'lat', 'latDir', 'lon', 'lonDir',
                'fixQual', 'numSat', 'horDil',
                'alt', 'altUnit', 'galt', 'galtUnit',
                'DPGS_updt', 'DPGS_ID']):
                GPSDAT[k] = gpsComponents[i]
            print gpsChars
            print json.dumps(GPSDAT, indent=2)

def readGPS():
    byte = None
    response_bytes = []
    try:
        while True: # Newline, or bad char.
            byte = BUS.read_byte(address)
            if byte == 255:
                return False
            elif byte > 126: # FIXME: unprintable char, not sure what these might be... Maybe load an ASCII table library to translate? May be i2c control chars?
                print "Unprintable char int={0}, chr={1}".format(byte, chr(byte))
            elif byte == 10: # FIXME: magic number
                break
            else:
                response_bytes.append(byte)
        response_chars = ''.join(chr(byte) for byte in response_bytes)
        parseResponse(response_chars)
    except IOError:
        time.sleep(0.5)
        connectBus()
    except Exception, e:
        print e
        LOG.error(e)

connectBus()
while True:
    readGPS()
    time.sleep(gpsReadInterval)