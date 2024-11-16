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
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, \
    ReplyKeyboardRemove, KeyboardButton
from aiogram.enums.parse_mode import ParseMode
from aiogram.methods.get_chat_member import ChatMemberMember
from aiogram.utils.media_group import MediaGroupBuilder
from utlits import get_chat_members
from currency import Currency

bot_db = BoTDb('participants.db')
dp = Dispatcher(storage=MemoryStorage())

admin_markup = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='Создать новый розыгрыш', callback_data='event')],
                     [InlineKeyboardButton(text='Удалить текущий розыгрыш', callback_data='del_event')],
                     [InlineKeyboardButton(text='Текущий розыгрыш', callback_data='details')],
                     [InlineKeyboardButton(text='Текущие участники', callback_data='members')],
                     [InlineKeyboardButton(text='Написать всем подписчикам', callback_data='send_to_all')],
                     [InlineKeyboardButton(text='Написать в канал приветствие', callback_data='send_to_channel')]])

main_menu = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Оформить/Рассчитать заказ", callback_data='order')],
                     [InlineKeyboardButton(text="Участвовать в конкурсе ", callback_data='contest')],
                     [InlineKeyboardButton(text="Узнать курс юаня", callback_data='currency')],
                     [InlineKeyboardButton(text="Написать отзыв", callback_data='feedback')],
                     [InlineKeyboardButton(text="Срок доставки", callback_data='delivery_time')],
                     [InlineKeyboardButton(text="Написать менеджеру", callback_data='manager')]])

back_markup = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Вернуться в меню", callback_data="back")]])

channel_markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Заказать',
                                                                             url='https://t.me/Hoops_shop_bot')]])

admin_back_markup = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Вернуться в панель админа", callback_data="back_admin")]])

feedback_markup = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='Оставить отзыв', url='https://t.me/hoops_reaction')],
                     [InlineKeyboardButton(text="Вернуться в меню", callback_data="back")]])

manager_markup = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='Написать менеджеру', url='https://t.me/raketka_228')],
                     [InlineKeyboardButton(text="Вернуться в меню", callback_data="back")]])
keyboard = types.ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Отменить расчет")]], resize_keyboard=True)
break_contest_keyboard = types.ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Отменить конкурс")]],
                                                   resize_keyboard=True)
break_newslet_keyboard = types.ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Отменить рассылку")]],
                                                   resize_keyboard=True)

product_markup = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Кроссовки👟", callback_data="prod_sneakers"),
                      InlineKeyboardButton(text="Зимняя обувь🥾👢", callback_data="prod_winter_shoes")],
                     [InlineKeyboardButton(text="Штаны (джинсы, спортивки)", callback_data="prod_pants"),
                      InlineKeyboardButton(text="Шорты🩳", callback_data="prod_shorts")],
                     [InlineKeyboardButton(text="Футболки и Рубашки👕👔", callback_data="prod_shirts")],
                     [InlineKeyboardButton(text="Мячи🏀", callback_data="prod_balls"),
                      InlineKeyboardButton(text="Украшения👑", callback_data="prod_decors"),
                      InlineKeyboardButton(text="Парфюмы🌷", callback_data="prod_perfumes")],
                     [InlineKeyboardButton(text="Кофты и свитера🩳", callback_data="prod_sweatshirts"),
                      InlineKeyboardButton(text="Верхняя одежда🧥", callback_data="prod_jacket")],
                     [InlineKeyboardButton(text="Нижнее белье👙🧦", callback_data="prod_underwear"),
                      InlineKeyboardButton(text="Аксессуары🧢🧤", callback_data="prod_accessories")],
                     [InlineKeyboardButton(text="Маленькая сумка 👛", callback_data="prod_small_bag")],
                     [InlineKeyboardButton(text="Большая сумка/Рюкзак 🧳🎒", callback_data="prod_big_bag")],
                     [InlineKeyboardButton(text="Вернуться в меню", callback_data="back")]])

order_markup = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Расчитать еще", callback_data="order")],
                     [InlineKeyboardButton(text="Заказать", callback_data="manager_order")],
                     [InlineKeyboardButton(text="Вернуться в меню", callback_data="back")]])

