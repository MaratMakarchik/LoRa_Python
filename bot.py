import asyncio
import os
import subprocess

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from dotenv import load_dotenv

from sender import LoraController

load_dotenv()

# Токен вашего бота (замените на реальный)
BOT_TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущен.", reply_markup=start_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await go_on(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await go_on(update, context)


async def handle_lora_communication(controller, update, context):
    chat_id = update.message.chat_id
    try:
        # Отправляем команду на начало измерений
        controller.send_command(b'10 1')
        await context.bot.send_message(chat_id, "Команда 'start' отправлена")

        # Цикл получения сообщений
        while True:
            message = controller.get_message()
            if message:
                await context.bot.send_message(chat_id, f"Получены данные: {message}")
            await asyncio.sleep(1)  # Неблокирующая задержка

    except Exception as e:
        await context.bot.send_message(chat_id, f"Ошибка: {str(e)}")
    finally:
        controller.stop()
        context.bot_data.pop('lora_controller', None)
        await context.bot.send_message(chat_id, "Контроллер LoRa остановлен")


async def start_measure(update, context):
    query = update.callback_query
    await query.answer()
    if 'lora_process' in context.bot_data:
        context.bot_data['lora_process'].terminate()
        context.bot_data['lora_process'].wait()
        del context.bot_data['lora_process']

    if 'lora_controller' in context.bot_data:
        context.bot_data['lora_controller'].stop()
        del context.bot_data['lora_controller']

        # Удаляем старые сокеты
    for sock in ['/tmp/lora_cmd.sock', '/tmp/lora_data.sock']:
        try:
            os.unlink(sock)
        except FileNotFoundError:
            pass

    # Получаем абсолютный путь к lora_app
    script_dir = os.path.dirname(os.path.abspath(__file__))
    lora_app_path = os.path.join(script_dir, "lora_app")

    # Запускаем C-программу как подпроцесс
    if 'lora_process' not in context.bot_data:
        try:
            lora_process = subprocess.Popen([lora_app_path])
            context.bot_data['lora_process'] = lora_process
            await asyncio.sleep(2)  # Даем время на создание сокетов
            await query.message.reply_text(f"Запущен процесс lora_app с PID: {lora_process.pid}")
        except Exception as e:
            await query.message.reply_text(f"Ошибка запуска lora_app: {str(e)}")
            return

    try:
        # Проверяем существование сокетов
        for sock_path in ['/tmp/lora_cmd.sock', '/tmp/lora_data.sock']:
            if not os.path.exists(sock_path):
                await query.message.reply_text(f"Сокет {sock_path} не найден!")
                return

        # Создаем контроллер
        controller = LoraController()
        controller.start()
        context.bot_data['lora_controller'] = controller
        await query.message.reply_text("Контроллер LoRa инициализирован")
    except Exception as e:
        await query.message.reply_text(f"Ошибка инициализации: {str(e)}")
        return

    await query.message.reply_text("Измерения начаты")
    asyncio.create_task(handle_lora_communication(controller, query, context))

    await go_on(update, context)


async def go_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        update_query = update
    else:
        update_query = update.callback_query
    await update_query.message.reply_text("Нажимайте, кнопку", reply_markup=start_markup)


def main():
    # Создаем приложение бота
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Регистрируем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    application.add_handler(CallbackQueryHandler(start_measure, pattern="start_measuring"))
    # Запускаем бота в режиме polling
    application.run_polling()


if __name__ == "__main__":
    start_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Начать измерения",
                                                                          callback_data="start_measuring")]])
    main()
