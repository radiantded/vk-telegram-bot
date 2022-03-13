import datetime
import logging
import os
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater


load_dotenv()

# НАСТРОЙКИ ЛОГГИРОВАНИЯ

TIME_FORMAT = "%Y-%m-%d_%H-%M"
CONSOLE_HANDLER = logging.StreamHandler()
LOG_HANDLER = RotatingFileHandler(
    '{}.log'.format(
        datetime.datetime.now().strftime(TIME_FORMAT)),
    mode='a', maxBytes=50*1024,
    backupCount=10, encoding='utf-8', delay=0
)
logging.basicConfig(
    handlers=(LOG_HANDLER, CONSOLE_HANDLER),
    format='[%(asctime)s | %(levelname)s]: %(message)s',
    datefmt=TIME_FORMAT,
    level=logging.INFO
)

# НАСТРОЙКИ ПОДКЛЮЧЕНИЯ

VK_API_URL = 'https://api.vk.com/method/'
VK_API_VERSION = '5.131'
VK_TOKEN = os.environ.get('vk_token')
TELEGRAM_TOKEN = os.environ.get('tg_token')

# НАСТРОЙКИ БОТА

POSTS_TO_GET = 100
WELCOME_MESSAGE = """
Привет! Отправь название группы ВК и ключевое слово
в формате <группа, слово, минимальное количество лайков>
"""
OK_MESSAGE = 'Самых популярных постов в группе "{}" с искомым словом "{}": {}'
FAIL_MESSAGE = 'Неверный формат запроса!'
NO_POSTS_MESSAGE = 'Постов с заданными параметрами не нашлось!'


def get_most_liked_posts(group_name: str, min_likes: str):
    """Получает посты указанной группы в соответствии
       с заданным минимальным количеством лайков"""

    logging.info(f'Получаю посты группы "{group_name}". '
                 f'Порог лайков: {min_likes}')
    url = '{}wall.get?domain={}&count={}&access_token={}&v={}'.format(
        VK_API_URL, group_name, POSTS_TO_GET, VK_TOKEN, VK_API_VERSION)
    request = requests.get(url)
    most_liked_posts = [
        x for x in request.json().get(
            'response').get(
                'items') if x.get('likes').get('count') >= int(min_likes)
    ]
    return most_liked_posts


def get_target_posts(posts: list, target: str):
    """Фильтрует посты в соответствии с заданным ключевым словом"""

    logging.info(f'Фильтрую посты по ключевому слову "{target}"')
    target_posts = [p for p in posts if target in p.get('text')]
    return target_posts


def main(update, context):
    message = update.message.text
    try:
        group_name, target, min_likes = message.split(', ')
    except ValueError:
        logging.error(f'Пользователь ввёл некорректный запрос: {message}')
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=FAIL_MESSAGE
        )
    try:
        most_liked_posts = get_most_liked_posts(group_name, min_likes)
        if most_liked_posts:
            target_posts = get_target_posts(most_liked_posts, target)
            target_posts_count = len(target_posts)
            logging.info(f'Получено постов: {target_posts_count}')
            if target_posts:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=OK_MESSAGE.format(
                        group_name,
                        target,
                        target_posts_count
                    )
                )
                for post in target_posts:
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"{post.get('text')[:2000]}..."
                    )
            else:
                logging.info(f'Постов по запросу "{message}" не найдено')
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=NO_POSTS_MESSAGE
                )
    except Exception as error:
        logging.error(f'В ходе обработки запроса "{message}" '
                      f'возникла ошибка "{error}"')


def wake_up(update, context):
    """Отправляет приветственное сообщение"""

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=WELCOME_MESSAGE
    )


if __name__ == '__main__':
    logging.info('Инициализация бота')
    updater = Updater(token=TELEGRAM_TOKEN)
    updater.dispatcher.add_handler(CommandHandler('start', wake_up))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, main))
    updater.start_polling()
    updater.idle()
