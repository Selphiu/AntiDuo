from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
import logging
import sqlite3
import random

addword_router = Router()
dp = Dispatcher()
router = Router()
dp.include_router(router) 

class AddWord(StatesGroup):
    waiting_word = State()
    test_antw = State()

class TestState(StatesGroup):
    waiting_for_answer = State()
    correct_translation = State()

class DeleteState(StatesGroup):
    waiting_for_word_selection = State()

GREETING_TEXT = "Willkommen, Meister! Ich bin Leyna, Ihre persönliche Anime-Dienstmädchen-Assistentin für den Sprachunterricht~! ♡"
WORD_ADDED_TEXT = "Wunderbar, Meister~! Ich habe das Wort '{word}' mit der Übersetzung '{translation}' zu Ihrer Sammlung hinzugefügt! ♡"
ERROR_FORMAT_TEXT = "Oh nein, Meister! Das Format ist nicht korrekt~! Bitte geben Sie es im Format ein: <Wort> - <Übersetzung>"
NO_WORDS_TEXT = "Meister, Sie haben noch keine Wörter gespeichert~! Bitte fügen Sie zuerst einige hinzu."
NEED_MORE_WORDS_TEXT = "Meister~! Sie brauchen mindestens 4 Wörter für einen Test. Bitte fügen Sie mehr hinzu! ♡"
TEST_WORD_TEXT = "Wort: {word}\nBitte wählen Sie die richtige Übersetzung, Meister~!"
CORRECT_ANSWER_TEXT = "Richtig, Meister~! Sie sind so klug! ♡"
WRONG_ANSWER_TEXT = "Oh, das ist nicht richtig, Meister~! Die korrekte Antwort wäre: '{correct}'"
LIST_WORDS_TEXT = "Hier ist Ihre Wörterliste, Meister~! ♡\n\n{word_list}"
DELETE_WORD_TEXT = "Welches Wort möchten Sie löschen, Meister~?"
WORD_DELETED_TEXT = "Das Wort '{word}' wurde erfolgreich gelöscht, Meister~! ♡"
NO_WORD_FOUND_TEXT = "Oh nein! Das Wort wurde nicht gefunden, Meister~!"

@addword_router.message(lambda message: '-' in message.text)
async def word_inp(message: Message, state: FSMContext) -> None:
    try:
        userid = message.from_user.id
        word, translation = map(str.strip, message.text.split('-', maxsplit=1))

        if not word or not translation:
            raise ValueError("Ungültiges Eingabeformat.")
        
        await add(userid, word, translation)

        await message.answer(WORD_ADDED_TEXT.format(word=word, translation=translation))
    except Exception as e:
        await message.answer(ERROR_FORMAT_TEXT)

async def add(userid, word, translation):
    db = sqlite3.connect('wordbase.db')
    c = db.cursor()
    c.execute("INSERT INTO words (userid, word, translation) VALUES (?, ?, ?)", (userid, word, translation))
    db.commit()
    db.close()

async def add_user(userid):
    logging.info(f"Neuer Benutzer hinzugefügt: {userid}")
    db = sqlite3.connect('wordbase.db')
    c = db.cursor()
    
    c.execute("SELECT userid FROM words WHERE userid = ? LIMIT 1", (userid,))
    if not c.fetchone():
        c.execute("INSERT INTO words (userid, word, translation) VALUES (?, ?, ?)", 
                 (userid, "willkommen", "welcome"))
    
    db.commit()
    db.close()

async def testing(message: Message, userid, state: FSMContext):
    db = sqlite3.connect('wordbase.db')
    c = db.cursor()
    c.execute("SELECT word, translation FROM words WHERE userid = ? AND word IS NOT NULL AND translation IS NOT NULL", (userid,))
    words = c.fetchall()
    db.close()

    if not words:
        await message.answer(NO_WORDS_TEXT)
        return

    if len(words) < 4:
        await message.answer(NEED_MORE_WORDS_TEXT)
        return
    correct_word, correct_translation = random.choice(words)

    await state.update_data(correct_word=correct_word, correct_translation=correct_translation)

    all_translations = [translation for _, translation in words if translation]
    if correct_translation in all_translations: all_translations.remove(correct_translation)

    try:
        fake_translations = random.sample(all_translations, min(3, len(all_translations)))
    except ValueError:
        fake_translations = all_translations

    variants = [correct_translation] + fake_translations
    random.shuffle(variants)

    buttons = [
        InlineKeyboardButton(text=variant, callback_data=f"answer_{variant}")
        for variant in variants
    ]

    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await message.answer(
        TEST_WORD_TEXT.format(word=correct_word),
        reply_markup=markup
    )

    await state.set_state(TestState.waiting_for_answer)

