import os
import sys

if len(sys.argv) > 1:
    if sys.argv[1] == '-t':
        TELEGRAM_API_KEY = '5237614948:AAF1sfGVhikBmAb9BeN_2YeQj-n2akZjDBA'
else:
    TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY_TITLE_BOT')

DB_NAME = 'bot_db'
SENDER_MAIL = os.getenv('SENDER_MAIL')
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PASS = os.getenv('SMTP_PASS')