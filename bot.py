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
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, \
    ReplyKeyboardRemove, KeyboardButton
from aiogram.methods.get_chat_member import ChatMemberMember
from utlits import get_chat_members, get_channel_members
from currency import Currency

bot_db = BoTDb('participants.db')
dp = Dispatcher(storage=MemoryStorage())

admin_markup = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='Создать новый розыгрыш', callback_data='event')],
                     [InlineKeyboardButton(text='Удалить текущий розыгрыш', callback_data='del_event')],
                     [InlineKeyboardButton(text='Текущий розыгрыш', callback_data='details')],
                     [InlineKeyboardButton(text='Текущие участники', callback_data='members')],
                     [InlineKeyboardButton(text='Написать всем подписчикам', callback_data='send_to_all')]
                     ])

main_menu = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Оформить/Рассчитать заказ", callback_data='order')],
                     [InlineKeyboardButton(text="Участвовать в конкурсе ", callback_data='contest')],
                     [InlineKeyboardButton(text="Узнать курс юаня", callback_data='currency')],
                     [InlineKeyboardButton(text="Написать отзыв", callback_data='feedback')],
                     [InlineKeyboardButton(text="Срок доставки", callback_data='delivery_time')],
                     [InlineKeyboardButton(text="Написать менеджеру", callback_data='manager')]])

back_markup = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Вернуться в меню", callback_data="back")]])

feedback_markup = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='Оставить отзыв', url='https://t.me/hoops_reaction')],
                     [InlineKeyboardButton(text="Вернуться в меню", callback_data="back")]])

manager_markup = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='Написать менеджеру', url='https://t.me/raketka_228')],
                     [InlineKeyboardButton(text="Вернуться в меню", callback_data="back")]])
channel_markup = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='Принять участие', url='https://t.me/Hoops_shop_bot')]])

keyboard = types.ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Отменить расчет")]], resize_keyboard=True)

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

prod_dict = {"prod_sneakers": ['Кросовки', 0.5], "prod_winter_shoes": ['Зимняя обувь', 0.5],
             "prod_pants": ['Штаны', 0.5], "prod_shorts": ['Шорты', 0.5],
             "prod_shirts": ['Футболки и Рубашки', 0.5], "prod_balls": ['Мячи', 0.5],
             "prod_decors": ['Украшения', 0.5], "prod_perfumes": ['Парфюмы', 0.5],
             "prod_sweatshirts": ['Кофты и свитера🩳', 0.5], "prod_jacket": ['Верхняя одежда', 0.5],
             "prod_underwear": ['Нижнее белье', 0.5], "prod_accessories": ['Аксессуары', 0.5],
             "prod_small_bag": ['Маленькая сумка', 0.5], "prod_big_bag": ['Большая сумка/Рюкзак', 0.5]}


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
                             reply_markup=channel_markup)
    else:
        await bot.send_message(keys.HOOPS_ID, f'Внимание!!! {dat["text"]} \n'
                                              f'Дата и время: {dat["date"]} в {dat["time"]}',
                               reply_markup=channel_markup)
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
    feedback_members = await get_chat_members(keys.HOOPS_CHAT_ID)
    channel_members = await get_channel_members(keys.HOOPS_ID)
    members = set(feedback_members + channel_members)
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
        text='Бла бла бла')
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=feedback_markup)


@dp.callback_query(F.data == "manager")
async def manager_menu(callback_query: types.CallbackQuery, bot: Bot):
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text='Бла бла бла')
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
async def order_menu(callback_query: types.CallbackQuery, bot: Bot):
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text='Начните расчет')
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=product_markup)


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
    cur = Currency()
    price = int(((data['price'] * cur.current_converted_price) + 56 * data['category'][1]) * 1.2)
    await message.answer(f"Доствавка до {data['address']} будет стоит {price} руб\n"
                         f"Курс: {cur.current_converted_price}", reply_markup=order_markup)


@dp.callback_query(F.data == "manager_order")
async def manager_order_handler(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.answer("Пришлите ссылку на ваш товар")
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
    cur = Currency()
    ru_price = int(((data['price'] * cur.current_converted_price) + 56 * data['category'][1]) * 1.2)
    await message.answer("Спасибо за заказ, скоро наш менеджер с вами свяжется", reply_markup=back_markup)
    await bot.send_message(keys.MANAGER_CHAT_ID, text=f"Заказ от {data['name']}\n"
                                                      f"Категория: {data['category'][0]}\n"
                                                      f"Размер товара: {data['size']}\n"
                                                      f"Цена в юанях: {data['price']}\n"
                                                      f"Цена в рублях: {ru_price}\n"
                                                      f"Ссылка на товар: {data['link']}\n"
                                                      f"Адресс доставки: {data['address']}\n"
                                                      f"Номер телефона: {data['phone']}")
    await state.clear()


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
