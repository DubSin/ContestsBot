import logging
import asyncio
import random
import sys
from datetime import datetime
from keys import BOT_TOKEN, HOOPS_ID, PASSWORD
from db import BoTDb
from aiogram import F
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram3_calendar import SimpleCalendar, simple_cal_callback
from aiogram import Dispatcher, Bot, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile

bot_db = BoTDb('participants.db')
dp = Dispatcher(storage=MemoryStorage())


class EnterState(StatesGroup):
    password = State()


class ContestState(StatesGroup):
    time = State()
    text = State()
    image = State()
    fake = State()


@dp.message(Command(commands=["admin"]))
async def start_menu(message: types.Message, state: FSMContext):
    await message.answer('Введите пароль:')
    await state.set_state(EnterState.password)


@dp.message(EnterState.password)
async def password(message: types.Message, state: FSMContext):
    await state.update_data(password=message.text)
    dat = await state.get_data()
    if dat['password'] == PASSWORD:
        admin_btn_1 = types.InlineKeyboardButton(text='Создать новый розыгрыш', callback_data='event')
        admin_btn_2 = types.InlineKeyboardButton(text='Удалить текущий розыгрыш', callback_data='del_event')
        admin_markup = InlineKeyboardBuilder().add(admin_btn_1).add(admin_btn_2)
        await message.answer('Приветствую в панели админа Пидарсина', reply_markup=admin_markup.as_markup())
        await state.clear()
    else:
        await message.answer('Неправильный пароль')


@dp.callback_query(F.data == 'event')
async def process_callback_user(callback_query: types.CallbackQuery, bot: Bot):
    events = bot_db.event_exists()
    if not events:
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=callback_query.message.text + '\n Выберете дату',
            reply_markup=await SimpleCalendar().start_calendar())
    else:
        await callback_query.answer("У вас есть текущий ивент")
    await bot.answer_callback_query(callback_query.id)


@dp.callback_query(F.data == 'del_event')
async def process_callback_user(callback_query: types.CallbackQuery, bot: Bot):
    await bot.answer_callback_query(callback_query.id)
    events = bot_db.event_exists()
    if events:
        bot_db.del_event()
        await callback_query.message.answer("Готово")
    else:
        await callback_query.message.answer("Нет текущих ивентов")


@dp.callback_query(simple_cal_callback.filter())
async def process_simple_calendar(callback_query: types.CallbackQuery, callback_data: CallbackData, state: FSMContext):
    calendar = SimpleCalendar()
    selected, date = await calendar.process_selection(callback_query, callback_data)
    if selected:
        await callback_query.message.edit_text(
            callback_query.message.text + f'\n Вы выбрали {date.strftime("%d/%m/%Y")}')
        await state.update_data(date=date.strftime("%d/%m/%Y"))
        await callback_query.message.answer("Теперь введите время конурса в формате (Час:минута):")
        await state.set_state(ContestState.time)


@dp.message(ContestState.time)
async def password(message: types.Message, state: FSMContext):
    try:
        tm = datetime.strptime(message.text, '%H:%M')
        await state.update_data(time=message.text)
        await message.answer("Напишите текст для розыгрыша")
        await state.set_state(ContestState.text)
    except ValueError:
        await message.answer('неверный формат')


@dp.message(ContestState.text)
async def password(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer('Прикрепите фото разыгрываемого лота')
    await state.set_state(ContestState.image)


@dp.message(ContestState.image)
async def password(message: types.Message, state: FSMContext, bot: Bot):
    if message.photo:
        file_name = f"photos/{message.photo[-1].file_id}.jpg"
        await bot.download(message.photo[-1], destination=file_name)
        await state.update_data(image=f'{message.photo[-1].file_id}.jpg')
        await message.answer('Это фейковый розыгрыш? Если да то напишите имя пользователя, если нет то напишите "n"')
        await state.set_state(ContestState.fake)
    else:
        await message.answer('Это не фото')


@dp.message(ContestState.fake)
async def password(message: types.Message, state: FSMContext):
    await state.update_data(fake=message.text)
    dat = await state.get_data()
    bot_db.add_event(dat['date'], dat['time'], dat['text'], dat['image'], dat['fake'])
    await message.answer('Все готово')
    await state.clear()


@dp.message(Command(commands=["start"]))
async def start_menu(message: types.Message):
    user_btn_1 = types.InlineKeyboardButton(text='Принять', callback_data='accept')
    user_btn_2 = types.InlineKeyboardButton(text='Отказать', callback_data='reject')
    user_markup = InlineKeyboardBuilder().add(user_btn_1).add(user_btn_2)
    await message.answer('Хотите принять участие в конкурсе?', reply_markup=user_markup.as_markup())


@dp.callback_query(F.data.startswith('accept'))
async def process_callback_user(callback_query: types.CallbackQuery, bot: Bot):
    await bot.answer_callback_query(callback_query.id)
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=None)
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text=callback_query.message.text + '\n Поздравляю, и удачи 🤞')
    bot_db.add_user(callback_query.from_user.id, callback_query.from_user.username)


@dp.callback_query(F.data.startswith('reject'))
async def process_callback_kb1btn1(callback_query: types.CallbackQuery, bot: Bot):
    await bot.answer_callback_query(callback_query.id)
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=None)
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text=callback_query.message.text + '\n Зря вы отказались 😢')


async def notifications(time, bot: Bot):
    while True:
        event = bot_db.get_event_details()
        members = bot_db.get_members()
        if event and members:
            date = datetime.strptime(event[1], '%d/%m/%Y %H:%M')
            delta = date - date.now()
            hours = delta.total_seconds() // 3600
            if 0 <= hours <= 3:
                members = bot_db.get_members()
                for i in members:
                    user_id = i[0]
                    await bot.send_message(user_id, f'Через {int(hours)} час(а) конурс')
            if delta.total_seconds() == 0:
                image = FSInputFile(f'photos/{event[4]}')
                if event[2] != 'n':
                    await bot.send_photo(HOOPS_ID, photo=image, caption=event[3] + f'\n Победил: @{event[2]}')
                else:
                    await bot.send_photo(HOOPS_ID, photo=image,
                                         caption=event[3] + f'\n Победил: @{random.choice(members)[1]}')
        await asyncio.sleep(time)


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    loop = asyncio.get_event_loop()
    loop.create_task(notifications(3600, bot))
    await dp.start_polling(bot, skip_updates=True)


if '__main__' == __name__:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