@addword_router.callback_query(lambda callback: callback.data.startswith("answer_"), TestState.waiting_for_answer)
async def handle_answer(callback: CallbackQuery, state: FSMContext):
    selected_translation = callback.data.replace("answer_", "")

    data = await state.get_data()
    correct_translation = data.get("correct_translation")
    correct_word = data.get("correct_word")

    if selected_translation == correct_translation:
        await callback.message.answer(CORRECT_ANSWER_TEXT)
        
        kb = [
            [
                InlineKeyboardButton(text="Noch ein Test", callback_data="next_test"),
                InlineKeyboardButton(text="Zurück zum Menü", callback_data="back_to_menu")
            ]
        ]
        markup = InlineKeyboardMarkup(inline_keyboard=kb)
        await callback.message.answer("Möchten Sie einen weiteren Test machen, Meister~?", reply_markup=markup)
    else:
        await callback.message.answer(WRONG_ANSWER_TEXT.format(correct=correct_translation))
        
        kb = [
            [
                InlineKeyboardButton(text="Noch ein Test", callback_data="next_test"),
                InlineKeyboardButton(text="Zurück zum Menü", callback_data="back_to_menu")
            ]
        ]
        markup = InlineKeyboardMarkup(inline_keyboard=kb)
        await callback.message.answer("Möchten Sie einen weiteren Test machen, Meister~?", reply_markup=markup)

    await state.clear()

@addword_router.callback_query(lambda callback: callback.data == "next_test")
async def next_test(callback: CallbackQuery, state: FSMContext):
    await testing(callback.message, callback.from_user.id, state)
    await callback.answer()

@addword_router.callback_query(lambda callback: callback.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    from main import send_main_menu
    await send_main_menu(callback.message, callback.from_user.id)
    await callback.answer()

async def list_words(message: Message, userid):
    db = sqlite3.connect('wordbase.db')
    c = db.cursor()
    c.execute("SELECT word, translation FROM words WHERE userid = ? AND word IS NOT NULL AND translation IS NOT NULL", (userid,))
    words = c.fetchall()
    db.close()

    if not words:
        await message.answer(NO_WORDS_TEXT)
        return
    
    word_list = "\n".join([f"• {word} - {translation}" for word, translation in words])
    await message.answer(LIST_WORDS_TEXT.format(word_list=word_list))

async def delete_word(message: Message, userid, state: FSMContext):
    db = sqlite3.connect('wordbase.db')
    c = db.cursor()
    c.execute("SELECT id, word, translation FROM words WHERE userid = ? AND word IS NOT NULL AND translation IS NOT NULL", (userid,))
    words = c.fetchall()
    db.close()

    if not words:
        await message.answer(NO_WORDS_TEXT)
        return

    buttons = []
    for word_id, word, translation in words:
        buttons.append([InlineKeyboardButton(
            text=f"{word} - {translation}", 
            callback_data=f"delete_{word_id}"
        )])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(DELETE_WORD_TEXT, reply_markup=markup)
    await state.set_state(DeleteState.waiting_for_word_selection)

@addword_router.callback_query(lambda callback: callback.data.startswith("delete_"), DeleteState.waiting_for_word_selection)
async def handle_delete_word(callback: CallbackQuery, state: FSMContext):
    word_id = callback.data.split("_")[1]
    
    db = sqlite3.connect('wordbase.db')
    c = db.cursor()
    c.execute("SELECT word FROM words WHERE id = ?", (word_id,))
    word_data = c.fetchone()
    
    if word_data:
        word = word_data[0]
        c.execute("DELETE FROM words WHERE id = ?", (word_id,))
        db.commit()
        await callback.message.answer(WORD_DELETED_TEXT.format(word=word))
    else:
        await callback.message.answer(NO_WORD_FOUND_TEXT)
    
    db.close()
    await state.clear()

    from main import send_main_menu
    await send_main_menu(callback.message, callback.from_user.id)
    await callback.answer()
