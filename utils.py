""" Utility functions to be called from the main tracker loop """

def print_status_char(character):
    """ prints a single character to stdout, no line break, flush output """
    print(character, end='', flush=True)

def uptime():
    """ returns the uptime in seconds of the computer as an integer """
    with open('/proc/uptime', 'r') as uptime_file:
        uptime_int = int(float(uptime_file.readline().split()[0]))
        return uptime_int
