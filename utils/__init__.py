import wiringpi

gps_uart_relay_gpio_pin = 19
wiringpi.wiringPiSetupGpio()
wiringpi.pinMode(gps_uart_relay_gpio_pin, 1)

def enable_relay_uart_to_gps():
    wiringpi.digitalWrite(gps_uart_relay_gpio_pin, 0)

def disable_relay_uart_to_gps():
    wiringpi.digitalWrite(gps_uart_relay_gpio_pin, 1)

def print_status_char(character):
    print(character, end='', flush=True)

def uptime():
    with open('/proc/uptime', 'r') as uptime_file:
        uptime_int = int(float(uptime_file.readline().split()[0]))
        return uptime_int

def print_conf(conf):
    print("Tracker startup. Config:")
    print(conf)
