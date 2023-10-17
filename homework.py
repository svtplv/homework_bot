import logging
import logging.config
import os
import time
from http import HTTPStatus
from sys import stdout

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ApiNotAvailable, EnvVariableMissing

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
    logging.debug('Начинаем отправку сообщения')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено успешно')
    except telegram.error.TelegramError:
        raise


def get_api_answer(timestamp):
    """
    Делает запрос к единственному эндпоинту API-сервиса.

    :param timestamp: Временная метка unix

    """
    payload = {'from_date': timestamp}
    try:
        logging.debug(
            f'Начинаем отправку запроса к API, эндпоинт - {ENDPOINT}, '
            f'параметры - {payload}'
        )
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except ConnectionError('Ошибка при запросе к основному API'):
        raise
    if response.status_code != HTTPStatus.OK:
        raise ApiNotAvailable(
            f'API вернуло ответ, отличный от 200. '
            f'Код {response.status_code}-{response.reason}'
        )
    logging.debug('Запрос к API: успех')
    return response.json()


def check_response(response):
    """
    Проверяет ответ API на соответствие документации.

    :param response: Ответ в формате JSON

    """
    logging.debug('Начинаем проверку API на соответствие документации')
    PUBLIC_ERROR_MESSAGE = 'API не соответствует документации'
    REQUIRED_KEYS = ('homeworks', 'current_date')
    if not isinstance(response, dict):
        raise TypeError(
            PUBLIC_ERROR_MESSAGE,
            f'Некорректный тип данных у параметра response - {type(response)}.'
        )
    logging.debug('Проверка типа данных у параметра response: Успех')
    missing_keys = [
        key for key in REQUIRED_KEYS if key not in response
    ]
    if missing_keys:
        raise KeyError(
            PUBLIC_ERROR_MESSAGE,
            f'Отсутствуют ключи: {", ".join(missing_keys)}'
        )
    logging.debug('Проверка ключей в словаре: Успех')
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            PUBLIC_ERROR_MESSAGE,
            f'Некорректный тип данных у словаря Д/З - {response["homeworks"]}'
        )
    logging.debug('Проверка типа данных по ключу homeworks: Успех')
    return response['homeworks']


def parse_status(homework):
    """
    Извлекает из информации о конкретной Д/З статус этой работы.

    :param homework: Последняя домашняя работа

    """
    logging.debug('Начинаем проверку статуса домашней работы')
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError(
            'Отсутствует название домашней работы',
            'Отсутствует ключ: homework_name'
        )
    homework_status = homework.get('status')
    if homework_status is None:
        raise KeyError(
            'Отсутствуют данные о статусе домашней работы',
            'Отсутствует ключ: status'
        )
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(
            'Неожиданный статус домашней работы', homework_status
        )
    verdict = HOMEWORK_VERDICTS[homework_status]
    logging.debug(f'Статус получен - {homework_status}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    previous_message = None
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
                send_message(bot, message)
            else:
                logging.debug('Статус домашнего задания не')
            timestamp = int(time.time())
        except telegram.error.TelegramError as error:
            logging.error(f'Ошибка при попытке отправить сообщение - {error}')
        except Exception as error:
            log_message = ' - '.join(error.args)
            logging.error(log_message)
            public_message = f'Сбой в работе программы: {error.args[0]}'
            if public_message != previous_message:
                try:
                    send_message(bot, public_message)
                    previous_message = public_message
                except telegram.error.TelegramError:
                    logging.error(
                        f'Ошибка при попытке отправить сообщение - {error}',
                        exc_info=True
                    )
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