order_back_markup = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Заказать еще", callback_data="order")],
                     [InlineKeyboardButton(text="Вернуться в меню", callback_data="back")]])

prod_dict = {"prod_sneakers": ['Кросовки', 0.6], "prod_winter_shoes": ['Зимняя обувь', 1.1],
             "prod_pants": ['Штаны', 0.7], "prod_shorts": ['Шорты', 0.35],
             "prod_shirts": ['Футболки и Рубашки', 0.5], "prod_balls": ['Мячи', 0.6],
             "prod_decors": ['Украшения', 0.3], "prod_perfumes": ['Парфюмы', 0.3],
             "prod_sweatshirts": ['Кофты и свитера', 0.7], "prod_jacket": ['Верхняя одежда', 1],
             "prod_underwear": ['Нижнее белье', 0.2], "prod_accessories": ['Аксессуары', 0.3],
             "prod_small_bag": ['Маленькая сумка', 0.5], "prod_big_bag": ['Большая сумка/Рюкзак', 0.7]}


class ContestState(StatesGroup):
    time = State()
    text = State()
    media = State()
    fake = State()
    after_text = State()


class SendMembers(StatesGroup):
    text = State()
    media = State()
    contest = State()


class OrderStates(StatesGroup):
    category = State()
    price = State()
    address = State()
    link = State()
    size = State()
    name = State()
    phone = State()


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
        await message.answer('Приветствую в панели админа ', reply_markup=admin_markup)


@dp.message(F.text == "Отменить конкурс")
async def product_handler(message: types.Message, state: FSMContext):
    await message.answer("Конкурс отменен", reply_markup=ReplyKeyboardRemove())
    await message.answer("Приветствую в панели админа", reply_markup=admin_markup)
    await state.clear()


@dp.message(F.text == "Отменить рассылку")
async def product_handler(message: types.Message, state: FSMContext):
    await message.answer("Рассылка отменена", reply_markup=ReplyKeyboardRemove())
    await message.answer("Приветствую в панели админа", reply_markup=admin_markup)
    await state.clear()


@dp.callback_query(F.data == "back_admin")
async def back_menu(callback_query: types.CallbackQuery, bot: Bot, state: FSMContext):
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text='Приветствую в панели админа')
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=admin_markup)
    await state.clear()


@dp.callback_query(F.data == 'details')
async def process_callback_user(callback_query: types.CallbackQuery, bot: Bot):
    await bot.answer_callback_query(callback_query.id)
    event_det = bot_db.get_event_details()
    if event_det:
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=f'Дата: {event_det[1]} \n'
                 f'Текст поста: {event_det[3]} \n'
                 f"Фейк: {event_det[2] if 'n' else 'yes'} \n"
                 f"Ссылка на фото: {event_det[4]}\n"
                 f"Текст победителя: {event_det[-1]}")
    else:
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text='Нет текущего ивента')
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=admin_back_markup)


@dp.callback_query(F.data == 'members')
async def process_callback_user(callback_query: types.CallbackQuery, bot: Bot):
    await bot.answer_callback_query(callback_query.id)
    event_memb = bot_db.get_members()
    st = ''
    if event_memb:
        for i in event_memb:
            st += f'Ник: {i[1]}, ID: {i[0]} \n'
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=st)
    else:
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text="Нет участников")
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=admin_back_markup)


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
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text="Готово")
        await del_media('media')
    else:
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text="Нет текущих ивентов")
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=admin_back_markup)


@dp.callback_query(simple_cal_callback.filter())
async def process_simple_calendar(callback_query: types.CallbackQuery, callback_data: CallbackData, state: FSMContext):
    calendar = SimpleCalendar()
    selected, date = await calendar.process_selection(callback_query, callback_data)
    if selected:
        await callback_query.message.edit_text(
            callback_query.message.text + f'\n Вы выбрали {date.strftime("%d/%m/%Y")}')
        await state.update_data(date=date.strftime("%d/%m/%Y"))
        await callback_query.message.answer("Теперь введите время конурса в формате (Час:минута):",
                                            reply_markup=break_contest_keyboard)
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
    await message.answer("Прикрепите фото/видео разыгрываемого лота, пришлите '-' после всех высланых файлов")
    await state.set_state(ContestState.media)


