import subprocess
import os
import sys
#--------------------------------------------------
from sender import LoraController
from autoassembly import compile_lora_app
from database import SensorDatabase
#--------------------------------------------------
MES_LEN = 90
CONFIG_SENSOR = 'sensor.conf'


def main():
    # Исправлено форматирование строки (f-строки)
    print(f"---{'start program':^{MES_LEN}}---")

    # Сборка и выполнение файлов Си
    if compile_lora_app():
        print(f"---{'The bin file has been successfully compiled':^{MES_LEN}}---")
    else:
        print(f"---{'bin file assembly error':^{MES_LEN}}---")
        sys.exit(1)
    
    # Создание и заполнение БД
    sensor_db = SensorDatabase()
    try:
        with open(CONFIG_SENSOR, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:  # Пропускаем пустые строки
                    # Добавляем проверку на наличие разделителя
                    if '@' in line:
                        sensor_id, sensor_location = line.split('@', 1)
                        sensor_db.add_sensor(sensor_id.strip(), sensor_location.strip())
                    else:
                        print(f"---{'Invalid format in config file':^{MES_LEN}}---")
    except FileNotFoundError:
        print(f"---{'the sensor configuration file was not found':^{MES_LEN}}---")
        sys.exit(1)
    except Exception as e:
        print(f"---{f'Error reading config file: {str(e)}':^{MES_LEN}}---")
        sys.exit(1)


if __name__ == "__main__":
    main()