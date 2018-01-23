# py_ublox_i2c

some of my hacking to read a ublox GPS over i2c.

[![Build Status](https://travis-ci.org/trickv/py_ublox_i2c.png)](https://travis-ci.org/trickv/py_ublox_i2c)

NB: must load the i2c drive with baudrate set to 400k:
 sudo modprobe i2c-bcm2708 baudrate=400000

Else you, like me, spend lots of times getting lots of errors. Bytes > 126 / corrupt lines are a symptom of a bus too slow to read all the data.
