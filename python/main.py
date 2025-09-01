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
# The measurement time of one sensor
# This is done because the MQ - 7 takes time to heat up
BEACON_TIME = 5

# Глобальные переменные для управления потоками
survey_timer: Optional[threading.Timer] = None
running = True

def data_survey(controller):
    """Функция для опроса данных сенсора"""
    try:
        command = f'st {BEACON_TIME} fn'
        controller.send_command(command.encode())
    except Exception as e:
        print_red(f"Error in data_survey: {e}")

def schedule_next_survey(controller):
    """Планирование следующего опроса"""
    global survey_timer
    if running:
        survey_timer = threading.Timer(SURVEY_TIME, data_survey, args=(controller,))
        survey_timer.daemon = True  # Поток завершится с основным программой
        survey_timer.start()

def load_sensor_config(config_path):
    """Загрузка конфигурации сенсоров из файла"""
    sensors = []
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):  # Пропускаем пустые строки и комментарии
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
    """Получение корневой директории проекта"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_executable_path():
    """Получение пути к исполняемому файлу"""
    return os.path.join(get_project_root(), 'file_c', 'bin', 'lora_app')

def signal_handler(sig, frame):
    """Обработчик сигналов для graceful shutdown"""
    global running
    print_red("\nReceived shutdown signal. Shutting down...")
    running = False
    if survey_timer:
        survey_timer.cancel()

def main():
    global running, survey_timer
   
    print_green('Starting program')

    # Установка обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Build C files
    if compile_lora_app():
        print_green('The binary file has been successfully compiled')
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

    # Launching the C program
    controller = None
    c_process = None
    
    try:
        exe_file = get_executable_path()
        
        # Проверяем существование исполняемого файла
        if not os.path.exists(exe_file):
            print_red(f"Executable file not found: {exe_file}")
            sys.exit(1)
        
        c_process = subprocess.Popen([exe_file])
        
        print_green(f"Started C process with PID: {c_process.pid}")
        time.sleep(2)  # Give the C program time to set up sockets

        controller = LoraController()
        controller.start()  # Start the background listener

        print_green("Starting main application loop")
        
        # Запускаем первый опрос
        schedule_next_survey(controller)

        # Main loop
        while running:
            try:
                message = controller.get_message()  # Checking and receiving the message
                
                if message: 
                    print_green(f"Received data: {message} | {time.strftime('%H:%M:%S', time.localtime())}")
                    # Здесь можно добавить обработку сообщения и сохранение в БД

                # Проверяем состояние соединений
                if not controller.cmd_socket and not controller.data_socket:
                    print_red("Both connections lost. Exiting")
                    break

                time.sleep(0.1)  # Main loop delay
                
            except Exception as e:
                print_red(f"Error in main loop: {e}")
                time.sleep(1)  # Задержка при ошибке

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
                c_process.terminate()  # Terminate the C subprocess
                # Ждем завершения процесса
                wait_time = 5
                for _ in range(wait_time * 10):
                    if c_process.poll() is not None:
                        break
                    time.sleep(0.1)
                else:
                    # Если процесс не завершился, принудительно убиваем
                    c_process.kill()
                    print_red("C process had to be killed")
                
                print_green("C process terminated")
            except Exception as e:
                print_red(f"Error terminating C process: {e}")
        
        print_green("Application finished")

if __name__ == "__main__":
    main()