import subprocess
import os
import sys
import time
import threading
import signal
from typing import Optional, List, Tuple

# Import modules
from compile_lora_app import compile_lora_app
from sender import LoraController
from database import SensorDatabase
from terminal_output import print_green, print_red

CONFIG_SENSOR = 'sensor.conf'
ERROR_MESSAGE_LOG = 'error_message.log'
SURVEY_TIME = 5*60
BEACON_TIME = 2*60

# Global variables for thread management
survey_timer: Optional[threading.Timer] = None
running = True

def data_survey(controller: LoraController) -> None:
    """Poll sensor data and schedule next survey"""
    try:
        command = f'st {BEACON_TIME} fn'
        controller.send_command(command.encode())

    except Exception as e:
        print_red(f"Error in data_survey: {e}")
    finally:
        if running:
            schedule_next_survey(controller)

def schedule_next_survey(controller: LoraController) -> None:
    """Schedule the next survey"""
    global survey_timer
    survey_timer = threading.Timer(SURVEY_TIME, data_survey, args=(controller,))
    survey_timer.daemon = True
    survey_timer.start()

def load_sensor_config(config_path: str) -> Optional[List[Tuple[str, str]]]:
    """Load sensor configuration from file"""
    sensors = []
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    if '@' in line:
                        sensor_id, sensor_location = line.split('@', 1)
                        sensors.append((sensor_id.strip(), sensor_location.strip()))
                    else:
                        print_red(f'Invalid format in config file at line {line_num}: {line}')
        return sensors
    except FileNotFoundError:
        print_red(f'The sensor configuration file was not found at {config_path}')
        return None
    except Exception as e:
        print_red(f'Error reading config file: {str(e)}')
        return None

def get_project_root() -> str:
    """Get project root directory"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_executable_path() -> str:
    """Get path to executable file"""
    return os.path.join(get_project_root(), 'file_c', 'bin', 'lora_app')

def signal_handler(sig: int, frame) -> None:
    """Signal handler for graceful shutdown"""
    global running
    print_red("\nReceived shutdown signal. Shutting down...")
    running = False
    if survey_timer:
        survey_timer.cancel()

def filter_string(s: str) -> bool:
    """Validate message format"""
    parts = s.strip().split()
    if len(parts) != 3:
        return False
    
    # Validate sensor ID
    if not parts[0].isdigit():
        return False
    
    # Validate measurement value (float with decimal point)
    try:
        float_val = float(parts[1])
        if '.' not in parts[1]:
            return False
    except ValueError:
        return False
    
    # Validate timestamp
    if not parts[2].isdigit():
        return False
        
    return True

def wait_for_initialization(controller: LoraController, timeout: int = 10) -> bool:
    """Wait for LoRa initialization with timeout"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        message = controller.get_message()
        if message == 'Lora init':
            return True
        time.sleep(0.5)
    return False

def main() -> None:
    global running, survey_timer
    
    print_green('Starting program')

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Build C files
    if not compile_lora_app():
        print_red('Binary file compilation error')
        sys.exit(1)
    print_green('Binary file compiled successfully')

    # Create database
    sensor_db = SensorDatabase()
    
    # Load sensor configuration
    config_path = os.path.join(get_project_root(), CONFIG_SENSOR)
    err_log_path = os.path.join(get_project_root(), ERROR_MESSAGE_LOG)
    sensors = load_sensor_config(config_path)
 
    if not sensors:
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
        
        if not os.path.exists(exe_file):
            print_red(f"Executable file not found: {exe_file}")
            sys.exit(1)
        
        c_process = subprocess.Popen([exe_file])
        
        print_green(f"Started C process with PID: {c_process.pid}")
        time.sleep(2)

        controller = LoraController()
        controller.start()

        # Wait for initialization with timeout
        if not wait_for_initialization(controller):
            print_red('The LoRa is not initialized')
            sys.exit(1)
            
        print_green("The LoRa has been successfully initialized")
        
        # Start first survey
        data_survey(controller)
        print_green("Starting main application loop")

        # Main loop
        while running:
            try:
                message = controller.get_message()
                
                if message: 
                    if filter_string(message):
                        print_green(f"Received: {message} | {time.strftime('%H:%M:%S')}")
                        sensor_id, value, co2_level = message.strip().split()
                        sensor_db.add_measurement(sensor_id, value, co2_level)
                    else:
                        # Log invalid messages
                        print_red(f"Received ERROR: {message} | {time.strftime('%H:%M:%S')}")
                        with open(err_log_path, 'a', encoding='utf-8') as f:
                            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

                time.sleep(0.1)
                
            except Exception as e:
                with open(err_log_path, 'a', encoding='utf-8') as f:
                            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Error in main loop: {e}\n")
                print_red(f"Error in main loop: {e}")
                time.sleep(1)

    except ConnectionRefusedError:
        print_red("Could not start the controller. Aborting")
    except Exception as e:
        print_red(f"Unexpected error: {e}")
    finally:
        # Cleanup resources
        running = False
        
        if survey_timer:
            survey_timer.cancel()
        
        if controller:
            controller.stop()
        
        if c_process:
            try:
                c_process.terminate()
                c_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                c_process.kill()
                print_red("C process had to be killed")
            except Exception as e:
                print_red(f"Error terminating C process: {e}")
        
        sensor_db.close()
        print_green("Application finished")

if __name__ == "__main__":
    main()