import logging
import logging.config
import os
import time
from http import HTTPStatus
from sys import stdout

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (ApiNotAvailable, EnvVariableMissing,
                        HomeWorkVerdictError, ResponseValidationError)

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


def check_tokens():
    """Проверяет доступность обязательных переменных окружения."""
    TOKENS = dict(
        PRACTICUM_TOKEN=PRACTICUM_TOKEN,
        TELEGRAM_TOKEN=TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID=TELEGRAM_CHAT_ID
    )
    missing_tokens = [
        token for token, value in TOKENS.items() if not value
    ]
    if missing_tokens:
        logging.critical(
            f'Отсутствует переменные окружения {" ,".join(missing_tokens)}'
        )
        raise EnvVariableMissing


def send_message(bot, message):
    """
    Отправляет сообщение в Telegram чат.

    :param bot: Бот, отправляющий сообщение
    :param message: Сообщение

    """
    logging.debug('Пытаемся отправить сообщение')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено успешно')
    except telegram.TelegramError as error:
        logging.error(f'При отправлении сообщения возникла ошибка {error}')


def get_api_answer(timestamp):
    """
    Делает запрос к единственному эндпоинту API-сервиса.

    :param timestamp: Временная метка unix

    """
    payload = {'from_date': timestamp}
    try:
        logging.debug(
            f'Отправляем запрос к API, эндпоинт - {ENDPOINT}, '
            f'параметры - {payload}'
        )
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
    if response.status_code != HTTPStatus.OK:
        logging.error(
            f'API вернуло ответ, отличный от 200. Код {response.status_code}'
        )
        raise ApiNotAvailable
    logging.debug('Запрос к API: успех')
    return response.json()


def check_response(response):
    """
    Проверяет ответ API на соответствие документации.

    :param response: Ответ в формате JSON

    """
    logging.debug('Начинаем проверку API на соответствие документации')
    REQUIRED_KEYS = ('homeworks', 'current_date')
    if not isinstance(response, dict):
        logging.error(
            f'Некорректный тип данных у параметра response - {type(response)}.'
        )
        raise TypeError
    logging.debug('Проверка типа данных у параметра response: Успех')
    missing_keys = [
        key for key in REQUIRED_KEYS if key not in response
    ]
    if missing_keys:
        logging.error(f'Отсутствуют ключи: {", ".join(missing_keys)}')
        print(response)
        raise ResponseValidationError
    logging.debug('Проверка ключей в словаре: Успех')
    if not isinstance(response['homeworks'], list):
        logging.error('Некорректный тип данных у словаря Д/З')
        raise TypeError
    logging.debug('Проверка типа данных по ключу homeworks: Успех')


def parse_status(homework):
    """
    Извлекает из информации о конкретной Д/З статус этой работы.

    :param homework: Последняя домашняя работа

    """
    logging.debug('Проверка статуса домашней работы')
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('Отсутствует ключ homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise HomeWorkVerdictError
    verdict = HOMEWORK_VERDICTS[homework_status]
    logging.debug('Статус получен - {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    previous_message = None
    while True:
        try:
            timestamp = int(time.time())
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
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': True
    })
    logging.basicConfig(
        format=(
            '%(asctime)s - %(levelname)s - '
            '%(funcName)s:%(lineno)d - %(message)s'
        ),
        level=logging.DEBUG,
        stream=stdout
    )
    main()
