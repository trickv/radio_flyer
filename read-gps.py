#!/usr/bin/env python3

import lib

g = lib.Gps()

while True:
    time.sleep(1)
    print(g.read())
