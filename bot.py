import os
import time
import socket
import subprocess
import threading
import queue
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from dotenv import load_dotenv

# Загружаем переменные окружения (BOT_TOKEN)
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Настройка логирования для отладки
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Класс для управления LoRa (из sender.py) ---
class LoraController:
    """
    Управляет LoRa-связью, используя отдельные сокеты для команд и данных.
    Приём данных обрабатывается в фоновом потоке без блокировки.
    """
    def __init__(self):
        self.cmd_socket = None
        self.data_socket = None
        self.data_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.receiver_thread = None

        try:
            logger.info("Connecting to command socket...")
            self.cmd_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.cmd_socket.connect('/tmp/lora_cmd.sock')
            logger.info("Connected to command socket.")

            logger.info("Connecting to data socket...")
            self.data_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.data_socket.connect('/tmp/lora_data.sock')
            logger.info("Connected to data socket.")

        except ConnectionRefusedError:
            logger.error("Connection refused. Make sure the C program is running.")
            self.close_sockets()
            raise

    def start(self):
        """Запускает фоновый поток для приёма данных."""
        if self.receiver_thread is None:
            self.stop_event.clear()
            self.receiver_thread = threading.Thread(target=self._data_receiver_loop, daemon=True)
            self.receiver_thread.start()
            logger.info("Data receiver thread started.")

    def _data_receiver_loop(self):
        """Основной цикл потока-приёмника."""
        while not self.stop_event.is_set():
            if not self.data_socket:
                break
            try:
                self.data_socket.settimeout(1.0)
                len_byte = self.data_socket.recv(1)
                if not len_byte:
                    logger.warning("Data connection closed by server.")
                    self.data_socket = None
                    break
                
                length = len_byte[0]
                data = self.data_socket.recv(length)
                
                processed_data = self._process_data(data)
                self.data_queue.put(processed_data)

            except socket.timeout:
                continue
            except socket.error as e:
                logger.error(f"Socket error on receive: {e}")
                self.data_socket = None
                break
        logger.info("Data receiver thread stopped.")

    def stop(self):
        """Останавливает поток-приёмник и закрывает сокеты."""
        logger.info("Stopping controller...")
        if self.receiver_thread and self.receiver_thread.is_alive():
            self.stop_event.set()
            self.receiver_thread.join()
        self.close_sockets()

    def send_command(self, data: bytes):
        """Отправляет команду через установленное соединение."""
        if not self.cmd_socket:
            logger.warning("Command socket is not connected.")
            return
        try:
            self.cmd_socket.sendall(bytes([len(data)]) + data)
            logger.info(f"Sent command: {data.decode()}")
        except BrokenPipeError:
            logger.error("Connection lost while sending command.")
            self.cmd_socket = None

    def get_message(self):
        """Извлекает одно сообщение из очереди (неблокирующий вызов)."""
        try:
            return self.data_queue.get_nowait()
        except queue.Empty:
            return None

    def _process_data(self, raw_data):
        """Обрабатывает сырые байты в строку."""
        if not raw_data:
            return None
        try:
            return raw_data.decode('utf-8')
        except UnicodeDecodeError:
            return list(raw_data)

    def close_sockets(self):
        """Корректно закрывает все сокеты."""
        if self.cmd_socket:
            self.cmd_socket.close()
            self.cmd_socket = None
            logger.info("Command socket closed.")
        if self.data_socket:
            self.data_socket.close()
            self.data_socket = None
            logger.info("Data socket closed.")

# --- Функции для планировщика задач ---

async def check_lora_messages(context: ContextTypes.DEFAULT_TYPE):
    """Задача, которая проверяет наличие сообщений от LoRa и отправляет их пользователю."""
    controller = context.bot_data.get('controller')
    chat_id = context.job.chat_id
    if not controller:
        return

    message = controller.get_message()
    if message:
        logger.info(f"Received from LoRa: {message}")
        await context.bot.send_message(chat_id=chat_id, text=f"Получены данные от датчика: {message}")

