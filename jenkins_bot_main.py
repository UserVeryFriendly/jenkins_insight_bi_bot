# coding: utf-8

import configparser
# import sys
import threading
import time
import traceback

from psycopg2 import OperationalError
import telebot
from telebot import types

from authentication import authenticate_user, no_authenticate_user, db_connection
from jenkins_deploy import deploy_app
from job_queue import JobQueue
from kind_of_app import html_build

config = configparser.ConfigParser()
config.read('D:/GH/nguk/config/global_config.cfg')

MAINTAINER_ID = 350129540

CONNECTION_DELAY = 3
CONNECTION_RETRIES = 5

QUEUE_DELAY = 5
RESTART_DELAY = 5

API_TOKEN = config['TOKEN']['test_try']
bot = telebot.TeleBot(API_TOKEN)


def confirmation_kb(is_start, selected_app):
    kb = types.InlineKeyboardMarkup(row_width=2)
    if is_start:
        no_button = types.InlineKeyboardButton(
            'Нет',
            callback_data=f'start_no_confirm_job'
        )
    else:
        no_button = types.InlineKeyboardButton(
            'Нет',
            callback_data='no_confirm_job'
        )
    yes_button = types.InlineKeyboardButton(
        'Да',
        callback_data=f'confirm_job_{selected_app}'
    )
    kb.add(yes_button, no_button)

    return kb


def send_err_message():
    bot.send_message(
        chat_id=MAINTAINER_ID,
        text=f'Error traceback:\n{traceback.format_exc()}'
    )


def take_apps(message):
    app_list = html_build()
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for app_info in app_list:
        app_id, app_name, app_tag = app_info.split(':')
        app_tag = app_tag.replace('"', '')
        button_text = f'{app_id}:{app_name}:{app_tag}'
        keyboard.add(types.KeyboardButton(button_text))

    bot.send_message(message.chat.id, 'Выберите приложение', reply_markup=keyboard)


def handle_exception():
    print(f'Error traceback:\n{traceback.format_exc()}')
    send_err_message()
    stop_event.set()


def job_processor(jobs, stop_event_flag, tg_bot):
    while not stop_event_flag.is_set():
        try:
            app_user_id = jobs.get_job()
            if app_user_id:
                selected_app, chat_id = app_user_id.split('|', maxsplit=1)

                app_id, app_name, app_tag = selected_app.split(':')
                app_tag = app_tag.replace('[', '').replace(']', '').replace("'", '')

                deploy_msg = tg_bot.send_message(chat_id, f'Деплой приложения {app_tag} пошел, ожидай статуса')
                deploy_status, build_console_log = deploy_app(app_id, app_name, app_tag)

                tg_bot.delete_message(chat_id, deploy_msg.message_id)
                if deploy_status:
                    tg_bot.send_message(chat_id, f'Приложение {app_tag} успешно развернуто.✅')

                    if build_console_log:
                        tg_bot.send_message(MAINTAINER_ID, build_console_log)
                    tg_bot.send_message('-4014525230', f'Приложение {app_tag} успешно развернуто.✅')
                else:
                    tg_bot.send_message(chat_id, f'Не удалось развернуть приложение {app_tag}.❌')

                    if build_console_log:
                        tg_bot.send_message(MAINTAINER_ID, build_console_log)
                    confirm_retry(chat_id, selected_app, tg_bot)

                # Очистка текущей работы
                jobs.release_current_job()
            time.sleep(QUEUE_DELAY)
        except Exception:
            handle_exception()
            # Остановка полинга бота
            tg_bot.stop_polling()
            # Очистка текущей работы
            jobs.release_current_job()
            time.sleep(RESTART_DELAY)  # Задержка перед перезапуском
            return


def bot_polling_thread(stop_event_flag, tg_bot):
    while not stop_event_flag.is_set():
        try:
            # Сброс флага для продолжения поллинга
            if tg_bot._TeleBot__stop_polling.is_set():
                tg_bot._TeleBot__stop_polling.clear()

            tg_bot.infinity_polling()
        except Exception:
            handle_exception()
            time.sleep(RESTART_DELAY)  # Задержка перед перезапуском
            return


def check_conn():
    global conn
    try:
        conn = db_connection()
    except OperationalError:
        bot.send_message(MAINTAINER_ID, f'Ошибка создания подключения к БД:\n{traceback.format_exc()}')
        tries = 0
        while tries < CONNECTION_RETRIES:
            try:
                time.sleep(CONNECTION_DELAY)
                conn = db_connection()
            except OperationalError:
                bot.send_message(MAINTAINER_ID, f'Попытка подключения №{tries + 1} не удалась.')
                tries += 1


