import os
import time
import telegram
import requests
import logging
import tg_logger
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('practicum_token')
TELEGRAM_TOKEN = os.getenv('telegram_token')
TELEGRAM_CHAT_ID = os.getenv('telegram_chat_id')

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


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Функция отправляет сообщение в телегрвм чат."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


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
        return homework_statuses.json()
    except requests.RequestException as error:
        logging.error(f'Ошибка отправки запроса. {error}')


def check_response(response):
    """Проверяем ответ API, функция должна вернуть список домашних работ."""
    if isinstance(response['homeworks'], list):
        return response['homeworks']


def parse_status(homework):
    """Извлекаем из информации о конкретной домашней работе ее статус."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[f'{homework_status}']
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем доступность переменных окружения."""
    for env in [PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN]:
        if not env:
            return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    # current_timestamp = int(time.mktime((2022, 2, 1, 7, 28, 0, 2, 294, 0)))

    while True:
        try:
            response = get_api_answer(current_timestamp)
            check_resp = check_response(response)
            status = parse_status(check_resp[0])
            send_message(bot, status)

            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.critical(message)
            time.sleep(RETRY_TIME)
        else:
            return main()


if __name__ == '__main__':
    main()
