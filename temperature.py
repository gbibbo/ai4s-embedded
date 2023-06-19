'''
This is a script that reads the temperature every 2 secodns and stores the result in /var/www/html/temperature_log.json. Previous files are deleted every time temperature.py is executed. The following configuration must be done to make temperature.py run at power up.
>Make the script executable. Open the terminal and run the following command:

chmod +x /home/pi/temperature.py

>Create a .desktop file to run the script at startup. Open the terminal and run the following command to create and edit the file:

nano ~/.config/autostart/run_temperature.desktop

>Add the following lines to the file:
    
[Desktop Entry]
Type=Application
Name=Run Temperature
Exec=python3 /home/pi/temperature.py
'''

import json
import time
from pathlib import Path
import os

def get_temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as temp_file:
            temp_millicelsius = int(temp_file.read().strip())
            return temp_millicelsius / 1000.0
    except FileNotFoundError:
        print(f"Error: /sys/class/thermal/thermal_zone0/temp not found.")
        return None

def log_temperature(temperature_log_path):
    temperature = get_temperature()
    if temperature is None:
        return

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    if not Path(temperature_log_path).exists():
        with open(temperature_log_path, 'w') as f:
            json.dump([], f)

    with open(temperature_log_path, 'r') as f:
        data = json.load(f)

    data.append({"timestamp": timestamp, "temperature": temperature})

    with open(temperature_log_path, 'w') as f:
        json.dump(data, f, indent=2)

def main():
    json_file_path = "/var/www/html/temperature_log.json"
    with open(json_file_path, 'w') as f:
        json.dump([], f)
    while True:
        log_temperature(json_file_path)
        time.sleep(2)

if __name__ == "__main__":
    main()