@dp.message(ContestState.media)
async def photo(message: types.Message, state: FSMContext, bot: Bot):
    if message.photo:
        file_name = f"media/{message.photo[-1].file_id}.jpg"
        await bot.download(message.photo[-1], destination=file_name)
    if message.video:
        print(message.video)
        file_name = f"media/{message.video.file_id}.mp4"
        await bot.download(message.video, destination=file_name)
    if message.text == '-':
        media = ' '.join([f for f in os.listdir('media') if os.path.isfile(os.path.join('media', f))])
        print(media)
        await state.update_data(media=media)
        await message.answer('Это фейковый розыгрыш? Если да то напишите имя пользователя, если нет то напишите "n"')
        await state.set_state(ContestState.fake)


@dp.message(ContestState.fake)
async def fake(message: types.Message, state: FSMContext):
    await state.update_data(fake=message.text)
    await message.answer("Отлично! Теперь введите сообщение победителю")
    await state.set_state(ContestState.after_text)


@dp.message(ContestState.after_text)
async def fake(message: types.Message, state: FSMContext, bot: Bot):
    await state.update_data(after_text=message.text)
    dat = await state.get_data()
    bot_db.add_event(dat['date'], dat['time'], dat['text'], dat['media'], dat['fake'], dat['after_text'])
    await message.answer('Конкурс создан', reply_markup=ReplyKeyboardRemove())
    await message.answer('Вернутся в панель админа', reply_markup=admin_back_markup)
    str_media = dat['media'].split()
    print(str_media)
    sck = 0
    media_group = MediaGroupBuilder()
    for obj in str_media:
        if obj.endswith('.mp4') or obj.endswith('.MP4'):
            if sck == 0:
                media_group.add_video(type="video", media=FSInputFile(f"media/{obj}"),
                                      caption=f'Внимание!!! {dat["text"]} \n'
                                              f'Дата и время: {dat["date"]} в {dat["time"]}\n'
                                              f"Хочешь участвовать <a href='https://t.me/Hoops_shop_bot'>жми</a>",
                                      parse_mode=ParseMode.HTML)
            else:
                media_group.add_video(type="video", media=FSInputFile(f"media/{obj}"))
        if obj.endswith('.jpg'):
            if sck == 0:
                media_group.add_photo(type="photo", media=FSInputFile(f"media/{obj}"),
                                      caption=f'Внимание!!! {dat["text"]} \n'
                                              f'Дата и время: {dat["date"]} в {dat["time"]}\n'
                                              f"Хочешь участвовать <a href='https://t.me/Hoops_shop_bot'>жми</a>",
                                      parse_mode=ParseMode.HTML)
            else:
                media_group.add_photo(type="photo", media=FSInputFile(f"media/{obj}"))
        sck += 1
    await bot.send_media_group(keys.HOOPS_ID, media=media_group.build())

    await state.clear()


@dp.callback_query(F.data == 'send_to_all')
async def process_callback_user(callback_query: types.CallbackQuery, bot: Bot, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.answer("Введите какой текст хотите отправить всем участникам группы Hoops",
                                        reply_markup=break_newslet_keyboard)
    await state.set_state(SendMembers.text)


@dp.callback_query(F.data == 'send_to_channel')
async def process_callback_user(callback_query: types.CallbackQuery, bot: Bot):
    await bot.answer_callback_query(callback_query.id)
    msg_text = """🔥Приветствуем друг , мы команда молодых предпринимателей, занимающихся выкупом и доставкой товаров из Китая\n
    ✨  Мы доставляем товары с  китайского маркетплейса  Poizon \n
    🐦‍🔥 𝐻𝑂𝑂𝑃𝑆_𝑆𝐻𝑂𝑃 - это место, где стиль встречается с качеством, а шопинг становится настоящим удовольствием.
     \nНаш бот:\n @Hoops_shop_bot
     \nПоддержка:\n @raketka_228 """
    to_pin_message = await bot.send_photo(keys.HOOPS_ID, FSInputFile('service_media/logo.jpg'),
                                          caption=msg_text,
                                          reply_markup=channel_markup)
    await bot.pin_chat_message(chat_id=keys.HOOPS_ID, message_id=to_pin_message.message_id)
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text="Сообщение успешно отпралено")
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=admin_back_markup)


