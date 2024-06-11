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
from aiogram.methods.get_chat_member import GetChatMember, ChatMemberMember
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
channel_btn_1 = types.InlineKeyboardButton(text='Принять участие', url='https://t.me/Hoops_shop_bot')
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
def is_admin(admin_list, message):
    admin_status = False
    for admin in admin_list:
        if admin.user.id == message.from_user.id:
            admin_status = True
            break
    return admin_status


@dp.message(EnterState.password)
async def password(message: types.Message, state: FSMContext):
    await state.update_data(password=message.text)
    dat = await state.get_data()
    if dat['password'] == PASSWORD:
@dp.message(Command(commands=["admin"]))
async def start_menu(message: types.Message, bot: Bot):
    admins = await bot.get_chat_administrators(chat_id=HOOPS_ID)
    if is_admin(admins, message) or message.from_user.id == ADMIN_ID:
        await message.answer('Приветствую в панели админа ', reply_markup=admin_markup.as_markup())
        await state.clear()
    else:
        await message.answer('Неправильный пароль')


@dp.callback_query(F.data == 'details')
@@ -183,7 +178,8 @@ async def password(message: types.Message, state: FSMContext, bot: Bot):
@dp.message(Command(commands=["start"]))
async def start_menu(message: types.Message, bot: Bot):
    user_status = await bot.get_chat_member(chat_id=HOOPS_ID, user_id=message.from_user.id)
    if isinstance(user_status, ChatMemberMember):
    admins = await bot.get_chat_administrators(chat_id=HOOPS_ID)
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
                if event[4] != '-' and event[2] != 'n':
                    image = FSInputFile(f'photos/{event[4]}')
                    await bot.send_photo(HOOPS_ID, photo=image,
                                         caption='@all \n' + event[3] + f'\n И победитель нашего розыгрыша футболки YEEZY x Gap x Balenciaga - @{event[2]} Поздравляем! Скоро мы свяжемся с тобой, чтобы уточнить детали получения приза. Следи за нашими обновлениями, у нас еще много интересного')
                    await bot.send_photo(ADMIN_ID, photo=image,
                                         caption='@all \n' + event[3] + f'\n  победитель нашего розыгрыша футболки YEEZY x Gap x Balenciaga - @{event[2]}  Поздравляем! Скоро мы свяжемся с тобой, чтобы уточнить детали получения приза. Следи за нашими обновлениями, у нас еще много интересного')
                    await del_photos(f'photos/{event[4]}')
                elif event[4] != '-' and event[2] == 'n':
                    winner = random.choice(members)
                    image = FSInputFile(f'photos/{event[4]}')
                    await bot.send_photo(HOOPS_ID, photo=image,
                                         caption='@all \n' + event[3] + f'\n И победитель нашего розыгрыша футболки YEEZY x Gap x Balenciaga - @{winner[1]}  Поздравляем! Скоро мы свяжемся с тобой, чтобы уточнить детали получения приза. Следи за нашими обновлениями, у нас еще много интересного')
                    await bot.send_photo(ADMIN_ID, photo=image,
                                         caption='@all \n' + event[3] + f'\n И победитель нашего розыгрыша футболки YEEZY x Gap x Balenciaga - @{winner[1]}  Поздравляем! Скоро мы свяжемся с тобой, чтобы уточнить детали получения приза. Следи за нашими обновлениями, у нас еще много интересного')
                    await del_photos(f'photos/{event[4]}')
                elif event[2] != 'n' and event[4] == '-':
                    await bot.send_message(HOOPS_ID, '@all \n' + event[3] + f'\n И победитель нашего розыгрыша футболки YEEZY x Gap x Balenciaga - @{event[2]} Поздравляем! Скоро мы свяжемся с тобой, чтобы уточнить детали получения приза. Следи за нашими обновлениями, у нас еще много интересного')
                    await bot.send_message(ADMIN_ID, '@all \n' + event[3] + f'\n И победитель нашего розыгрыша футболки YEEZY x Gap x Balenciaga - @{event[2]} Поздравляем! Скоро мы свяжемся с тобой, чтобы уточнить детали получения приза. Следи за нашими обновлениями, у нас еще много интересного')
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
