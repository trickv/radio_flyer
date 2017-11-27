import time
import os

import picamera

class Camera():
    output_directory = None
    camera_ready = False
    fail_counter = 0

    def __init__(self):
        base_directory = "/home/pi/photos/"
        max_index = 0
        for directory in os.listdir(base_directory):
            try:
                current = int(directory)
            except ValueError:
                continue
            if current > max_index:
                max_index = current
        directory = base_directory + str(max_index + 1)
        print("Camera: Output dir set to %s" % directory)
        try:
            os.makedirs(directory, exist_ok = True) # Python >= 3.2 required for exist_ok flag
            self.camera_ready = True
        except OSError as exception:
            print("Error while creating camera output dir: %s" % exception)
        self.output_directory = directory

    def __raspistill_camera_take_photo(self, packet_data, camera_output_directory):
        filename = "{0}/{1}-{2}.jpg".format(camera_output_directory, packet_data['seq'], packet_data['time'])
        subprocess.call(["raspistill", "-o", filename], timeout=10)

    def take_photo(self, packet_data, delay=2):
        if not self.camera_ready:
            print("Camera not ready.")
            return False
        output_file = "{0}/{1}-{2}.jpg".format(self.output_directory, packet_data['seq'], packet_data['time'])
        if os.path.exists(output_file):
            print("output file %s exists, skipping" % output_file)
            return False
        try:
            camera = picamera.PiCamera()
            camera.resolution = (3280, 2464) # max resolution for v2 sensor
            try:
                packet_data['lat'] = "%s/10000" % int(abs(packet_data['lat']) * 10000)
                packet_data['lon'] = "%s/10000" % int(abs(packet_data['lon']) * 10000)
                packet_data['alt'] = "%s/100" % int(packet_data['alt'] * 100)
                camera.exif_tags.update({
                    'GPS.GPSLatitude': str(packet_data['lat']),
                    'GPS.GPSLatitudeRef': 'S' if packet_data['lat'] < 0 else 'N',
                    'GPS.GPSLongitude': str(packet_data['lon']),
                    'GPS.GPSLongitudeRef': 'E' if packet_data['lon'] > 0 else 'W',
                    'GPS.GPSAltitude': str(packet_data['alt']),
                    'GPS.GPSSatellites': str(packet_data['num_sats']),
                    'GPS.GPSTimeStamp': packet_data['time'],
                    # 'GPS.GPSDateStamp': packet_data['date'], # TODO grab date from GPS before turning off other strings?
                    'EXIF.UserComment': "sequence={seq}, temperature={temperature}, pressure={pressure}, humidity={humidity}".format(**packet_data),
                    # TODO: EXIF.DateTimeOriginal and DateTimeDigitized
                    })
            except KeyError as exception:
                # likely this is during warmup where we don't have a GPS fix. Don't worry about exif.
                print("Failed to add GPS EXIF data: {0}".format(exception))
                pass
            camera.start_preview()
            time.sleep(delay)
            camera.capture(output_file)
            camera.close() # This turns the camera off, saving power between shots
        except Exception as exception:
            self.fail_counter += 1
            if self.fail_counter > 10:
                self.camera_ready = False
            print("Camera error, count {1}: {0}".format(exception, self.fail_counter))
            pass
            return False
        return output_file
