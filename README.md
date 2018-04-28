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

On a clean install of raspbian 9:
* raspi-config:
 * Enable the I2C interface
 * Disable the on-board UART getty
* git clone this repo into /home/pi/radio_flyer
* cd into linux and run the install script in each subdir
