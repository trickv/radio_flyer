import time
import os
import smbus
import threading
import queue

import serial
import picamera
import wiringpi
import pynmea2


class Camera():
    delay = 2
    free_space_threshold = 500 * 1024 * 1024 # 500MiB

    output_directory = None
    camera_ready = False
    fail_counter = 0
    sequence = 0

    def __init__(self):
        base_directory = "/home/pi/photos/"
        max_index = 0
        for directory in os.listdir(base_directory):
            try:
                current = int(directory)
            except ValueError:
                continue
            if current > max_index:
                max_index = current
        directory = base_directory + str(max_index + 1)
        print("Camera: Output dir set to %s" % directory)
        try:
            os.makedirs(directory, exist_ok = True) # Python >= 3.2 required for exist_ok flag
            self.camera_ready = True
        except OSError as exception:
            print("Error while creating camera output dir: %s" % exception)
        self.output_directory = directory

    def take_photo(self):
        if not self.camera_ready:
            print("Camera not ready.")
            return
        filesystem_status = os.statvfs(self.output_directory)
        free_space_bytes = filesystem_status.f_bavail * filesystem_status.f_bsize
        if free_space_bytes < self.free_space_threshold:
            print("Low on disk space: {}".format(free_space_bytes))
            return
        self.sequence += 1
        output_file = "{0}/{1}.jpg".format(self.output_directory, self.sequence)
        print("Camera: taking picture to {}".format(output_file))
        if os.path.exists(output_file):
            print("output file %s exists, skipping" % output_file)
            return
        camera = None
        try:
            camera = picamera.PiCamera()
            camera.resolution = (3280, 2464) # max resolution for v2 sensor
            camera.start_preview()
            time.sleep(self.delay)
            camera.capture(output_file)
            self.fail_counter = 0
        except Exception as exception:
            self.fail_counter += 1
            if self.fail_counter > 10:
                self.camera_ready = False
            print("Camera error, count {1}: {0}".format(exception, self.fail_counter))
            time.sleep(10) # cool off time after exception for hardware / other process to exit
        finally:
            # This turns the camera off, saving power between shots
            # It also must be run to free hardware locks for the next shot
            if camera:
                camera.close()


class Lm75():

    """
    By default the address of LM75 sensors are set to 0x48
    aka A0, A1, and A2 are set to GND (0v).
    """
    def __init__(self, address=0x48, bus_id = 1):
        self.address = address
        self.bus = smbus.SMBus(bus_id)

    def get_temperature(self):
        # Read I2C data and calculate temperature
        raw = self.bus.read_word_data(self.address, 0) & 0xFFFF
        raw = ((raw << 8) & 0xFF00) + (raw >> 8)
        temperature = (raw / 32.0) / 8.0
        return temperature


class Transmitter():
    uart = None
    enable_gpio_pin = 23

    # transmitter RTTY specs:
    rtty_baud = 50
    rtty_bits = serial.EIGHTBITS
    rtty_parity = serial.PARITY_NONE
    rtty_stopbits = serial.STOPBITS_TWO

    def __init__(self):
        self.open_uart()
        self.enable_tx()

    def enable_tx(self):
        wiringpi.wiringPiSetupGpio()
        wiringpi.pinMode(self.enable_gpio_pin, 1)
        wiringpi.digitalWrite(self.enable_gpio_pin, 1)

    def open_uart(self):
        if self.uart:
            raise Exception("UART previously opened?")
        self.uart = serial.Serial('/dev/ttyAMA0',
                                  self.rtty_baud, self.rtty_bits,
                                  self.rtty_parity, self.rtty_stopbits)

    def close_uart(self):
        self.uart.close()
        self.uart = None

    def send(self, string):
        print("TX: {0}".format(string), end="")
        self.uart.write(string.encode('ascii'))

