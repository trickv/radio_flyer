#!/usr/bin/env python3

import lib
import time

g = lib.Gps()

while True:
    time.sleep(1)
    print(repr(g.read()))
