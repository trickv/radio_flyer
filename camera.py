#!/usr/bin/env python3

""" replacement implementation for taking photos from the main tracker """

import time

import lib


def main():
    """ main loop, never exits """
    print("Camera capture startup")
    camera = lib.Camera()
    while True:
        camera.take_photo()
        time.sleep(8)


if __name__ == "__main__":
    main()
