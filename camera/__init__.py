import picamera
import time

class Camera():
    output_directory = None

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
        os.makedirs(directory, exist_ok = True) # Python >= 3.2 required for exist_ok flag
        self.output_directory = directory

    def __raspistill_camera_take_photo(packet_data, camera_output_directory):
        filename = "{0}/{1}-{2}.jpg".format(camera_output_directory, packet_data['seq'], packet_data['time'])
        subprocess.call(["raspistill", "-o", filename])

    def take_photo(packet_data):
        camera = picamera.PiCamera()
        output_file = "{0}/{1}-{2}.jpg".format(self.output_directory, packet_data['seq'], packet_data['time'])
        if os.path.exists(output_file):
            print("output file %s exists, skipping" % output_file)
            return
        camera.resolution = (3280, 2464) # max resolution for v2 sensor
        camera.start_preview()
        time.sleep(2)
        camera.capture(output_file)
        camera.close() # This turns the camera off, saving power between shots