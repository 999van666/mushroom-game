import asyncio, os
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from dotenv import load_dotenv
load_dotenv()
TOKEN=os.getenv("BOT_TOKEN"); WEBAPP_URL=os.getenv("WEBAPP_URL")
if not TOKEN: raise RuntimeError("BOT_TOKEN is not configured")
if not WEBAPP_URL: raise RuntimeError("WEBAPP_URL is not configured")
dp=Dispatcher()
@dp.message(CommandStart())
async def start(message:Message):
    kb=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🍄 Открыть Грибалку",web_app=WebAppInfo(url=WEBAPP_URL))]],resize_keyboard=True)
    await message.answer("🍄 Добро пожаловать в «Грибалку»!\n\nИщи грибы, повышай уровень и собирай коллекцию.",reply_markup=kb)
async def main():
    await dp.start_polling(Bot(TOKEN))
if __name__=="__main__": asyncio.run(main())
