import socket
import time
import errno

class LoraController:
    def __init__(self):
        """Инициализирует и подключает сокеты при создании объекта."""
        self.cmd_socket = None
        self.data_socket = None
        try:
            # Подключаем сокет для отправки команд
            self.cmd_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.cmd_socket.connect('/tmp/lora_cmd.sock')
            print("Connected to command socket.")

            # Подключаем сокет для приема данных
            self.data_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.data_socket.connect('/tmp/lora_data.sock')
            self.data_socket.setblocking(False) # Делаем неблокирующим для чтения
            print("Connected to data socket.")

        except ConnectionRefusedError:
            print("Connection refused. Make sure the C program is running and waiting for connections.")
            self.close() # Закрываем сокеты, если что-то пошло не так
            raise

    def send_command(self, data: bytes):
        """Отправляет команду через установленное соединение."""
        if not self.cmd_socket:
            print("Command socket is not connected.")
            return
        try:
            # Отправляем длину (1 байт), а затем сами данные
            self.cmd_socket.sendall(bytes([len(data)]) + data)
        except BrokenPipeError:
            print("Connection lost while sending command.")
            self.cmd_socket = None


    def receive_data(self):
        """Читает данные из неблокирующего сокета."""
        if not self.data_socket:
            return None
        
        try:
            # Сначала читаем длину сообщения (1 байт)
            len_byte = self.data_socket.recv(1)
            if not len_byte:
                print("Data connection closed by server.")
                self.data_socket = None
                return None
            
            length = len_byte[0]
            # Читаем ровно столько байт, сколько указано в длине
            data = self.data_socket.recv(length)
            return data

        except BlockingIOError:
            # Это нормально для неблокирующего сокета, данных просто нет
            return None
        except socket.error as e:
            print(f"Socket error on receive: {e}")
            self.data_socket = None
            return None

    def process_data(self, raw_data):
        """Обрабатывает сырые байты в строку или список."""
        if not raw_data:
            return None
        try:
            return raw_data.decode('utf-8')
        except UnicodeDecodeError:
            return list(raw_data)

    def run(self):
        """Основной цикл работы."""
        print("Starting controller loop...")
        try:
            while True:
                # Пример отправки команды каждые 5 секунд
                # if int(time.time()) % 5 == 0:
                #     self.send_command(b'Hello from Python!')
                #     time.sleep(1) # Чтобы не отправлять много раз в одну секунду

                raw_data = self.receive_data()
                if raw_data is not None:
                    processed = self.process_data(raw_data)
                    print(f"Received: {processed}")
                
                # Если оба соединения потеряны, выходим
                if not self.cmd_socket and not self.data_socket:
                    print("Both connections are lost. Exiting.")
                    break

                time.sleep(0.1) # Небольшая задержка, чтобы не нагружать процессор

        finally:
            self.close()

    def close(self):
        """Корректно закрывает все сокеты."""
        if self.cmd_socket:
            self.cmd_socket.close()
            self.cmd_socket = None
            print("Command socket closed.")
        if self.data_socket:
            self.data_socket.close()
            self.data_socket = None
            print("Data socket closed.")


if __name__ == "__main__":
    try:
        controller = LoraController()
        controller.run()
    except ConnectionRefusedError:
        print("Could not start controller.")
    except KeyboardInterrupt:
        print("\nExiting.")
