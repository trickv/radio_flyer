#!/usr/bin/env python

import time
import subprocess

buffer = ""

while True:
    #time.usleep(10)
    command = "pigs i2crd 0 16"
    command = [x for x in command.split(" ")]
    byte_str_array = subprocess.check_output(command)
    for byte_str in byte_str_array.split(" "):
        byte = int(byte_str)
        character = chr(byte)
        if byte == 255: # i2c err?
            next
        if byte > 126: # unprintable?
            #print "Unprintable: %d" % byte
            next
        if byte < 0:
            print "<0: %d" % byte
            next
        if byte == 10: # new line
            print(buffer)
            buffer = ""
        else:
            buffer = buffer + character

