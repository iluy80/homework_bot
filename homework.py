import os
import time
import telegram
import requests
import logging
import tg_logger
import json
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s, %(levelname)s, %(message)s')
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=None)
logger.addHandler(handler)
handler = tg_logger.setup(logger,
                          token=TELEGRAM_TOKEN, users=TELEGRAM_CHAT_ID)


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Функция отправляет сообщение в телегрвм чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.TelegramError:
        logging.error('Соощение не отправляется')


def get_api_answer(current_timestamp):
    """Делаем запрос к сайту и возвращаем запрос с данными JSON."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if homework_statuses.status_code != requests.codes.ok:
            logging.error('Сервер возвращает код, отличный от 200')
            raise
        try:
            return homework_statuses.json()
        except json.decoder.JSONDecodeError:
            logging.error('ответ не преобразуется в json')
    except requests.RequestException as error:
        logging.error(f'Ошибка отправки запроса. {error}')


def check_response(response):
    """Проверяем ответ API, функция должна вернуть список домашних работ."""
    if not isinstance(response, dict):
        raise TypeError('Ошибка, возвращаетс не словарь')
    if 'homeworks' not in response and 'status' not in \
            response['homeworks'][0]:
        raise TypeError('Ошибка, ключей нет')
    if isinstance(response['homeworks'], list):
        try:
            homeworks = response['homeworks']
        except Exception as error:
            logging.error(f'Ошибка {error}')
            raise TypeError(f'Ошибка {error}')
        else:
            return homeworks


def parse_status(homework):
    """Извлекаем из информации о конкретной домашней работе ее статус."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework:
        verdict = HOMEWORK_VERDICTS[f'{homework_status}']
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        verdict != HOMEWORK_VERDICTS[f'{homework_status}']
        logging.error('Ключей в вердикте нет')


def check_tokens():
    """Проверяем доступность переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    # current_timestamp = int(time.mktime((2022, 1, 29, 7, 27, 0, 2, 294, 0)))

    while True:
        try:
            response = get_api_answer(current_timestamp)
            check_resp = check_response(response)
            if check_resp:
                status = parse_status(check_resp[0])
                send_message(bot, status)
            else:
                logging.debug('Работы нет в проверке')
            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.critical(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
