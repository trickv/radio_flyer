import wiringpi

gps_uart_relay_gpio_pin = 19
wiringpi.wiringPiSetupGpio()
wiringpi.pinMode(gps_uart_relay_gpio_pin, 1)

def enable_relay_uart_to_gps():
    wiringpi.digitalWrite(gps_uart_relay_gpio_pin, 0)

def disable_relay_uart_to_gps():
    wiringpi.digitalWrite(gps_uart_relay_gpio_pin, 1)
