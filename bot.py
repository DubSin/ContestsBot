import logging
import asyncio
import random
import sys
import shutil
import os
from datetime import datetime, timedelta
from keys import BOT_TOKEN, HOOPS_ID, PASSWORD, ADMIN_ID
from db import BoTDb
from aiogram.methods import DeleteWebhook
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

user_btn_1 = types.InlineKeyboardButton(text='Принять', callback_data='accept')
user_btn_2 = types.InlineKeyboardButton(text='Отказать', callback_data='reject')
user_markup = InlineKeyboardBuilder().add(user_btn_1).add(user_btn_2)

admin_btn_1 = types.InlineKeyboardButton(text='Создать новый розыгрыш', callback_data='event')
admin_btn_2 = types.InlineKeyboardButton(text='Удалить текущий розыгрыш', callback_data='del_event')
admin_btn_3 = types.InlineKeyboardButton(text='Текущий розыгрыш', callback_data='details')
admin_btn_4 = types.InlineKeyboardButton(text='Текущие участники', callback_data='members')
admin_markup = InlineKeyboardBuilder().add(admin_btn_1).add(admin_btn_2).add(admin_btn_3).add(admin_btn_4)

channel_btn_1 = types.InlineKeyboardButton(text='Принять участие', callback_data='channel_accept')
channel_markup = InlineKeyboardBuilder().add(channel_btn_1)


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
        await message.answer('Приветствую в панели админа ', reply_markup=admin_markup.as_markup())
        await state.clear()
    else:
        await message.answer('Неправильный пароль')


@dp.callback_query(F.data == 'details')
async def process_callback_user(callback_query: types.CallbackQuery, bot: Bot):
    await bot.answer_callback_query(callback_query.id)
    event_det = bot_db.get_event_details()
    if event_det:
        await callback_query.message.answer(f'Дата: {event_det[1]} \n'
                                            f'Текст поста: {event_det[3]} \n'
                                            f"Фейк: {event_det[2] if 'n' else 'yes'} \n"
                                            f"Ссылка на фото: {event_det[-1]}")
    else:
        await callback_query.message.answer('Нет текущего ивента')


@dp.callback_query(F.data == 'members')
async def process_callback_user(callback_query: types.CallbackQuery, bot: Bot):
    await bot.answer_callback_query(callback_query.id)
    event_memb = bot_db.get_members()
    st = ''
    if event_memb:
        for i in event_memb:
            st += f'Ник: {i[1]}, ID: {i[0]} \n'
        await callback_query.message.answer(st)
    else:
        await callback_query.message.answer('Нет текущего ивента')


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
    await message.answer("Прикрепите фото разыгрываемого лота или пришлите '-' если фото отсутствует")
    await state.set_state(ContestState.image)


@dp.message(ContestState.image)
async def password(message: types.Message, state: FSMContext, bot: Bot):
    if message.photo:
        file_name = f"photos/{message.photo[-1].file_id}.jpg"
        await bot.download(message.photo[-1], destination=file_name)
        await state.update_data(image=f'{message.photo[-1].file_id}.jpg')
        await message.answer('Это фейковый розыгрыш? Если да то напишите имя пользователя, если нет то напишите "n"')
        await state.set_state(ContestState.fake)
    elif message.text == '-':
        await state.update_data(image='-')
        await message.answer('Это фейковый розыгрыш? Если да то напишите имя пользователя, если нет то напишите "n"')
        await state.set_state(ContestState.fake)
    else:
        await message.answer('Это не фото')


@dp.message(ContestState.fake)
async def password(message: types.Message, state: FSMContext, bot: Bot):
    await state.update_data(fake=message.text)
    dat = await state.get_data()
    bot_db.add_event(dat['date'], dat['time'], dat['text'], dat['image'], dat['fake'])
    await message.answer('Все готово')
    if dat['image'] != '-':
        image = FSInputFile(f'photos/{dat["image"]}')
        await bot.send_photo(HOOPS_ID, photo=image, caption=f'@all \n Внимание!!! {dat["text"]} \n'
                                                            f'Дата и время: {dat["date"]} в {dat["time"]}',
                             reply_markup=channel_markup.as_markup())
    else:
        await bot.send_message(HOOPS_ID, f'@all \n Внимание!!! {dat["text"]} \n'
                                         f'Дата и время: {dat["date"]} в {dat["time"]}',
                               reply_markup=channel_markup.as_markup())
    await state.clear()


@dp.message(Command(commands=["start"]))
async def start_menu(message: types.Message):
    if bot_db.event_exists():
        await message.answer('Хотите принять участие в конкурсе?', reply_markup=user_markup.as_markup())
    else:
        await message.answer('Нет ближайших конурсов 😢')


@dp.callback_query(F.data.startswith('channel_accept'))
async def process_callback_user(callback_query: types.CallbackQuery, bot: Bot):
    await bot.answer_callback_query(callback_query.id)
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=None)
    bot_db.add_user(callback_query.from_user.id, callback_query.from_user.username)


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
            delta = date - (datetime.now() + timedelta(hours=3))
            print(delta)
            if 0 <= delta.total_seconds() <= time:
                if event[4] != '-' and event[2] != 'n':
                    image = FSInputFile(f'photos/{event[4]}')
                    await bot.send_photo(HOOPS_ID, photo=image,
                                         caption='@all \n' + event[3] + f'\n Победил: @{event[2]}')
                    await bot.send_photo(ADMIN_ID, photo=image,
                                         caption='@all \n' + event[3] + f'\n Победил: @{event[2]}')
                    await del_photos(f'photos/{event[4]}')
                elif event[4] != '-' and event[2] == 'n':
                    winner = random.choice(members)
                    image = FSInputFile(f'photos/{event[4]}')
                    await bot.send_photo(HOOPS_ID, photo=image,
                                         caption='@all \n' + event[3] + f'\n Победил: @{winner[1]}')
                    await bot.send_photo(ADMIN_ID, photo=image,
                                         caption='@all \n' + event[3] + f'\n Победил: @{winner[1]}')
                    await del_photos(f'photos/{event[4]}')
                elif event[2] != 'n' and event[4] == '-':
                    await bot.send_message(HOOPS_ID, '@all \n' + event[3] + f'\n Победил: @{event[2]}')
                    await bot.send_message(ADMIN_ID, '@all \n' + event[3] + f'\n Победил: @{event[2]}')
                elif event[2] == 'n' and event[4] == '-':
                    winner = random.choice(members)
                    await bot.send_message(HOOPS_ID, '@all \n' + event[3] + f'\n Победил: @{winner[1]}')
                    await bot.send_message(ADMIN_ID, '@all \n' + event[3] + f'\n Победил: @{winner[1]}')
                bot_db.del_event()
        await asyncio.sleep(time)


async def del_photos(folder_path):
    shutil.rmtree(folder_path)
    os.mkdir(folder_path)


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    loop = asyncio.get_event_loop()
    loop.create_task(notifications(100, bot))
    await bot(DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)


if '__main__' == __name__:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
