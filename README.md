# radio_flyer

code to run on a pi for a HAB flight.

[amazing diagram and pseudocode](https://photos.app.goo.gl/z1cqi8LFvM8kGdN53)

Learned lots from:
* https://github.com/Chetic/Serenity 
* https://github.com/PiInTheSky/pits

[![Build Status](https://travis-ci.org/trickv/radio_flyer.png)](https://travis-ci.org/trickv/radio_flyer)


= how to install

Wiring:
* I2C sensors wired in
* GPS on serial
* MTX2 / NTX2 on the on-board UART
 * Enable pin connected to GPIO 23

On a clean install of raspbian 9:
* raspi-config:
 * Interfacing: Enable the I2C interface
 * Interfacing: Serial: Disable console, enable hardware.
 * Interfacing: Enable the Camera
* /boot/config.txt:
 * Pi Nano W: Add to /boot/config.txt: dtoverlay=pi3-miniuart-bt
 * Optionally disable wifi to save power: dtoverlay=pi3-disable-wifi
* sudo systemctl disable hciuart
* git clone this repo into /home/pi/radio_flyer
* cd into linux and run the install script in each subdir
