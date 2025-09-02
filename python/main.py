import subprocess
import os
import sys
import time
import threading
import signal
from typing import Optional

# Import modules
from compile_lora_app import compile_lora_app
from sender import LoraController
from database import SensorDatabase
from terminal_output import print_green, print_red

CONFIG_SENSOR = 'sensor.conf' 
# Sensor polling frequency time
SURVEY_TIME = 20
# Measurement time for one sensor
# This is needed because the MQ-7 sensor requires heating time
BEACON_TIME = 5

# Global variables for thread management
survey_timer: Optional[threading.Timer] = None
running = True

def data_survey(controller):
    # Function to poll sensor data
    try:
        command = f'st {BEACON_TIME} fn'
        controller.send_command(command.encode())
    except Exception as e:
        print_red(f"Error in data_survey: {e}")
    finally:
        # Schedule next survey after completing current one
        if running:
            schedule_next_survey(controller)

def schedule_next_survey(controller):
    # Schedule the next survey
    global survey_timer
    if running:
        survey_timer = threading.Timer(SURVEY_TIME, data_survey, args=(controller,))
        survey_timer.daemon = True  # Thread will terminate with main program
        survey_timer.start()

def load_sensor_config(config_path):
    # Load sensor configuration from file
    sensors = []
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):  # Skip empty lines and comments
                    if '@' in line:
                        sensor_id, sensor_location = line.split('@', 1)
                        sensors.append((sensor_id.strip(), sensor_location.strip()))
                    else:
                        print_red(f'Invalid format in config file at line {line_num}: {line}')
                        return None
        return sensors
    except FileNotFoundError:
        print_red('The sensor configuration file was not found')
        return None
    except Exception as e:
        print_red(f'Error reading config file: {str(e)}')
        return None

def get_project_root():
    # Get project root directory
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_executable_path():
    # Get path to executable file
    return os.path.join(get_project_root(), 'file_c', 'bin', 'lora_app')

def signal_handler(sig, frame):
    # Signal handler for graceful shutdown
    global running
    print_red("\nReceived shutdown signal. Shutting down...")
    running = False
    if survey_timer:
        survey_timer.cancel()

def main():
    global running, survey_timer
   
    print_green('Starting program')

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Build C files
    if compile_lora_app():
        print_green('Binary file compiled successfully')
    else:
        print_red('Binary file compilation error')
        sys.exit(1)

    # Create database
    sensor_db = SensorDatabase()
    
    # Load sensor configuration
    config_path = os.path.join(get_project_root(), CONFIG_SENSOR)
    sensors = load_sensor_config(config_path)
    
    if sensors is None:
        sys.exit(1)
    
    # Add sensors to database
    for sensor_id, sensor_location in sensors:
        sensor_db.add_sensor(sensor_id, sensor_location)
    
    print_green(f"Loaded {len(sensors)} sensors from configuration")

    # Launch C program
    controller = None
    c_process = None
    
    try:
        exe_file = get_executable_path()
        
        # Check if executable file exists
        if not os.path.exists(exe_file):
            print_red(f"Executable file not found: {exe_file}")
            sys.exit(1)
        
        c_process = subprocess.Popen([exe_file])
        
        print_green(f"Started C process with PID: {c_process.pid}")
        time.sleep(2)  # Give C program time to set up sockets

        controller = LoraController()
        controller.start()  # Start background listener

        time.sleep(2)
    
        if controller.get_message() == 'Lora init':
            print_green("The LoRa has been successfully initialized")
        else:
            print_red('The LoRa is not initialized')
            sys.exit(1)
        
        # Start first survey
        data_survey(controller)
        print_green("Starting main application loop")
        
        # Main loop
        while running:
            try:
                message = controller.get_message()  # Check and receive messages
                
                if message: 
                    print_green(f"Received data: {message} | {time.strftime('%H:%M:%S', time.localtime())}")
                    # Add message processing and database saving here

                # Check connection status
                if not controller.cmd_socket and not controller.data_socket:
                    print_red("Both connections lost. Exiting")
                    break

                time.sleep(0.1)  # Main loop delay
                
            except Exception as e:
                print_red(f"Error in main loop: {e}")
                time.sleep(1)  # Delay on error

    except ConnectionRefusedError:
        print_red("Could not start the controller. Aborting")
    except Exception as e:
        print_red(f"Unexpected error: {e}")
    finally:
        running = False
        if survey_timer:
            survey_timer.cancel()
        
        if controller:
            controller.stop()
        
        if c_process:
            try:
                c_process.terminate()  # Terminate C subprocess
                # Wait for process to finish
                wait_time = 5
                for _ in range(wait_time * 10):
                    if c_process.poll() is not None:
                        break
                    time.sleep(0.1)
                else:
                    # Force kill if process doesn't terminate
                    c_process.kill()
                    print_red("C process had to be killed")
                
                print_green("C process terminated")
            except Exception as e:
                print_red(f"Error terminating C process: {e}")
        
        print_green("Application finished")

if __name__ == "__main__":
    main()