# homework_bot
python telegram bot

## Описание
Бот обращается к API сервиса Практикум.Домашка, узнает, взята ли домашняя работа в ревью, проверена ли она, провалена или принята и отправляет результат в Телеграм-чат. Дополнительно реализовано логгирование.

## Технологии
* Python 3.9 
* python-telegram-bot 13.7

## Запуск проекта

- Установите и активируйте виртуальное окружение
```
python -m venv venv
source venv/Scripts/activate
```
- Установите зависимости из файла requirements.txt
```
python -m pip install --upgrade pip
pip install -r requirements.txt
```
- в корневой директории проекта создать файл .env и указать:

PRACTICUM_TOKEN: токен Яндекс.Практикума ([как получить?](https://oauth.yandex.ru/authorize?response_type=token&client_id=1d0b9dd4d652455a9eb710d450ff456a))  
TELEGRAM_TOKEN: токен Telegram-бота, полученный от BotFather ([как получить?](https://core.telegram.org/bots/features#botfather))  
TELEGRAM_CHAT_ID: id Telegram-аккаунта для получения собщений ([как получить?](https://t.me/userinfobot))  

- после импортирования в проект в качестве константных значений токенов и id, указанных в файле _.env_, бот готов к запуску

Более подробно с информацией о создании Telegram-ботов можно ознакомиться в [официальной документации](https://core.telegram.org/bots/api).

## _Разработчики_
[Поляков Святослав](https://github.com/svtplv)
