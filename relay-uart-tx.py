#!/usr/bin/env python3

import wiringpi
import time
import sys

relay_control_pin = 19

if len(sys.argv) == 2 and sys.argv[1] == "on":
    print("You want relay on, yay!.")
    set_high = False
else:
    print("You want relay off.")
    set_high = True

print("Setting GPIO pin {0} to {1}".format(relay_control_pin, set_high))

wiringpi.wiringPiSetupGpio()

wiringpi.pinMode(relay_control_pin, 1)
wiringpi.digitalWrite(relay_control_pin, 1 if set_high else 0)
