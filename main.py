from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
import logging
import sqlite3
from func import addword_router, add_user, testing, list_words, delete_word, GREETING_TEXT 

API_TOKEN = ''
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
dp.include_router(addword_router)

logging.basicConfig(level=logging.DEBUG, filename="py_log.log", filemode="w")

with sqlite3.connect('wordbase.db') as db:
    c = db.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS words (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        userid INTEGER NOT NULL,
        word TEXT,
        translation TEXT
    )""")
    db.commit()
    logging.debug("Tabelle 'words' initialisiert falls sie nicht existierte.")

class MonitorCallback(CallbackData, prefix="monitor"):
    action: str

@dp.message(CommandStart())
async def start_command(message: Message):
    userid = message.from_user.id
    await add_user(userid)
    await message.answer(GREETING_TEXT)
    await send_main_menu(message, userid)

async def send_main_menu(message: Message, userid):
    kb = [
        [
            InlineKeyboardButton(text="🖋️ Wort hinzufügen", callback_data=MonitorCallback(action="add").pack()),
            InlineKeyboardButton(text="📝 Test starten", callback_data=MonitorCallback(action="test").pack()),
        ],
        [
            InlineKeyboardButton(text="📚 Wörterliste", callback_data=MonitorCallback(action="list").pack()),
            InlineKeyboardButton(text="❌ Wort löschen", callback_data=MonitorCallback(action="delete").pack())
        ]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=kb)
    await message.answer("Bitte wählen Sie eine Option, Meister~! ♡", reply_markup=markup)

@dp.callback_query(MonitorCallback.filter())
async def handle_callback(callback: CallbackQuery, callback_data: MonitorCallback, state: FSMContext):
    action = callback_data.action
    userid = callback.from_user.id

    if action == "add":
        await callback.message.answer("Bitte geben Sie ein Wort und seine Übersetzung im Format ein: <Wort> - <Übersetzung>")
        await callback.answer()
    elif action == "test":
        await testing(callback.message, userid, state)
        await callback.answer()
    elif action == "list":
        await list_words(callback.message, userid)
        await callback.answer()
    elif action == "delete":
        await delete_word(callback.message, userid, state)
        await callback.answer()

@dp.message(Command("wort"))
async def word_command(message: Message):
    await message.answer("Bitte geben Sie ein Wort und seine Übersetzung im Format ein: <Wort> - <Übersetzung>")

@dp.message(Command("test"))
async def test_command(message: Message, state: FSMContext):
    await testing(message, message.from_user.id, state)

@dp.message(Command("liste"))
async def list_command(message: Message):
    await list_words(message, message.from_user.id)

@dp.message(Command("löschen"))
async def delete_command(message: Message, state: FSMContext):
    await delete_word(message, message.from_user.id, state)

@dp.message(Command("hilfe"))
async def help_command(message: Message):
    help_text = (
        "✨ *Leyna's Befehle* ✨\n\n"
        "/start - Starten Sie den Bot und zeigen Sie das Hauptmenü an\n"
        "/wort - Fügen Sie ein neues Wort hinzu\n"
        "/test - Starten Sie einen Worttest\n"
        "/liste - Zeigen Sie Ihre Wörterliste an\n"
        "/löschen - Löschen Sie ein Wort\n"
        "/hilfe - Zeigen Sie diese Hilfenachricht an\n\n"
        "Sie können auch einfach ein Wort und seine Übersetzung im Format eingeben: <Wort> - <Übersetzung>"
    )
    await message.answer(help_text, parse_mode="Markdown")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


a = 10
b = 100
if a == b:
    print("how")
elif a != b:
    print("yes")
else: 
    print("what")
