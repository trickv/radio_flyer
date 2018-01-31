def print_status_char(character):
    print(character, end='', flush=True)

def uptime():
    with open('/proc/uptime', 'r') as uptime_file:
        uptime_int = int(float(uptime_file.readline().split()[0]))
        return uptime_int