@dp.message(SendMembers.text)
async def send_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("Добавьте фотографии/видео (напишите '-', в качестве завершения)")
    await state.set_state(SendMembers.media)


@dp.message(SendMembers.media)
async def send_photo(message: types.Message, state: FSMContext, bot: Bot):
    try:
        if message.photo:
            path = f"media_distrib/{message.photo[-1].file_id}.jpg"
            await bot.download(message.photo[-1], destination=path)
        if message.video:
            path = f"media_distrib/{message.video.file_id}.mp4"
            await bot.download(message.video, destination=path)
        if message.text == '-':
            media = ' '.join(
                [f for f in os.listdir('media_distrib') if os.path.isfile(os.path.join('media_distrib', f))])
            await state.update_data(media=media)
            dat = await state.get_data()
            members = await get_chat_members(keys.HOOPS_CHAT_ID)
            if type(media) == list:
                if media:
                    str_media = dat['media'].split()
                    sck = 0
                    media_group = MediaGroupBuilder()
                    for obj in str_media:
                        if obj.endswith('.mp4') or obj.endswith('.MP4'):
                            if sck == 0:
                                media_group.add_video(type="video", media=FSInputFile(f"media_distrib/{obj}"),
                                                      caption=dat['text'])
                            else:
                                media_group.add_video(type="video", media=FSInputFile(f"media_distrib/{obj}"))
                        if obj.endswith('.jpg'):
                            if sck == 0:
                                media_group.add_photo(type="photo", media=FSInputFile(f"media_distrib/{obj}"),
                                                      caption=dat['text'])
                            else:
                                media_group.add_photo(type="photo", media=FSInputFile(f"media_distrib/{obj}"))
                        sck += 1
                    for member in members:
                        await bot.send_media_group(member, media=media_group.build())
                else:
                    for member in members:
                        await bot.send_message(member, dat['text'])
                await message.answer('Рассылка завершена', reply_markup=ReplyKeyboardRemove())
                await message.answer('Сообщения успешно отправлены', reply_markup=admin_back_markup)
                await del_media('media_distrib')
                await state.clear()
            else:
                await message.answer(f'Апи перегружен на {media} секунд, попробуйте позже',
                                     reply_markup=ReplyKeyboardRemove())
                await message.answer('Вернуться в меню', reply_markup=admin_back_markup)
                await del_media('media_distrib')
    except exceptions.TelegramForbiddenError:
        pass


@dp.message(Command(commands=["start"]))
async def start_menu(message: types.Message):
    await message.answer("Привествую, я Hoops Shop Bot", reply_markup=main_menu)


@dp.callback_query(F.data == "contest")
async def contest_menu(callback_query: types.CallbackQuery, bot: Bot):
    user_status = await bot.get_chat_member(chat_id=keys.HOOPS_ID, user_id=callback_query.from_user.id)
    admins = await bot.get_chat_administrators(chat_id=keys.HOOPS_ID)
    if isinstance(user_status, ChatMemberMember) or is_admin(admins, callback_query):
        if bot_db.event_exists():
            bot_db.add_user(callback_query.from_user.id, callback_query.from_user.username)
            await bot.edit_message_text(
                chat_id=callback_query.from_user.id,
                message_id=callback_query.message.message_id,
                text='Теперь Вы участвуете в конкурсе. Удачи🤞🍀')
            await bot.edit_message_reply_markup(
                chat_id=callback_query.from_user.id,
                message_id=callback_query.message.message_id,
                reply_markup=back_markup)
        else:
            await bot.edit_message_text(
                chat_id=callback_query.from_user.id,
                message_id=callback_query.message.message_id,
                text='Нет ближайших конурсов 😢')
            await bot.edit_message_reply_markup(
                chat_id=callback_query.from_user.id,
                message_id=callback_query.message.message_id,
                reply_markup=back_markup)
    else:
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text='Вы не подписаны 🤬')
        await bot.edit_message_reply_markup(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            reply_markup=back_markup)