# --- Обработчики команд и кнопок ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение с кнопкой."""
    start_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("Запросить данные с датчика (10 1)", callback_data="request_data")
    ]])
    await update.message.reply_text("Бот готов к работе. Нажмите кнопку, чтобы отправить команду на датчик.", reply_markup=start_markup)

async def request_data_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатие на кнопку 'Запросить данные'."""
    query = update.callback_query
    await query.answer()

    controller = context.bot_data.get('controller')
    chat_id = query.message.chat_id

    if not controller:
        await query.edit_message_text("Ошибка: LoRa-контроллер не инициализирован.")
        return

    # Отправка команды "10 1"
    command_to_send = "10 1"
    controller.send_command(command_to_send.encode('utf-8'))
    await query.edit_message_text(f"Команда '{command_to_send}' отправлена. Ожидаю ответ от датчика...")

    # Удаляем старую задачу, если она есть, чтобы избежать дублирования
    current_jobs = context.job_queue.get_jobs_by_name(f"lora_listener_{chat_id}")
    for job in current_jobs:
        job.schedule_removal()
        logger.info(f"Removed old job: {job.name}")

    # Запускаем повторяющуюся задачу для проверки сообщений от LoRa
    context.job_queue.run_repeating(
        check_lora_messages,
        interval=2,  # Проверять каждые 2 секунды
        chat_id=chat_id,
        name=f"lora_listener_{chat_id}"
    )

async def stop_listening(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Останавливает прослушивание сообщений от LoRa."""
    chat_id = update.message.chat_id
    jobs = context.job_queue.get_jobs_by_name(f"lora_listener_{chat_id}")
    
    if not jobs:
        await update.message.reply_text("Прослушивание уже остановлено.")
        return

    for job in jobs:
        job.schedule_removal()

    await update.message.reply_text("Прослушивание сообщений от датчика остановлено.")


def main():
    """Основная функция для запуска бота и LoRa контроллера."""
    c_process = None
    controller = None
    try:
        # Компилируем C-программу (если нужно)
        # Убедитесь, что wiringPi установлен: sudo apt-get install wiringpi
        logger.info("Compiling C code...")
        compile_process = subprocess.run(
            ["sudo", "gcc", "-o", "lora_app", "main.c", "LoRa.c", "-lwiringPi"],
            capture_output=True, text=True
        )
        if compile_process.returncode != 0:
            logger.error(f"C compilation failed:\n{compile_process.stderr}")
            return
        logger.info("C code compiled successfully.")
        
        # Запускаем C-программу в фоновом режиме
        # Используем sudo, так как wiringPi часто требует прав суперпользователя
        c_process = subprocess.Popen(["sudo", "./lora_app"])
        logger.info(f"Started C process with PID: {c_process.pid}")
        time.sleep(2)  # Даём время на создание сокетов

        # Инициализируем LoRa-контроллер
        controller = LoraController()
        controller.start()  # Запускаем фоновый поток для прослушивания

        # Создаём приложение бота
        application = Application.builder().token(BOT_TOKEN).build()

        # Сохраняем контроллер в контексте бота для доступа в обработчиках
        application.bot_data['controller'] = controller

        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("stop", stop_listening))
        application.add_handler(CallbackQueryHandler(request_data_callback, pattern="^request_data$"))
        
        logger.info("Starting bot polling...")
        application.run_polling()

    except ConnectionRefusedError:
        logger.critical("Could not connect to the C application's sockets. Aborting.")
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}")
    finally:
        # Корректное завершение работы
        if controller:
            controller.stop()
        if c_process:
            # Используем sudo для завершения процесса, если он был запущен с sudo
            subprocess.run(["sudo", "kill", str(c_process.pid)])
            c_process.wait()
            logger.info("C process terminated.")
        logger.info("Application finished.")

if __name__ == "__main__":
    main()