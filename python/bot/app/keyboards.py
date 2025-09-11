from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_amount_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="10"), KeyboardButton(text="25")],
            [KeyboardButton(text="50"), KeyboardButton(text="100")]
        ],
        resize_keyboard=True
    )
    return keyboard