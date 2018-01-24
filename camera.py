#!/usr/bin/env python3

import time

import lib


def main():
    print("Camera capture startup")
    camera = lib.Camera()
    while True:
        camera.take_photo()
        time.sleep(8)


if __name__ == "__main__":
    main()
