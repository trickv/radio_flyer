# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a High Altitude Balloon (HAB) tracker system designed to run on a Raspberry Pi. The tracker collects GPS coordinates, sensor data (temperature, humidity, pressure), and transmits telemetry via radio during balloon flights.

## Architecture

### Core Components

- **main.py**: Primary flight tracker loop that coordinates GPS reading, sensor collection, and radio transmission
- **lib.py**: Core library containing hardware interface classes:
  - `Transmitter`: Radio transmission via MTX2/NTX2 on UART
  - `Gps`: GPS data collection via serial interface using pynmea2
  - `Sensors`: I2C sensor management (BME280, LM75 temperature sensor)
  - `Camera`: Raspberry Pi camera control for flight photography
- **utils.py**: Utility functions for status output and system uptime
- **exercise-sensors.py**: Test/debug script for sensor validation without radio transmission

### Hardware Interface

- **GPS**: Serial connection for location and timing data
- **Radio Transmitter**: MTX2/NTX2 connected to GPIO 23 (enable) and UART
- **I2C Sensors**: BME280 (environmental data), LM75 (internal temperature)
- **Camera**: Raspberry Pi camera module

### Telemetry Protocol

The system transmits UKHAS-standard telemetry strings with CRC-CCITT checksum:
- Operational mode: `CALLSIGN,seq,time,lat,lon,alt,num_sats,temperature,pressure,humidity,internal_temp,HAM_CALLSIGN`
- No GPS fix mode: `CALLSIGN,seq,NOFIX,time,0,0,0,num_sats,temperature,pressure,humidity,uptime,internal_temp,HAM_CALLSIGN`

## Development Commands

### Dependencies
```bash
pip install -r requirements.pip
```

### Linting
```bash
pylint --disable too-few-public-methods --disable too-many-instance-attributes *.py
```

### Testing/Development
```bash
# Test sensors without radio transmission
./exercise-sensors.py

# Test GPS reading
./read-gps.py

# Run main tracker (use with caution - transmits radio)
./main.py
```

### System Installation
The `linux/` directory contains installation scripts for system-level configuration:
- `linux/boot/install`: Boot configuration
- `linux/systemd/install`: Service installation (radio_flyer.service, flyer_camera.service)
- `linux/udev/install`: USB GPS device rules

## Flight Callsigns
- Primary: EAGLE
- Ham radio: KD9PRC (for FCC compliance)