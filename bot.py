import asyncio
import os

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
    chat_id = update.effective_chat.id
    try:
        # Отправляем команду на начало измерений
        controller.send_command(b'start')
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
    await query.message.reply_text("Измерения начаты")
    """ТУТ БУДУТ ИЗМЕРЕНИЯ"""
    controller = context.bot_data.get('lora_controller')
    if not controller:
        try:
            controller = LoraController()
            controller.start()
            context.bot_data['lora_controller'] = controller
            await query.message.reply_text("Контроллер LoRa инициализирован")
        except Exception as e:
            await query.message.reply_text(f"Ошибка инициализации: {str(e)}")
            return

    # Запускаем асинхронную задачу для работы с LoRa
    asyncio.create_task(handle_lora_communication(controller, update, context))
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