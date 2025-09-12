import sqlite3
from datetime import datetime

class SensorDatabase:
    def __init__(self, db_name='sensors.db'):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()


    def create_tables(self):
        # Таблица с информацией о датчиках
        sensors_table_query = """
        CREATE TABLE IF NOT EXISTS sensors (
            sensor_id INTEGER PRIMARY KEY,
            location TEXT NOT NULL UNIQUE
        )
        """
        
        # Таблица с измерениями
        measurements_table_query = """
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id INTEGER NOT NULL,
            temperature REAL,
            co2_level INTEGER,
            Vcc REAL,
            timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (sensor_id) REFERENCES sensors (sensor_id)
        )
        """
        
        self.conn.execute(sensors_table_query)
        self.conn.execute(measurements_table_query)
        self.conn.commit()

    def add_sensor(self, sensor_id, location):
        """Добавление нового датчика в систему"""
        try:
            self.conn.execute(
                "INSERT INTO sensors (sensor_id, location) VALUES (?, ?)",
                (sensor_id, location)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Если датчик с таким ID или местоположением уже существует
            return False

    def add_measurement(self, sensor_id, temperature, co2_level, Vcc):
        """Добавление измерения от датчика"""
        # Проверяем, существует ли датчик
        cursor = self.conn.execute(
            "SELECT sensor_id FROM sensors WHERE sensor_id = ?", 
            (sensor_id,)
        )
        
        if cursor.fetchone() is None:
            raise ValueError(f"Датчик с ID {sensor_id} не зарегистрирован")
        
        # Добавляем измерение
        self.conn.execute(
            "INSERT INTO measurements (sensor_id, temperature, co2_level, Vcc) VALUES (?, ?, ?, ?)",
            (sensor_id, temperature, co2_level, Vcc)
        )
        self.conn.commit()

    def get_sensors(self):
        """Получение списка всех датчиков"""
        cursor = self.conn.execute("SELECT * FROM sensors")
        return cursor.fetchall()

    def get_measurements(self, sensor_id=None, hours=None, limit=100):
        """Получение измерений с возможностью фильтрации"""
        query = """
        SELECT m.*, s.location 
        FROM measurements m 
        JOIN sensors s ON m.sensor_id = s.sensor_id
        """
        params = []
        
        conditions = []
        if sensor_id:
            conditions.append(" m.sensor_id = ? ")
            params.append(sensor_id)
            
        if hours:
            conditions.append(" m.timestamp > datetime('now', ?) ")
            params.append(f"-{hours} hours")
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY m.timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor = self.conn.execute(query, params)
        return cursor.fetchall()

    def get_latest_measurement(self, sensor_id):
        """Получение последнего измерения для конкретного датчика"""
        query = """
        SELECT m.*, s.location 
        FROM measurements m 
        JOIN sensors s ON m.sensor_id = s.sensor_id
        WHERE m.sensor_id = ?
        ORDER BY m.timestamp DESC 
        LIMIT 1
        """
        cursor = self.conn.execute(query, (sensor_id,))
        return cursor.fetchone()

    def get_average_readings(self, sensor_id=None, hours=24):
        """Получение средних показаний за указанный период"""
        query = """
        SELECT 
            AVG(temperature) as avg_temp,
            AVG(co2_level) as avg_co2
        FROM measurements 
        WHERE timestamp > datetime('now', ?)
        """
        params = [f"-{hours} hours"]
        
        if sensor_id:
            query += " AND sensor_id = ?"
            params.append(sensor_id)
            
        cursor = self.conn.execute(query, params)
        result = cursor.fetchone()
        
        return {
            'avg_temperature': round(result[0], 2) if result[0] is not None else None,
            'avg_co2': round(result[1], 2) if result[1] is not None else None
        }

    def close(self):
        self.conn.close()
if __name__ == "__main__":
    db = SensorDatabase()
    
    # Добавляем датчики (делается один раз)
    db.add_sensor(1, "Комната 101")
    db.add_sensor(2, "Кухня")
    db.add_sensor(3, "Спальня")
    
    # Добавляем измерения
    db.add_measurement(1, 25.73, 450)
    db.add_measurement(2, 23.15, 500)
    db.add_measurement(1, 24.89, 460)
    db.add_measurement(3, 22.41, 420)
    
    # Получаем список всех датчиков
    print("Все датчики:")
    for sensor in db.get_sensors():
        print(sensor)
    
    # Получаем последние измерения
    print("\nПоследние измерения:")
    for measurement in db.get_measurements(limit=5):
        print(measurement)
    
    # Получаем средние показания за последние 24 часа
    averages = db.get_average_readings()
    print(f"\nСредние показания за 24 часа: Температура={averages['avg_temperature']}°C, CO2={averages['avg_co2']}ppm")
    
    # Получаем последнее измерение для датчика 1
    latest = db.get_latest_measurement(1)
    print(f"\nПоследнее измерение датчика 1: Температура={latest[2]}°C, CO2={latest[3]}ppm")
    
    db.close()