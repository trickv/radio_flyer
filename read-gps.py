#!/usr/bin/env python3

import lib
import time


g = lib.Gps()

import random

while True:
    print(repr(g.read()))
    sleep_amount = random.randint(0,10000) / 1000.0
    print("\nMAIN: sleeping {} seconds.".format(sleep_amount))
    time.sleep(sleep_amount)
    print("MAIN: slept {} seconds.".format(sleep_amount))
