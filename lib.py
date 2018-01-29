import time
import os
import smbus
import threading
import queue
import datetime

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
    read_queue = None
    write_queue = None
    read_thread = None
    ubx_read_queue = None

    # The following is a bit arbitrary...
    # On the seemingly impossible occasion where the main thread hasn't read in a while,
    # the queue will grow. This will cause the queue to fill up after 1000 seconds of data
    # from the GPS and throw, rather than sit there silent forever.
    maximum_read_queue_size = 1000

    default_timeout = 0.1 # FIXME low timeout for debugging

    def __init__(self):
        self.port = serial.Serial('/dev/ttyUSBGPS', 9600, timeout=self.default_timeout)
        self.read_queue = queue.Queue(maxsize=self.maximum_read_queue_size)
        self.write_queue = queue.Queue()
        self.ubx_read_queue = queue.Queue()
        self.read_thread = threading.Thread(target=self.__io_thread, daemon=True)
        self.read_thread.start()
        time.sleep(2)
        self.configure_for_flight()


    def configure_for_flight(self):
        """
        hacking space, these are mostly for testing. for flight I'll remove this
        function and put necessary calls in __init__()
        """
        self.configure_output_messages()
        time.sleep(3)
        self.enable_flight_mode()
        time.sleep(5)
        self.reboot() # for funsies, FIXME, remove this before flight of course!
        time.sleep(5)
        self.configure_output_messages()
        pass


    def configure_output_messages(self):
        ubx_cfg_class = 0x06
        ubx_cfg_msg = 0x01
        for index in range(1, 6):
            payload = bytearray.fromhex("F0") + index.to_bytes(1, byteorder='little') + bytearray.fromhex("00 00 00 00 00 01")
            return_code = self.__send_and_confirm_ubx_packet(ubx_cfg_class, ubx_cfg_msg, payload)
            if not return_code:
                raise Exception("Failed to configure output message id {}".format(index))


    def enable_flight_mode(self):
        # the following is from https://github.com/Chetic/Serenity/blob/master/Serenity.py#L10
        # bytearray.fromhex("B5 62 06 24 24 00 FF FF 06 03 00 00 00 00 10 27 00 00 05 00 FA 00 FA 00 64 00 2C 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 16 DC")
        cfg_nav5_class_id = 0x06
        cfg_nav5_message_id = 0x24
        payload = bytearray.fromhex("FF FF 06 03 00 00 00 00 10 27 00 00 05 00 FA 00 FA 00 64 00 2C 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00")
        return self.__send_and_confirm_ubx_packet(cfg_nav5_class_id, cfg_nav5_message_id, payload)


    def reboot(self):
        """
        This method REBOOTS THE GPS. Useful for testing/debugging.
        Not useful at 30000 meters!
        """
        # https://gist.github.com/tomazas/3ab51f91cdc418f5704d says to send:
        # send 0x06, 0x04, 0x04, 0x00, 0xFF, 0x87, 0x00, 0x00
        return self.__send_and_confirm_ubx_packet(0x06, 0x04, bytearray.fromhex("FF 87 00 00"))

    def __send_and_confirm_ubx_packet(self, class_id, message_id, payload):
        ubx_packet_header = bytearray.fromhex("B5 62") # constant
        length_field_bytes = 2 # constant

        if self.ubx_read_queue.qsize() > 0:
            raise Exception("ubx_read_queue must be empty before calling this function")

        prefix = bytearray((class_id, message_id))
        length = len(payload).to_bytes(length_field_bytes, byteorder='little')
        checksum = self.__ubx_checksum(prefix + length + payload)
        packet = ubx_packet_header + prefix + length + payload + checksum
        self.write_queue.put(packet)
        print("UBX packet built: {}".format(packet))

        ack_prefix = bytearray.fromhex("05 01")
        ack_length = int(2).to_bytes(length_field_bytes, byteorder='little')
        ack_payload = prefix
        ack_checksum = self.__ubx_checksum(ack_prefix + ack_length + ack_payload)
        expected_ack = ubx_packet_header + ack_prefix + ack_length + ack_payload + ack_checksum
        wait_length = 10 # seconds
        wait_interval = 0.1 # seconds
        interval_count = 0
        while True:
            if interval_count * wait_interval > wait_length:
                print("UBX packet sent without ACK! This is bad.")
                break
            time.sleep(wait_interval) # excessively large to force me to fix race conditions FIXME
            if self.ubx_read_queue.qsize() > 0:
                ack = self.ubx_read_queue.get()
                if ack == expected_ack:
                    print("UBX packet ACKd: {}".format(ack))
                elif ack[2:3] == bytearray.fromhex("05 01"):
                    print("UBX-NAK packet! :(")
                else:
                    print("Unknown UBX reply: {}".format(ack))
                    print("Looking for      : {}".format(expected_ack))
                return True
            interval_count += 1
        return False

    def __ubx_checksum(self, prefix_and_payload):
        """
        Calculates a UBX binary packet checksum.
        Algorithm comes from the u-blox M8 Receiver Description manual section "UBX Checksum"
        This is an implementation of the 8-Bit Fletcher Algorithm,
            so there may be a standard library for this.
        """
        checksum_a = 0
        checksum_b = 0
        for byte in prefix_and_payload:
            checksum_a = checksum_a + byte
            checksum_b = checksum_a + checksum_b
        checksum_a %= 256
        checksum_b %= 256
        return bytearray((checksum_a, checksum_b))


    def read(self):
        queue_size = self.read_queue.qsize()
        print("Queue length: {}".format(queue_size))
        if queue_size == 0 and not self.read_thread.is_alive():
            raise Exception("queue is empty and read thread is dead. bailing out.")
        while True:
            try:
                self.latest_sentence = self.read_queue.get(block=False)
            except queue.Empty:
                break
        return self.latest_sentence


    def __io_thread(self):
        """
        Singleton thread which will run indefinitely, reading and
        writing between the gps serial and {read,write}_queue.

        Do not invoke directly, this method never returns.
        """
        while True:
            print(".", end='', flush=True)
            while self.write_queue.qsize() > 0:
                to_write = self.write_queue.get()
                to_write_type = type(to_write)
                if to_write_type == str:
                    to_write = to_write.encode('utf-8')
                print("GPS: write {}: {}".format(to_write_type, to_write))
                self.port.write(to_write)
            sentence = self.__read()
            if sentence:
                self.read_queue.put(sentence)
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
        if waiting == 0:
            return False
        first_byte = self.port.read()
        if first_byte == b'\xb5': # looks like a UBX proprietary packet
            self.port.timeout = 10
            remaining_header = self.port.read(3)
            length_bytes = self.port.read(2)
            length = int.from_bytes(length_bytes, byteorder='little')
            remaining_packet = self.port.read(length + 2) # add 2 for checksum bytes
            self.port.timeout = self.default_timeout
            ubx_packet = first_byte + remaining_header + length_bytes + remaining_packet
            self.ubx_read_queue.put(ubx_packet)
            return
        else:
            line = self.port.readline()
            line = first_byte + line
        try:
            ascii_line = line.decode('ascii')
        except UnicodeDecodeError as exception:
            print("GPS reply string decode error on: {}".format(line))
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
