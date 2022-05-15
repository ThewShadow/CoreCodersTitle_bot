import smtplib

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
import settings
import response_texts
import logging
import pymongo
import email
from email.utils import formataddr
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level='INFO', filename='logs.log', format=FORMAT)
logger = logging.getLogger()

try:
    client = pymongo.MongoClient('mongodb://localhost', 27017)
    db = client[settings.DB_NAME]
    orders = db['orders']
    print(f'CONNECT TO DB ("{settings.DB_NAME}") SUCCESSFULLY')
except Exception as e:
    logger.critical(e)
    raise f'ERROR CONNECT TO DB ({settings.DB_NAME})! Check file "logs.log"'

try:
    bot = telebot.TeleBot(settings.TELEGRAM_API_KEY)
except Exception as e:
    logger.critical(e)
    raise f'ERROR CREATE TELEGRAM BOT! Check file "logs.log"'

recivers = ['zvichayniy.vick@gmail.com', 'ivpavliv@gmail.com']

class Order:
    LIST = {}
    def __init__(self, name,
                 bot_destination=None,
                 bot_functions=None,
                 need_admin_panel=False,
                 contacts=None):

        self.name = name
        self.bot_destination = bot_destination
        self.bot_functions = bot_functions
        self.need_admin_panel = need_admin_panel
        self.contacts = contacts

    def save(self):
        orders.insert_one(self.get_dict())

    def get_view(self):
        return f'<b>Ім\'я</b>: {self.name}\n' \
            f'<b>Призначення бота</b>: {self.bot_destination}\n' \
            f'<b>Функціональність</b>: {self.bot_functions}\n' \
            f'<b>Потрібна адмін панель</b>: {self.need_admin_panel}\n' \
            f'<b>Контакти</b>: {self.contacts}'

    def get_dict(self):
        return {
            'name': self.name,
            'bot_destination': self.bot_destination,
            'bot_functions': self.bot_functions,
            'need_admin_panel': self.need_admin_panel,
            'contacts': self.contacts,
        }

    def send_order(self):
        msg = MIMEMultipart()
        msg['From'] = formataddr(('title.cc.bot@', settings.SENDER_MAIL))
        msg['To'] = ', '.join(recivers)
        msg['Subject'] = 'Нове замовлення '

        content = self.get_view()
        msg.attach(MIMEText(content, "html"))


        with smtplib.SMTP_SSL(settings.SMTP_SERVER) as server:
            server.login(settings.SENDER_MAIL, settings.SMTP_PASS)
            server.send_message(msg)





NEED_ADMIN_PANEL_VALUES = {
    'NeedAdminPanelYes': True,
    'NeedAdminPanelNo': False,
}


@bot.message_handler(commands=['start', 'help'])
def start(message):
    bot.send_message(message.chat.id, response_texts.WELCOME.format(message.from_user.first_name))


@bot.message_handler(func=lambda msg: 'order' in msg.text)
def create_order(message):
    user_name = message.from_user.first_name
    chat_id = message.chat.id
    new_order = Order(user_name)
    Order.LIST[chat_id] = new_order

    mkp = ReplyKeyboardMarkup(resize_keyboard=True)
    mkp.add(KeyboardButton('Скасувати заявку'))
    bot.send_message(message.chat.id, 'Створеня заявки на розробку бота розпочато:', reply_markup=mkp)
    desc_destination_step(message)


@bot.message_handler(func=lambda msg: 'segments' in msg.text)
def segments_list(message):
    bot.send_message(message.chat.id, response_texts.SEGMENTS, parse_mode='html')


@bot.message_handler(func=lambda msg: 'technology' in msg.text)
def technology_list(message):
    bot.send_message(message.chat.id, response_texts.TECHNOLOGY)


@bot.message_handler(func=lambda msg: 'about' in msg.text)
def about_us(message):
    bot.send_message(message.chat.id, response_texts.ABOUT_US)


@bot.callback_query_handler(func=lambda msg: True)
def callback_query_handler(call):
    chat_id = call.message.chat.id
    if call.data in NEED_ADMIN_PANEL_VALUES:
        order = Order.LIST[chat_id]
        order.need_admin_panel = NEED_ADMIN_PANEL_VALUES[call.data]
        input_contacts_step(call.message)


def error_handler(func):
    def wrapper(message):
        try:
            func(message)
        except Exception as e:
            logger.error(e)
            bot.reply_to(message, response_texts.ERROR_MESSAGE)
    return wrapper


def interruption_handler(func):
    def wrapper(message):
        if 'скасувати заявку' in message.text.lower():
            bot.clear_step_handler_by_chat_id(message.chat.id)
            mkp = ReplyKeyboardRemove()
            bot.delete_message(message.chat.id, message.message_id)
            bot.send_message(message.chat.id, 'Заявку скасовано', reply_markup=mkp)
        else:
            func(message)
    return wrapper


@error_handler
@interruption_handler
def desc_destination_step(message):
    bot.send_message(message.chat.id, 'Вкажіть призначеня бота:')
    bot.register_next_step_handler(message, desc_functions_step)


@error_handler
@interruption_handler
def desc_functions_step(message):
    order = Order.LIST[message.chat.id]
    order.bot_destination = message.text
    bot.send_message(message.chat.id, 'Опишіть функціонал який Вам потрібен:')
    bot.register_next_step_handler(message, need_admin_panel_step)


@error_handler
@interruption_handler
def need_admin_panel_step(message):
    order = Order.LIST[message.chat.id]
    order.bot_functions = message.text

    mkp = InlineKeyboardMarkup()
    mkp.add(InlineKeyboardButton('Так', callback_data='NeedAdminPanelYes'),
            InlineKeyboardButton('Ні', callback_data='NeedAdminPanelNo'))

    bot.send_message(message.chat.id, 'Потрібна адмін панель?', reply_markup=mkp)


@error_handler
@interruption_handler
def input_contacts_step(message):
    bot.send_message(message.chat.id, 'Як з вами зв\'язатись? ' 
                                      '\nВкажіть номер телефону, електронну пошту або інші контакти. ')
    bot.register_next_step_handler(message, finale_create_order_step)


@error_handler
@interruption_handler
def finale_create_order_step(message):
    order = Order.LIST[message.chat.id]
    order.contacts = message.text.strip()
    try:
        order.save()
        order.send_order()
        order_text = order.get_view()
        bot.send_message(message.chat.id, order_text, parse_mode='html', reply_markup=ReplyKeyboardRemove())
        bot.send_message(message.chat.id, 'Заявку прийнято! Ми зв\'яжемось з Вами найближчим часом.')

    except Exception as e:
        logger.error(e)
        bot.send_message(message.chat.id, response_texts.ERROR_MESSAGE)


def run_bot():
    print('BOT STARTED')
    bot.infinity_polling()


if __name__ == '__main__':
    run_bot()