class Gps():
    latest_sentence = None
    port = None
    packet_queue = None
    read_thread = None

    # The following is a bit arbitrary...
    # On the seemingly impossible occasion where the main thread hasn't read in a while,
    # the queue will grow. This will cause the queue to fill up after 1000 seconds of data
    # from the GPS and throw, rather than sit there silent forever.
    maximum_packet_queue_size = 1000

    def __init__(self):
        self.port = serial.Serial('/dev/ttyUSBGPS', 9600, timeout=0.1) # FIXME low timeout for debugging
        self.packet_queue = queue.Queue(maxsize=self.maximum_packet_queue_size)
        self.read_thread = threading.Thread(target=self.__read_thread, daemon=True)
        self.read_thread.start()

    # FIXME: Enable flight mode
    # TODO: is it possible to read the configuration to verify
    # flight mode has actually been enabled?

    def configure_for_flight(self):
        time.sleep(1)
        self.port.write(("\r\n" * 5).encode('ascii'))
        time.sleep(1)
        disable_excessive_reports(gps_serial)
        time.sleep(1)
        self.port.write(("\r\n" * 5).encode('ascii'))
        time.sleep(1)
        self.port.close()


    def configure_to_defaults(self):
        self.__set_excessive_reports(enable=True)


    def enable_flight_mode(self):
        # FIXME UNTESTED!
        # following is from https://github.com/Chetic/Serenity/blob/master/Serenity.py#L10
        mode_string = bytearray.fromhex("B5 62 06 24 24 00 FF FF 06 03 00 00 00 00 10 27 00 00 05 00 FA 00 FA 00 64 00 2C 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 16 DC")
        for character in mode_string:
            self.port.write(chr(character))
        self.port.write("\r\n")


    def disable_excessive_reports():
        self.__set_excessive_reports(enable=False)


    def __set_excessive_reports(enable=False):
        disable_template = "PUBX,40,%s,%d,0,0,0"
        messages_disable = [
            "GLL",
            "GSA",
            "RMC",
            "GSV",
            "VTG",
        ]
        for message in messages_disable:
            disable_command = disable_template % (message, 1 if enable else 0)
            checksum_int = 0
            for character in disable_command:
                checksum_int ^= ord(character)
            disable_command = "$%s*%x\r\n" % (disable_command, checksum_int)
            self.port.write(disable_command.encode('ascii'))


    def read(self):
        queue_size = self.packet_queue.qsize()
        print("Queue length: {}".format(queue_size))
        if queue_size == 0 and not self.read_thread.is_alive():
            raise Exception("queue is empty and read thread is dead. bailing out.")
        while True:
            try:
                self.latest_sentence = self.packet_queue.get(block=False)
            except queue.Empty:
                break
        return self.latest_sentence


    def __read_thread(self):
        """
        Singleton thread which will run indefinitely, reading the
        gps for sentences and putting the messages on a queue.

        Do not invoke directly, this method never returns.
        """
        while True:
            print(".", end='', flush=True)
            sentence = self.__read()
            if sentence:
                self.packet_queue.put(sentence)
            else:
                time.sleep(0.1)


    def __read(self):
        """
        Reads a sentence from the GPS serial port, validates and
        parses with pynmea2, and returns the pynmea2 sentence object.

        Returns False when no data is available.


        FIXME: Exceptions to catch:

        Partial sentence with non-ascii characters which fails to decode:
        GPS: b'\x05\xb1073705.00,5133.19017,N,00011.63010,W,1,12,0.66,78.4,M,45.7,M,,*66\r\n'
        UnicodeDecodeError: 'ascii' code  File "./read-gps.py", line 10, in <module>
         c can't decode byte 0xb1 in position 1: ordinal not in range(128)
        return pynmea2.parse(output.decode('ascii'), check=True)

        UnicodeDecodeError: 'ascii' codec can't decode byte 0xb1 in position 1: ordinal not in range(128)

        partial sentence again, but produces a pynmea parser error:
        pynmea2.nmea.ParseError: ('could not parse data', '7.00,5133.19072,N,00011.63259,W,1,12,0.70,73.4,M,45.7,M,,*69\r\n')



        GPS: b')\x92b\x82r\xb2\x8ab\xba\xa2r\xaabj\xb145.7,M,,*6B\r\n'
        UnicodeDecodeError: 'ascii' codec can't decode byte 0x92 in position 1: ordinal not in range(128)
        """

        waiting = self.port.in_waiting
        line = self.port.readline()
        try:
            ascii_line = line.decode('ascii')
        except UnicodeDecodeError as exception:
            print("ASCII decode error")
            return False
        if len(ascii_line) == 0:
            return False
        if ascii_line[0] != "$":
            print("non-dollar line")
            return False
        print("GPS (buf={}) raw line: {}".format(waiting, line))
        try:
            nmea_line = pynmea2.parse(ascii_line, check=True)
        except pynmea2.nmea.ParseError as exception:
            print(exception)
            return False
        return nmea_line
