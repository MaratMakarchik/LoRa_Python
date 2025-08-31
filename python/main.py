import subprocess
import os
import sys

# Import modules
from compile_lora_app import compile_lora_app
from sender import LoraController
from database import SensorDatabase
from terminal_output import print_green, print_red

CONFIG_SENSOR = 'sensor.conf'

def main():
   
    print_green('start program')

    # Build and execute C files
    if compile_lora_app():
        print_green('The bin file has been successfully compiled')
    else:
        print_red('bin file assembly error')
        sys.exit(1)
    
     # Create and populate database
    sensor_db = SensorDatabase()
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), CONFIG_SENSOR)
        with open(config_path, 'r', encoding='utf-8') as f:
              for line in f:
                  line = line.strip()
                  if line:  # Skip empty lines
                      # Add check for separator
                      if '@' in line:
                          sensor_id, sensor_location = line.split('@', 1)
                          sensor_db.add_sensor(sensor_id.strip(), sensor_location.strip())
                      else:
                          print_red('Invalid format in config file')
                    
    except FileNotFoundError:
          print_red('the sensor configuration file was not found')
          sys.exit(1)
    except Exception as e:
          print_red(f'Error reading config file: {str(e)}')
          sys.exit(1)

if __name__ == "__main__":
    main()