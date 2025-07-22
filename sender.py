import socket
import struct
import os

class LoraController:
    def __init__(self):
        self.cmd_socket = self.connect_socket('/tmp/lora_cmd.sock')
        self.data_socket = self.connect_socket('/tmp/lora_data.sock')
        
    def connect_socket(self, path):
        if os.path.exists(path):
            os.unlink(path)
            
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(path)
        sock.listen(1)
        return sock

    def send_command(self, data):
        """Отправка данных в C-программу для передачи через LoRa"""
        if not isinstance(data, bytes):
            data = bytes(data)
        
        client, _ = self.cmd_socket.accept()
        client.send(bytes([len(data)]))  # Отправляем длину
        client.send(data)                # Отправляем данные
        client.close()

    def receive_data(self):
        """Получение данных из C-программы"""
        client, _ = self.data_socket.accept()
        
        # Читаем длину данных
        len_data = client.recv(1)
        if not len_data:
            return None
            
        length = len_data[0]
        # Читаем сами данные
        data = client.recv(length)
        client.close()
        return data

    def process_data(self, raw):
        """Обработка сырых данных от LoRa"""
        try:
            return raw.decode('utf-8')
        except UnicodeDecodeError:
            return list(raw)  # Возвращаем как массив чисел

    def run(self):
        while True:
            # Проверяем входящие данные
            raw_data = self.receive_data()
            if raw_data:
                processed = self.process_data(raw_data)
                print(f"Received: {processed}")
                
            # Здесь можно добавить отправку по какому-либо триггеру
            # self.send_command([0x01, 0x02, 0x03])

if __name__ == "__main__":
    controller = LoraController()
    controller.run()