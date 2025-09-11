# handlers.py
from aiogram import types, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove

from python.bdrv.database import SensorDatabase
from app.keyboards import get_amount_keyboard

router = Router()
db = SensorDatabase()

class SensorStates(StatesGroup):
    waiting_for_amount = State()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        "Добро пожаловать! Введите количество запросов (от 1 до 100):",
        reply_markup=get_amount_keyboard()
    )
    await state.set_state(SensorStates.waiting_for_amount)

@router.message(SensorStates.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if 1 <= amount <= 100:
            # Получаем данные из БД
            measurements = db.get_measurements(limit=amount)
            
            if not measurements:
                await message.answer("В базе данных нет записей.", reply_markup=ReplyKeyboardRemove())
                await state.clear()
                return

            # Форматируем результаты
            response = ["Последние измерения:"]
            for i, meas in enumerate(measurements, 1):
                response.append(
                    f"{i}. 📅 {meas[5]} | "
                    f"📍 {meas[6]} | "
                    f"🌡 {meas[2]}°C | "
                    f"CO₂ {meas[3]}ppm | "
                    f"🔋 {meas[4]}V"
                )

            # Разбиваем на сообщения по 10 записей
            for i in range(0, len(response), 10):
                await message.answer("\n".join(response[i:i+10]), reply_markup=ReplyKeyboardRemove())

            await state.clear()
        else:
            await message.answer("Пожалуйста, введите число от 1 до 100:")
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число:")