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
    print("---{:^MES_LEN}---".format("start program"))

    #Сборка и выполнения файлов Си
    
    if compile_lora_app():
        print("---{:^MES_LEN}---".format("The bin file has been successfully compiled"))
    else:
        print("---{:^MES_LEN}---".format("bin file assembly error"))
        sys.exit(1)
    
    #Создание и заполнение БД
    sensor_db = SensorDatabase()
    with open (CONFIG_SENSOR,encoding='utf-8') as f:
        if f.closed:
             print("---{:^MES_LEN}---".format("the sensor configuration file was not found or has not been opened"))
             sys.exit(1)
        else:
            while True:
                content = f.readline()
                if not content:
                    break
                sensor_id, sensor_location = content.split("@")
                sensor_db.add_sensor(sensor_id,sensor_location)
            


if __name__ == "__main__":
	main()








if __name__ == "__main__":
    main()