@dp.callback_query(F.data == "feedback")
async def feedback_menu(callback_query: types.CallbackQuery, bot: Bot):
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text='Оставьте отзыв')
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=feedback_markup)


@dp.callback_query(F.data == "manager")
async def manager_menu(callback_query: types.CallbackQuery, bot: Bot):
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text='Напишите менеджеру')
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=manager_markup)


@dp.callback_query(F.data == "delivery_time")
async def delivery_menu(callback_query: types.CallbackQuery, bot: Bot):
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text='🚚Приблизительные сроки доставки:\n\nТовар доезжает до склада в Китае за 2-6 дней, откуда направляется на '
             'наш склад в Москву (это занимает примерно 12-16 дней), откуда отправляется Вам СДЭКом, '
             'если это необходимо')
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=back_markup)


@dp.callback_query(F.data == "currency")
async def currency_menu(callback_query: types.CallbackQuery, bot: Bot):
    cur = Currency()
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text=f'Текущий курс: {cur.current_converted_price} \n\n‼Курс юаня к рублю в нашем магазине зависит от курса '
             f'Центрального Банка РФ. Предоставляем один из самы выгодных курсов на рынке🤩')
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=back_markup)


@dp.callback_query(F.data == "back")
async def back_menu(callback_query: types.CallbackQuery, bot: Bot, state: FSMContext):
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text='Привествую, я Hoops Shop Bot')
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=main_menu)
    await state.clear()


@dp.callback_query(F.data == "order")
async def order_menu(callback_query: types.CallbackQuery, bot: Bot, state: FSMContext):
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text='Начните расчет')
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=product_markup)
    await state.clear()


@dp.message(F.text == "Отменить расчет")
async def product_handler(message: types.Message, state: FSMContext):
    await message.answer("Расчет отменен", reply_markup=ReplyKeyboardRemove())
    await message.answer("Начните рассчет", reply_markup=product_markup)
    await state.clear()


@dp.callback_query(F.data.startswith("prod"))
async def product_handler(callback_query: types.CallbackQuery, bot: Bot, state: FSMContext):
    await state.update_data(category=prod_dict[callback_query.data])
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.answer("Введите цену товара в юанях", reply_markup=keyboard)
    await state.set_state(OrderStates.price)


@dp.message(OrderStates.price)
async def price_state(message: types.Message, state: FSMContext):
    try:
        await state.update_data(price=int(message.text))
        await message.answer("Отлично! Теперь введите адрес доставки")
        await state.set_state(OrderStates.address)
    except ValueError:
        await message.answer("Вы ввели не число")


