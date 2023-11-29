import os
import sys
import logging
import time
from http import HTTPStatus
import requests
import telegram
from dotenv import load_dotenv


load_dotenv()


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}

HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}

EXPECTED_KEYS = ["homeworks", "current_date"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
file_handler = logging.FileHandler("log_bot.log", mode='a')
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(file_handler)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f"Сообщение в Telegram отправлено: {message}")
    except telegram.TelegramError:
        logger.error(f"Сбой при отправке сообщения в Telegram: {message}")


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту и возвращает ответ в случае обновления."""
    try:
        payload = {"from_date": timestamp}
        homeworks = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if homeworks.status_code != HTTPStatus.OK:
            logger.error("Эндпоинт недоступен")
            raise Exception("Эдпоинт недоступен")
        return homeworks.json()
    except requests.RequestException as error:
        logger.error(f"Ошибка: {error}")
    except Exception as error:
        logger.error(f"Ошибка при подключении к эдпоинту: {error}")
        raise Exception(f"Ошибка при подключении к эдпоинту: {error}")


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError("Ответ API не соответствует документации")
    elif "homeworks" not in response:
        raise KeyError("Ошибка: отсутствует ключ homeworks")
    elif not isinstance(response["homeworks"], list):
        raise TypeError("Неверный тип данных для homeworks")
    return response.get("homeworks")


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе ее статус."""
    try:
        homework_name = homework["homework_name"]
        homework_status = homework["status"]
        if homework_status not in HOMEWORK_VERDICTS:
            logger.error(
                f"Неожиданный статус домашней работы: {homework_status}"
            )
            raise Exception(
                "Неожиданный статус домашней работы: {homework_status}"
            )
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError("Ошибка: Отсутствует ключ homework_name"):
        logger.error("Ошибка: Отсутствует ключ homework_name")
    except Exception as error:
        logger.error(f"Ошибка при извлечении информации о работе: {error}")
        raise


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical(
            "Отсутствуют обязательные переменные"
            " окружения во время запуска бота"
        )
        sys.exit(
            "Отсутствуют обязательные переменные"
            " окружения во время запуска бота"
        )
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get("current_date")
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                if message:
                    send_message(bot, message)
        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
