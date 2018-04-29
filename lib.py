"""
Core libraries for the tracker.
"""
import time
import os
import threading
import queue

import smbus
import serial
import wiringpi
import pynmea2
import pynmea2.types.talker
from bme280 import bme280, bme280_i2c
import picamera # pylint: disable=import-error


class Camera():
    """
    Camera class, which encapsulates the Raspberry Pi camera and
    tries to make it easy for an external program to just
    "take a bunch of photos as we fly"

    This isn't 100% stable so I'll drive it from camera.py for the first flight
    """
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
            os.makedirs(directory, exist_ok=True) # Python >= 3.2 required for exist_ok flag
            self.camera_ready = True
        except OSError as exception:
            print("Error while creating camera output dir: %s" % exception)
        self.output_directory = directory

    def take_photo(self):
        """
        Takes a photo and writes the resulting image to the output directory.
        Will skip taking a photo if the camera isn't ready from previous runs,
        and will detect repeat errors and disable the camera until restart.
        """
        if not self.camera_ready:
            print("Camera not ready.")
            return
        filesystem_status = os.statvfs(self.output_directory)
        free_space_bytes = filesystem_status.f_bavail * filesystem_status.f_bsize
        if free_space_bytes < self.free_space_threshold:
            print("Low on disk space: {}".format(free_space_bytes), flush=True)
            return
        self.sequence += 1
        output_file = "{0}/{1:06}.jpg".format(self.output_directory, self.sequence)
        print("Camera: taking picture to {}".format(output_file), flush=True)
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
        except Exception as exception: # pylint: disable=broad-except
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
    LM75 I2C temperature sensor reading class.
    By default the address of LM75 sensors are set to 0x48
    aka A0, A1, and A2 are set to GND (0v).
    """
    def __init__(self, address=0x48, bus_id=1):
        self.address = address
        self.bus = smbus.SMBus(bus_id)

    def get_temperature(self):
        """
        Read I2C data and calculate temperature
        http://www.ti.com/lit/ds/symlink/lm75a.pdf page 12
        """
        raw = self.bus.read_word_data(self.address, 0) & 0xFFFF
        raw = ((raw << 8) & 0xFF00) + (raw >> 8)
        temperature = (raw / 32.0) / 8.0
        if raw > 0x100: # most significant bit is 1, so it's negative
            temperature = -((~temperature & 0xFF) + 1)
        return temperature


class Bme280():
    """
    Bme280 I2C temperature sensor reading class.
    """
    def __init__(self, address=0x76, bus_id=1):
        self.address = address
        self.bus = smbus.SMBus(bus_id)
        bme280_i2c.set_default_bus(1)
        bme280_i2c.set_default_i2c_address(0x76)
        bme280.setup()

    def read(self): # pylint: disable=no-self-use
        """
        Read I2C data
        """
        return bme280.read_all()


class Transmitter():
    """
    Encapsultes the radio transmitter which is connected by:
    * Output "enable" relay
    * UART
    """
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
        """ Enable the TX-ENABLE GPIO pin """
        wiringpi.wiringPiSetupGpio()
        wiringpi.pinMode(self.enable_gpio_pin, 1)
        wiringpi.digitalWrite(self.enable_gpio_pin, 1)

    def open_uart(self):
        """ Open the UART port with PySerial """
        if self.uart:
            raise Exception("UART previously opened?")
        self.uart = serial.Serial('/dev/ttyAMA0',
                                  self.rtty_baud, self.rtty_bits,
                                  self.rtty_parity, self.rtty_stopbits)

    def close_uart(self):
        """ Close the UART (doubt I'll need this anymore. """
        self.uart.close()
        self.uart = None

    def send(self, string, block=True):
        """
        Transmit the supplied string in ASCII format, and debug to console
        """
        self.uart.write(string.encode('ascii'))
        print("TX: {0}".format(string), end="", flush=True)
        if not block:
            return
        nearly_empty_buffer = self.rtty_baud / 8 / 2 # 3 bytes at 50 baud is ~1/2 second
        while True:
            print("TX spin locking, out_waiting={}".format(self.uart.out_waiting))
            time.sleep(0.3)
            if self.uart.out_waiting <= nearly_empty_buffer:
                print("TX buf low enough for me")
                return


def __ubx_checksum(prefix_and_payload):
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


def ubx_assemble_packet(class_id, message_id, payload):
    """
    Assembles and returns a UBX packet from a class id,
    message id and payload bytearray.
    """
    # UBX protocol constants:
    ubx_packet_header = bytearray.fromhex("B5 62") # constant
    length_field_bytes = 2 # constant

    prefix = bytearray((class_id, message_id))
    length = len(payload).to_bytes(length_field_bytes, byteorder='little')
    return ubx_packet_header \
        + prefix \
        + length \
        + payload \
        + __ubx_checksum(prefix + length + payload)

class Gps():
    """
    Encapsulates the GPS receiver.
    Contains a PySerial UART connection, and a I/O thread.
    Also includes functions to configure the GPS, and generate "UBX" messages.
    """
    latest_sentence = None
    port = None
    read_thread = None

    read_queue = None
    write_queue = None
    ubx_read_queue = None

    # The following is a bit arbitrary...
    # On the seemingly impossible occasion where the main thread hasn't read in a while,
    # the queue will grow. This will cause the queue to fill up after 1000 seconds of data
    # from the GPS and throw, rather than sit there silent forever.
    maximum_read_queue_size = 1000

    default_timeout = 0.1 # Serial port read timeout. Should be quite low.

    debug_mode = False # change me to see debug output from this class

    def __init__(self):
        """
        Configure the GPS device and initialize queues, and start the I/O thread.
        """
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
        time.sleep(2)
        self.enable_flight_mode()
        #time.sleep(5)
        #self.reboot() # for funsies, FIXME, remove this before flight of course!
        #time.sleep(5)
        #self.configure_output_messages()


    def configure_output_messages(self):
        """
        Disables NMEA sentences with CFG-PRN: GLL, GSA, GSV, RMC, VTG (id 1 to 5)
        """
        ubx_cfg_class = 0x06
        ubx_cfg_msg = 0x01
        for index in range(1, 6):
            payload = bytearray.fromhex("F0")
            payload += index.to_bytes(1, byteorder='little')
            payload += bytearray.fromhex("00 00 00 00 00 01")
            return_code = self.__send_and_confirm_ubx_packet(ubx_cfg_class, ubx_cfg_msg, payload)
            if not return_code:
                raise Exception("Failed to configure output message id {}".format(index))


    def enable_flight_mode(self):
        """
        Sends a CFG-NAV5 UBX message which enables "flight mode", which allows
        operation at higher altitudes than defaults.
        Should read up more on this sentence, I'm just copying this
        byte string from other tracker projects.
        See for example string:
            https://github.com/Chetic/Serenity/blob/master/Serenity.py#L10
            https://github.com/PiInTheSky/pits/blob/master/tracker/gps.c#L423
        """
        print("GPS: enabling flight mode")
        cfg_nav5_class_id = 0x06
        cfg_nav5_message_id = 0x24
        payload = bytearray.fromhex("FF FF 06 03 00 00 00 00 10 27 00 00 05 00 FA 00 FA 00 64 00 2C 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00") # pylint: disable=line-too-long
        ack_ok = self.__send_and_confirm_ubx_packet(cfg_nav5_class_id, cfg_nav5_message_id, payload)
        if not ack_ok:
            raise Exception("Failed to configure GPS for flight mode.")
        print("GPS: flight mode enabled.")


    def reboot(self):
        """
        This method REBOOTS THE GPS. Useful for testing/debugging.
        Not useful at 30000 meters!
        """
        # https://gist.github.com/tomazas/3ab51f91cdc418f5704d says to send:
        # send 0x06, 0x04, 0x04, 0x00, 0xFF, 0x87, 0x00, 0x00
        return self.__send_and_confirm_ubx_packet(0x06, 0x04, bytearray.fromhex("FF 87 00 00"))

    def __send_and_confirm_ubx_packet(self, class_id, message_id, payload):
        """
        Constructs, sends, and waits for an ACK packet for a UBX "binary" packet.
        User only needs to specify the class & message IDs, and the payload as a bytearray;
            the header, length and checksum are calculated automatically.
        Then constructs the corresponding CFG-ACK packet expected, and waits for it.
        If the ACK packet is not received, returns False.
        """

        if self.ubx_read_queue.qsize() > 0:
            raise Exception("ubx_read_queue must be empty before calling this function")
        send_packet = ubx_assemble_packet(class_id, message_id, payload)
        self.write_queue.put(send_packet)
        self.debug("UBX packet built: {}".format(send_packet))

        expected_ack = ubx_assemble_packet(0x05, 0x01, bytearray((class_id, message_id)))

        wait_length = 10 # seconds
        wait_interval = 0.1 # seconds
        for _ in range(0, int(wait_length / wait_interval)):
            time.sleep(wait_interval) # excessively large to force me to fix race conditions FIXME
            if self.ubx_read_queue.qsize() > 0:
                ack = self.ubx_read_queue.get()
                if ack == expected_ack:
                    self.debug("UBX packet ACKd: {}".format(ack))
                    return True
                elif ack[2:3] == bytearray.fromhex("05 01"):
                    print("UBX-NAK packet! {}".format(ack))
                    return False
                else:
                    self.debug("Unknown UBX reply: {}".format(ack))
                    self.debug("Looking for      : {}".format(expected_ack))
                return True
        print("UBX packet sent without ACK! This is bad.")
        return False



    def read(self):
        """
        Returns the most recently received NMEA sentence.
        """
        queue_size = self.read_queue.qsize()
        self.debug("Queue length: {}".format(queue_size))
        if queue_size == 0 and not self.read_thread.is_alive():
            raise Exception("queue is empty and read thread is dead. bailing out.")
        while True:
            try:
                sentence = self.read_queue.get(block=False)
                if isinstance(sentence, pynmea2.types.talker.GGA):
                    self.latest_sentence = sentence
                else:
                    print("GPS: Unhandled message type received: {}".format(sentence))
            except queue.Empty:
                break
        return self.latest_sentence


    def __io_thread(self):
        """
        Singleton thread which will run indefinitely, reading and
        writing between the gps serial and {read,write}_queue.

        Do not invoke directly, this method never returns.
        """
        print("GPS: I/O thread started")
        while True:
            while self.write_queue.qsize() > 0:
                to_write = self.write_queue.get()
                to_write_type = type(to_write)
                if to_write_type == str:
                    to_write = to_write.encode('utf-8')
                self.debug("GPS: write {}: {}".format(to_write_type, to_write))
                self.port.write(to_write)
            got_some_data = self.__read()
            if not got_some_data:
                time.sleep(0.1)


    def __read(self):
        """
        Reads a from the GPS serial port.
        Interprets between UBX and NMEA packets and places into appropriate queues.
        For NMEA packets, they are parsed by pynmea2 and corrupt packets are discarded.

        Returns False when no data is available, True when data has been read.
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
            self.debug("UBX raw packet received: {}".format(ubx_packet))
            return True
        else:
            line = self.port.readline()
            line = first_byte + line
        try:
            ascii_line = line.decode('ascii')
        except UnicodeDecodeError as exception:
            self.debug("GPS reply string decode error on: {}".format(line))
            return False
        if ascii_line[0] != "$":
            self.debug("non-dollar line")
            return False
        self.debug("GPS (buf={}) raw line: {}".format(waiting, line))
        print("GPS: {}\n".format(ascii_line.strip()), flush=True)
        try:
            nmea_line = pynmea2.parse(ascii_line, check=True)
        except pynmea2.nmea.ParseError as exception:
            self.debug(exception)
            return False
        self.read_queue.put(nmea_line)
        return True

    def debug(self, message):
        """ prints a debug message to stdout if self_debug is set True """
        if self.debug_mode:
            print(message)


class Sensors():
    """
    Contains all code for talking to on-board sensors, excluding the GPS.
    Reads them periodically in a thread and makes latest data available for reading.
    """
    bme280_queue = None
    lm75_queue = None

    bme280_sensor = None
    lm75_sensor = None
    
    latest_bme280_data = None
    latest_lm75_temperature = None

    read_thread = None
    
    maximum_read_queue_size = 1000

    def __init__(self):
        """
        Start a thread which reads and logs data from the on-board sensors (excluding GPS).
        """
        self.lm75_sensor = Lm75()
        self.bme280_sensor = Bme280()
        self.lm75_queue = queue.Queue(maxsize=self.maximum_read_queue_size)
        self.bme280_queue = queue.Queue(maxsize=self.maximum_read_queue_size)
        self.read_thread = threading.Thread(target=self.__read_thread, daemon=True)
        self.read_thread.start()
        time.sleep(2)

    def __read_thread(self):
        print("Sensor read thread started")
        while True:
            lm75_data = self.lm75_sensor.get_temperature()
            lm75_queue.put(lm75_data)
            bme280_data = self.bme280_sensor.read()
            bme280_queue.put(bme280_data)
            sensor_format = "Sensors: lm75={0}, bme280 t={1} h={2} p={3}" # FIXME csv? time?
            print(sensor_format.format(lm75_data, bme280_data.temperature,
                  bme280_data.humidity, bme280_data.pressure))
            time.sleep(1)

    def get_bme280(self):
        if self.bme280_queue.qsize() == 0 and not self.read_thread.is_alive():
            raise Exception("bme280 queue is empty and thread is dead.")
        print("DEBUG: bme280 qsize={}".format(self.bme280_queue.qsize()))
        while True:
            try:
                self.latest_bme280_data = self.bme280_queue.get(block=False)
            except queue.Empty:
                break
        return self.latest_bme280_data

    def get_lm75_temperature(self):
        if self.lm75_queue.qsize() == 0 and not self.read_thread.is_alive():
            raise Exception("lm75 queue is empty and thread is dead.")
        print("DEBUG: lm75 qsize={}".format(self.lm75_queue.qsize()))
        while True:
            try:
                self.latest_lm75_temperature = self.lm75_queue.get(block=False)
            except queue.Empty:
                break
        return self.latest_lm75_temperature
