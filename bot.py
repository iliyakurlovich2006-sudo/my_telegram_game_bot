import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# Берём токен и URL из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

if not TOKEN or not RENDER_URL:
    raise ValueError("BOT_TOKEN или RENDER_EXTERNAL_URL не заданы")

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# --- Игровая логика ---
class GameState(StatesGroup):
    waiting_for_guess = State()

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Привет! Давай сыграем в «Угадай число»! Отправь /game чтобы начать.")

@dp.message(Command("game"))
async def game(message: types.Message, state: FSMContext):
    number = random.randint(1, 100)
    await state.update_data(number=number, attempts=0, max_attempts=5)
    await state.set_state(GameState.waiting_for_guess)
    await message.answer("Я загадал число от 1 до 100. У тебя 5 попыток. Попробуй угадать!")

@dp.message(GameState.waiting_for_guess)
async def guess(message: types.Message, state: FSMContext):
    data = await state.get_data()
    number = data["number"]
    attempts = data["attempts"]
    max_attempts = data["max_attempts"]

    try:
        user_guess = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введи целое число от 1 до 100.")
        return

    if user_guess < 1 or user_guess > 100:
        await message.answer("Число должно быть от 1 до 100!")
        return

    attempts += 1
    await state.update_data(attempts=attempts)

    if user_guess == number:
        await message.answer(f"Поздравляю! Ты угадал число {number} с {attempts} попытки(ок)! 🎉")
        await state.clear()
    elif attempts >= max_attempts:
        await message.answer(f"Ты проиграл. Я загадал число {number}. Попробуй ещё раз — /game!")
        await state.clear()
    else:
        hint = "больше" if user_guess < number else "меньше"
        await message.answer(f"Не угадал! Попытка {attempts}/{max_attempts}. Число {hint}. Попробуй ещё:")

@dp.message(Command("cancel"))
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Игра отменена. Напиши /game, чтобы сыграть заново.")

# --- Веб-сервер для вебхука ---
app = web.Application()
webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
webhook_handler.register(app, path=WEBHOOK_PATH)
setup_application(app, dp, bot=bot)

async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)

app.on_startup.append(on_startup)

if __name__ == "__main__":
    web.run_app(app, port=int(os.getenv("PORT", 8080)))