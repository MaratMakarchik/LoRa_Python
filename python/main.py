# main.py
import subprocess
import os
import sys

# Import modules
from compile_lora_app import compile_lora_app
# Note: You might need to adjust these imports based on your actual file structure
# from sender import LoraController
# from database import SensorDatabase

MES_LEN = 90
CONFIG_SENSOR = 'sensor.conf'

def main():
    # Fixed string formatting
    print(f"---{'start program':^{MES_LEN}}---")

    # Build and execute C files
    if compile_lora_app():
        print(f"---{'The bin file has been successfully compiled':^{MES_LEN}}---")
    else:
        print(f"---{'bin file assembly error':^{MES_LEN}}---")
        sys.exit(1)
    
    # Note: The database and sensor configuration code is commented out
    # as it might need adjustments based on your project structure
    
    # # Create and populate database
    # sensor_db = SensorDatabase()
    # try:
    #     # Use the correct path to config file (in project root)
    #     config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), CONFIG_SENSOR)
    #     with open(config_path, 'r', encoding='utf-8') as f:
    #         for line in f:
    #             line = line.strip()
    #             if line:  # Skip empty lines
    #                 # Add check for separator
    #                 if '@' in line:
    #                     sensor_id, sensor_location = line.split('@', 1)
    #                     sensor_db.add_sensor(sensor_id.strip(), sensor_location.strip())
    #                 else:
    #                     print(f"---{'Invalid format in config file':^{MES_LEN}}---")
    # except FileNotFoundError:
    #     print(f"---{'the sensor configuration file was not found':^{MES_LEN}}---")
    #     sys.exit(1)
    # except Exception as e:
    #     print(f"---{f'Error reading config file: {str(e)}':^{MES_LEN}}---")
    #     sys.exit(1)

if __name__ == "__main__":
    main()