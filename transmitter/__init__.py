import wiringpi
import serial

wiringpi.wiringPiSetupGpio()
wiringpi.pinMode(relay_control_pin, 1)


class Transmitter():
    uart = None
    enable_gpio_pin = 23

    # transmitter RTTY specs:
    rtty_baud = 50
    rtty_bits = serial.EIGHTBITS
    rtty_parity = serial.PARITY_NONE
    rtty_stopbits = serial.STOPBITS_TWO

    def enable_tx(self):
        wiringpi.digitalWrite(enable_gpio_pin, 1)

    def open_uart(self):
        if self.uart:
            raise Exception("UART previously opened?")
        self.uart = serial.Serial('/dev/ttyAMA0',
            self.rtty_baud, self.rtty_bits,
            self.rtty_parity, self.rtty_stopbits)

    def send_sentence(self, sentence):
        self.uart.write(sentence)
