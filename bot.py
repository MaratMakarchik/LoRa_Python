import os

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from dotenv import load_dotenv
load_dotenv()

# Токен вашего бота (замените на реальный)
BOT_TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущен.", reply_markup=start_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await go_on(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await go_on(update, context)


async def start_measure(update, context):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Измерения начаты")
    """ТУТ БУДУТ ИЗМЕЕРЕНИЯ"""
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