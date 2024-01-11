import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv as ld2
from telegram.error import TelegramError

from exceptions import (AccessStatusError, EmptyHWList, RequestError,
                        SendError)

ld2()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 60
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Удачная отправка сообщения!')
    except TelegramError as error:
        raise SendError(
            f'Неудачная отправка сообщения! {error}'
        )


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        hw_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params,
        )
    except RequestError as error:
        raise RequestError(f'Ошибка в запросе: {error}')
    if hw_statuses.status_code != 200:
        status_code = hw_statuses.status_code
        raise AccessStatusError(f'Ошибка доступа {status_code}')
    try:
        return hw_statuses.json()
    except ValueError as error:
        raise ValueError(f'Ошибка парсинга: {error}')


def check_response(response):
    if not isinstance(response, dict):
        raise TypeError('Ответ не совпадает со словарем')
    if 'homeworks' not in response.keys():
        raise KeyError('Данный ключ отсутствует')
    hw_roster = response['homeworks']
    if not isinstance(hw_roster, list):
        raise TypeError('Тип не совпадает со списком')
    if len(hw_roster) == 0:
        raise EmptyHWList('Список ДЗ пуст')
    return hw_roster[0]


def parse_status(homework):
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ homework_name')
    if 'status' not in homework:
        raise KeyError('Отсутствует  ключ "status"')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES.keys():
        raise KeyError(f'Неизвестный статус {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}": {verdict}'


def check_tokens():
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True


def main():
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    error_saving_message = ''
    if not check_tokens():
        logger.critical('Недоступность переменных окружения')
        sys.exit(1)
    while True:
        try:
            response = get_api_answer(current_timestamp)
            message = parse_status(check_response(response))
            if message != status:
                send_message(bot, message)
                status = message
        except SendError as error:
            logger.error(
                f'Неудачная отправка сообщения! {error}'
            )
        except Exception as error:
            logger.error(error)
            message_error = f'Сбой в работе программы: {error}'
            if message_error != error_saving_message:
                send_message(bot, message_error)
                error_saving_message = message_error
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='program.log',
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s, %(lineno)s',
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    handler = RotatingFileHandler(
        'main.log',
        maxBytes=50000000,
        backupCount=5,
        encoding='utf-8',
    )
    logger.addHandler(handler)

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(lineno)s'
    )

    handler.setFormatter(formatter)
    main()
