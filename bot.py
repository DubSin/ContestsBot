import logging
import asyncio
import random
import sys
import shutil
import os
from datetime import datetime, timedelta
import keys
from db import BoTDb
from aiogram.methods import DeleteWebhook
from aiogram import F, exceptions
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram3_calendar import SimpleCalendar, simple_cal_callback
from aiogram import Dispatcher, Bot, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from aiogram.methods.get_chat_member import GetChatMember, ChatMemberMember
from utlits import get_chat_members

bot_db = BoTDb('participants.db')
dp = Dispatcher(storage=MemoryStorage())

user_btn_1 = types.InlineKeyboardButton(text='Принять', callback_data='accept')
user_btn_2 = types.InlineKeyboardButton(text='Отказать', callback_data='reject')
user_markup = InlineKeyboardBuilder().add(user_btn_1).add(user_btn_2)

admin_btn_1 = types.InlineKeyboardButton(text='Создать новый розыгрыш', callback_data='event')
admin_btn_2 = types.InlineKeyboardButton(text='Удалить текущий розыгрыш', callback_data='del_event')
admin_btn_3 = types.InlineKeyboardButton(text='Текущий розыгрыш', callback_data='details')
admin_btn_4 = types.InlineKeyboardButton(text='Текущие участники', callback_data='members')
admin_btn_5 = types.InlineKeyboardButton(text='Написать всем подписчикам', callback_data='send_to_all')
admin_markup = InlineKeyboardBuilder().add(admin_btn_1).add(admin_btn_2).add(admin_btn_3).add(admin_btn_4)\
    .add(admin_btn_5)

channel_btn_1 = types.InlineKeyboardButton(text='Принять участие', url='https://t.me/Hoops_shop_bot')
channel_markup = InlineKeyboardBuilder().add(channel_btn_1)


class ContestState(StatesGroup):
    time = State()
    text = State()
    image = State()
    fake = State()
    after_text = State()


class SendMembers(StatesGroup):
    text = State()
    photo = State()
    contest = State()


def is_admin(admin_list, message):
    admin_status = False
    for admin in admin_list:
        if admin.user.id == message.from_user.id:
            admin_status = True
            break
    return admin_status


@dp.message(Command(commands=["admin"]))
async def start_menu(message: types.Message, bot: Bot):
    admins = await bot.get_chat_administrators(chat_id=keys.HOOPS_ID)
    if is_admin(admins, message) or message.from_user.id == keys.ADMIN_ID:
        await message.answer('Приветствую в панели админа ', reply_markup=admin_markup.as_markup())


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
async def text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("Прикрепите фото разыгрываемого лота или пришлите '-' если фото отсутствует")
    await state.set_state(ContestState.image)


@dp.message(ContestState.image)
async def photo(message: types.Message, state: FSMContext, bot: Bot):
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
async def fake(message: types.Message, state: FSMContext, bot: Bot):
    await state.update_data(fake=message.text)
    await message.answer("Отлично! Теперь введите сообщение победителю")
    await state.set_state(ContestState.after_text)


@dp.message(ContestState.after_text)
async def fake(message: types.Message, state: FSMContext, bot: Bot):
    await state.update_data(after_text=message.text)
    dat = await state.get_data()
    bot_db.add_event(dat['date'], dat['time'], dat['text'], dat['image'], dat['fake'], dat['after_text'])
    await message.answer('Все готово')
    if dat['image'] != '-':
        image = FSInputFile(f'photos/{dat["image"]}')
        await bot.send_photo(keys.HOOPS_ID, photo=image, caption=f'Внимание!!! {dat["text"]} \n'
                                                                 f'Дата и время: {dat["date"]} в {dat["time"]}',
                             reply_markup=channel_markup.as_markup())
    else:
        await bot.send_message(keys.HOOPS_ID, f'Внимание!!! {dat["text"]} \n'
                                              f'Дата и время: {dat["date"]} в {dat["time"]}',
                               reply_markup=channel_markup.as_markup())
    await state.clear()


