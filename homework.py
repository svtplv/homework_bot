import logging
import os
import time
from sys import stdout

from http import HTTPStatus
import requests
from dotenv import load_dotenv
import telegram

from exceptions import (
    ApiNotAvailable,
    EnvVariableMissing,
    HomeWorkVerdictError,
    ResponseValidationError
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    stream=stdout
)


def check_tokens():
    """Проверяет доступность обязательных переменных окружения."""
    TOKENS = dict(
        PRACTICUM_TOKEN=PRACTICUM_TOKEN,
        TELEGRAM_TOKEN=TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID=TELEGRAM_CHAT_ID
    )
    for key, value in TOKENS.items():
        if value is None:
            logging.critical(f'Отсутствует переменная окружения {key}')
            raise EnvVariableMissing


def send_message(bot, message):
    """
    Отправляет сообщение в Telegram чат.

    :param bot: Бот, отправляющий сообщение
    :param message: Сообщение

    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено успешно')
    except Exception as error:
        logging.error(f'При отправлении сообщения возникла ошибка {error}')


def get_api_answer(timestamp):
    """
    Делает запрос к единственному эндпоинту API-сервиса.

    :param timestamp: Временная метка unix

    """
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
    if response.status_code != HTTPStatus.OK:
        logging.error(
            f'API вернуло ответ, отличный от 200. Код {response.status_code}'
        )
        raise ApiNotAvailable
    return response.json()


def check_response(response):
    """
    Проверяет ответ API на соответствие документации.

    :param response: Ответ в формате JSON

    """
    if not isinstance(response, dict):
        logging.error('Некорректный тип данных у параметра response.')
        raise TypeError
    if 'homeworks' not in response and 'current_time' not in response:
        logging.error(
            f'Недостает обязательных ключей. Ключи: {response.keys()}'
        )
        raise ResponseValidationError
    if not isinstance(response['homeworks'], list):
        logging.error('Некорректный тип данных у словаря Д/З')
        raise TypeError


def parse_status(homework):
    """
    Извлекает из информации о конкретной Д/З статус этой работы.

    :param homework: Последняя домашняя работа

    """
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('Отсутствует ключ homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise HomeWorkVerdictError
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    previous_message = None
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            try:
                message = parse_status(response['homeworks'][0])
            except (IndexError, KeyError):
                message = 'Домашняя работа еще не была отправлена на проверку.'
            except HomeWorkVerdictError:
                message = 'Ошибка, неожиданный статус домашней работы.'
            if message != previous_message:
                send_message(bot, message)
                previous_message = message
            else:
                logging.debug('Статус домашней работы не менялся')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
