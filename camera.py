#!/usr/bin/env python3

import time

import camera as camera_class


def main():
    print("Camera capture startup")
    camera = camera_class.Camera()
    while True:
        camera.take_photo()
        time.sleep(8)


if __name__ == "__main__":
    main()