@dp.callback_query(F.data == 'send_to_all')
async def process_callback_user(callback_query: types.CallbackQuery, bot: Bot, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.answer("Введите какой текст хотите отправить всем участникам группы Hoops")
    await state.set_state(SendMembers.text)


@dp.message(SendMembers.text)
async def send_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("Добавьте фотографии (напишите '-', если не хотите добавлять)")
    await state.set_state(SendMembers.photo)


@dp.message(SendMembers.photo)
async def send_photo(message: types.Message, state: FSMContext, bot: Bot):
    members = await get_chat_members(keys.HOOPS_CHAT_ID)
    try:
        for i in members:
            print(i)
        if message.photo:
            file_name = f"photos/{message.photo[-1].file_id}.jpg"
            await bot.download(message.photo[-1], destination=file_name)
            await state.update_data(photo=f'{message.photo[-1].file_id}.jpg')
            dat = await state.get_data()
            image = FSInputFile(f'photos/{dat["photo"]}')
            for member in members:
                await bot.send_photo(member, photo=image, caption=dat['text'])
        elif message.text == '-':
            await state.update_data(photo='-')
            dat = await state.get_data()
            for member in members:
                await bot.send_message(member, dat['text'])
        else:
            await message.answer('Это не фото')
        await message.answer('Сообщение успешное отправлено')
    except exceptions.TelegramForbiddenError:
        pass
    await state.clear()


@dp.message(Command(commands=["start"]))
async def start_menu(message: types.Message, bot: Bot):
    user_status = await bot.get_chat_member(chat_id=keys.HOOPS_ID, user_id=message.from_user.id)
    admins = await bot.get_chat_administrators(chat_id=keys.HOOPS_ID)
    if isinstance(user_status, ChatMemberMember) or is_admin(admins, message):
        if bot_db.event_exists():
            await message.answer('Хотите принять участие в конкурсе?', reply_markup=user_markup.as_markup())
        else:
            await message.answer('Нет ближайших конурсов 😢')
    else:
        await message.answer('Вы не подписаны 🤬')


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
                print('yea ')
                if event[4] != '-' and event[2] != 'n':
                    image = FSInputFile(f'photos/{event[4]}')
                    await bot.send_photo(keys.HOOPS_ID, photo=image,
                                         caption=f'Победил: @{event[2]}\n' + event[-1])
                    await bot.send_photo(keys.ADMIN_ID, photo=image,
                                         caption=f'Победил: @{event[2]}\n' + event[-1])
                    await del_photos(f'photos/{event[4]}')
                elif event[4] != '-' and event[2] == 'n':
                    winner = random.choice(members)
                    image = FSInputFile(f'photos/{event[4]}')
                    await bot.send_photo(keys.HOOPS_ID, photo=image,
                                         caption=f'Победил: @{winner[1]}\n' + event[-1])
                    await bot.send_photo(keys.ADMIN_ID, photo=image,
                                         caption=f'Победил: @{winner[1]}\n' + event[-1])
                    await del_photos(f'photos/{event[4]}')
                elif event[2] != 'n' and event[4] == '-':
                    await bot.send_message(keys.HOOPS_ID, f'Победил: @{event[2]}\n' + event[-1])
                    await bot.send_message(keys.ADMIN_ID, f'Победил: @{event[2]}\n' + event[-1])
                elif event[2] == 'n' and event[4] == '-':
                    winner = random.choice(members)
                    await bot.send_message(keys.HOOPS_ID, f'Победил: @{winner[1]}\n' + event[-1])
                    await bot.send_message(keys.ADMIN_ID, f'Победил: @{winner[1]}\n' + event[-1])
                bot_db.del_event()
        await asyncio.sleep(time)


async def del_photos(folder_path):
    shutil.rmtree(folder_path)
    os.mkdir(folder_path)


async def main() -> None:
    bot = Bot(token=keys.BOT_TOKEN)
    loop = asyncio.get_event_loop()
    loop.create_task(notifications(60, bot))
    await bot(DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)


if '__main__' == __name__:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