@dp.message(OrderStates.address)
async def address_state(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    data = await state.get_data()
    try:
        cur = Currency()
        price = int(((data['price'] * cur.current_converted_price) + 56 * data['category'][1]) * 1.2)
        await message.answer(f"Доствавка до {data['address']} будет стоит {price} руб\n"
                             f"Курс: {cur.current_converted_price}", reply_markup=order_markup)
    except Exception:
        await message.answer("Возникла ошибка", reply_markup=back_markup)


@dp.callback_query(F.data == "manager_order")
async def manager_order_handler(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    await bot.answer_callback_query(callback_query.id)
    media_group = MediaGroupBuilder(caption="Пришлите ссылку на ваш товар(Инскрукция на фото выше)")
    media_group.add_photo(type="photo", media=FSInputFile(f"service_media/instruct2.jpg"))
    media_group.add_photo(type="photo", media=FSInputFile(f"service_media/instruct1.jpg"))
    await bot.send_media_group(callback_query.from_user.id, media=media_group.build())
    await state.set_state(OrderStates.link)


@dp.message(OrderStates.link)
async def link_state(message: types.Message, state: FSMContext):
    await state.update_data(link=message.text)
    await message.answer("Напишите размер вашего товара")
    await state.set_state(OrderStates.size)


@dp.message(OrderStates.size)
async def link_state(message: types.Message, state: FSMContext):
    await state.update_data(size=message.text)
    await message.answer("Отлично! Теперь напишите свое ФИО")
    await state.set_state(OrderStates.name)


@dp.message(OrderStates.name)
async def name_state(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Отлично! Теперь напишите свое номер телефона, чтобы наш менеджер мог связаться с вами")
    await state.set_state(OrderStates.phone)


@dp.message(OrderStates.phone)
async def phone_state(message: types.Message, state: FSMContext, bot: Bot):
    await state.update_data(phone=message.text)
    data = await state.get_data()
    try:
        cur = Currency()
        ru_price = int(((data['price'] * cur.current_converted_price) + 56 * data['category'][1]) * 1.2)
        username = message.from_user.username
        await message.answer("Спасибо за заказ", reply_markup=ReplyKeyboardRemove())
        await message.answer('Cкоро наш менеджер с вами свяжется', reply_markup=order_back_markup)
        await bot.send_message(keys.MANAGER_CHAT_ID, text=f"Заказ от {data['name']}\n"
                                                          f"Категория: {data['category'][0]}\n"
                                                          f"Размер товара: {data['size']}\n"
                                                          f"Цена в юанях: {data['price']}\n"
                                                          f"Цена в рублях: {ru_price}\n"
                                                          f"Ссылка на товар: {data['link']}\n"
                                                          f"Адресс доставки: {data['address']}\n"
                                                          f"Номер телефона: {data['phone']}\n"
                                                          f"Связаться с клиентом: <a href='https://t.me/{username}'>жми</a>",
                               parse_mode=ParseMode.HTML)
    except Exception:
        await message.answer("Возникла ошибка", reply_markup=back_markup)
    await state.clear()


async def notifications(time, bot: Bot):
    while True:
        event = bot_db.get_event_details()
        members = bot_db.get_members()
        if event and members:
            date = datetime.strptime(event[1], '%d/%m/%Y %H:%M')
            delta = date - (datetime.now() + timedelta(hours=3))
            print("Seconds to event:" + str(delta.total_seconds()))
            if 0 <= delta.total_seconds() <= time:
                if event[2] != 'n':
                    str_media = event[4].split()
                    sck = 0
                    media_group = MediaGroupBuilder()
                    for obj in str_media:
                        if obj.endswith('.mp4') or obj.endswith('.MP4'):
                            if sck == 0:
                                media_group.add_video(type="video", media=FSInputFile(f"media/{obj}"),
                                                      caption=f'Победил: @{event[2]}\n' + event[-1])
                            else:
                                media_group.add_video(type="video", media=FSInputFile(f"media/{obj}"))
                        if obj.endswith('.jpg'):
                            if sck == 0:
                                media_group.add_photo(type="photo", media=FSInputFile(f"media/{obj}"),
                                                      caption=f'Победил: @{event[2]}\n' + event[-1])
                            else:
                                media_group.add_photo(type="photo", media=FSInputFile(f"media/{obj}"))
                        sck += 1
                    await bot.send_media_group(keys.HOOPS_ID, media=media_group.build())
                    await bot.send_media_group(keys.ADMIN_ID, media=media_group.build())

                    await del_media(f'media')
                elif event[2] == 'n':
                    winner = random.choice(members)
                    str_media = event[4].split()
                    sck = 0
                    media_group = MediaGroupBuilder()
                    for obj in str_media:
                        if obj.endswith('.mp4') or obj.endswith('.MP4'):
                            if sck == 0:
                                media_group.add_video(type="video", media=FSInputFile(f"media/{obj}"),
                                                      caption=f'Победил: @{winner[1]}\n' + event[-1])
                            else:
                                media_group.add_video(type="video", media=FSInputFile(f"media/{obj}"))
                        if obj.endswith('.jpg'):
                            if sck == 0:
                                media_group.add_photo(type="photo", media=FSInputFile(f"media/{obj}"),
                                                      caption=f'Победил: @{winner[1]}\n' + event[-1])
                            else:
                                media_group.add_photo(type="photo", media=FSInputFile(f"media/{obj}"))
                        sck += 1
                    await bot.send_media_group(keys.HOOPS_ID, media=media_group.build())
                    await bot.send_media_group(keys.ADMIN_ID, media=media_group.build())
                    await del_media('media')
                bot_db.del_event()
        await asyncio.sleep(time)


async def del_media(folder_path):
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