@bot.message_handler(func=lambda message: message.chat.type == 'private', commands=['start'])
def start(message):
    global conn
    if conn and conn.closed:
        check_conn()

    if authenticate_user(conn, message):
        loading_message = bot.send_message(message.chat.id, 'Идет подгрузка Аппов, ожидайте')
        take_apps(message)
        bot.delete_message(message.chat.id, loading_message.message_id)
    else:
        no_authenticate_user(conn, message)


@bot.message_handler(func=lambda message: message.chat.type == 'private', commands=['queue'])
def print_queue(message):
    global conn
    if conn and conn.closed:
        check_conn()

    if authenticate_user(conn, message):
        jobs = job_queue.queue_list()

        if job_queue.current_job:
            selected_app, _ = job_queue.current_job.split('|', maxsplit=1)
            output_current_job = 'Сейчас в работе: '
            output_current_job += selected_app + '\n'
        else:
            output_current_job = 'В работе нет приложений\n'

        if jobs:
            output_jobs = 'В очереди:\n'
            for job in jobs:
                selected_app, _ = job.split('|', maxsplit=1)
                output_jobs += selected_app + '\n'
        else:
            output_jobs = 'Очередь пуста'
        bot.send_message(message.chat.id, output_current_job + output_jobs)
    else:
        no_authenticate_user(conn, message)


@bot.message_handler(func=lambda message: message.chat.type == 'private', commands=['conn'])
def refresh_connection(message):
    global conn

    if authenticate_user(conn, message):
        if conn:
            conn.close()
        check_conn()
        bot.send_message(message.chat.id, 'Соединение с БД пересоздано.')
    else:
        no_authenticate_user(conn, message)


@bot.message_handler(func=lambda message: message.chat.type == 'private')
def echo_message(message):
    global conn
    if conn and conn.closed:
        check_conn()

    if authenticate_user(conn, message):
        if message.text:
            selected_app = message.text
            bot.send_message(
                message.chat.id,
                f'Вы уверены в выборе {selected_app}?',
                reply_markup=confirmation_kb(is_start=True, selected_app=selected_app)
            )
    else:
        no_authenticate_user(conn, message)


@bot.callback_query_handler(func=lambda callback: callback.data == 'no_confirm_job')
def no_confirm_job(callback):
    bot.answer_callback_query(callback.id)
    bot.delete_message(callback.message.chat.id, callback.message.message_id)


@bot.callback_query_handler(func=lambda callback: callback.data == 'start_no_confirm_job')
def no_confirm_start(callback):
    bot.answer_callback_query(callback.id)
    bot.delete_message(callback.message.chat.id, callback.message.message_id)

    start(callback.message)


@bot.callback_query_handler(func=lambda callback: callback.data.startswith('confirm_job_'))
def yes_confirm_job(callback):
    selected_app = callback.data.removeprefix('confirm_job_')

    job_queue.add_job(f'{selected_app}|{callback.from_user.id}')

    bot.answer_callback_query(callback.id)
    bot.delete_message(callback.message.chat.id, callback.message.message_id)


def confirm_retry(chat_id, selected_app, tg_bot):
    tg_bot.send_message(
        chat_id,
        f'Вы хотите повторить деплой {selected_app}?',
        reply_markup=confirmation_kb(is_start=False, selected_app=selected_app)
    )


def main():
    global conn
    if conn:
        conn.close()
    check_conn()

    job_processor_thread = threading.Thread(target=job_processor, args=(job_queue, stop_event, bot))
    job_processor_thread.start()

    polling_thread = threading.Thread(target=bot_polling_thread, args=(stop_event, bot))
    polling_thread.start()

    # Дожидаемся завершения работы обоих потоков
    job_processor_thread.join()
    polling_thread.join()


if __name__ == '__main__':

    conn = None
    job_queue = JobQueue()
    stop_event = threading.Event()

    while True:
        stop_event.clear()
        main()

    # try:
    #     # conn = db_connection()
    #     # bot.infinity_polling()
    #     main()
    # except Exception:
    #     print(
    #         f'Error traceback:\n'
    #         f'{traceback.format_exc()}'
    #     )
    #     send_err_message()
    #     # main()
    # finally:
    #     if conn:
    #         conn.close()



