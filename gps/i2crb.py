#!/usr/bin/env python

import time
import subprocess

buffer = ""

while True:
    #time.usleep(10)
    command = "pigs i2crb 0 0"
    command = [x for x in command.split(" ")]
    byte_str = subprocess.check_output(command)
    byte = int(byte_str)
    character = chr(byte)
#    print(character)
    buffer = buffer + character
    if byte == 10: # new line
        print(buffer)
        buffer = ""

