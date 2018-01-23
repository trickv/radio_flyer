import smbus

class Lm75():

    """
    By default the address of LM75 sensors are set to 0x48
    aka A0, A1, and A2 are set to GND (0v).
    """
    def __init__(self, address=0x48, bus_id = 1):
        self.address = address
        self.bus = smbus.SMBus(bus_id)

    def get_temperature(self):
        # Read I2C data and calculate temperature
        raw = bus.read_word_data(self.address, 0) & 0xFFFF
        raw = ((raw << 8) & 0xFF00) + (raw >> 8)
        temperature = (raw / 32.0) / 8.0
        return temperature
