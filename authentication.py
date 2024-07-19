# coding: utf-8

import psycopg2
import telebot
import configparser

config = configparser.ConfigParser()
config.read('D:/GH/nguk/config/global_config.cfg')

SERVER_NAME = config['jenkins_bot']['SERVER_NAME']

API_TOKEN = config['TOKEN']['test_try']
bot = telebot.TeleBot(API_TOKEN)


def authenticate_user(conn, message):
    user_id = message.chat.id
    return is_user_authenticated_in_postgresql(conn, user_id)


def no_authenticate_user(conn, message):
    user_id = message.chat.id
    username = message.from_user.username
    bot.send_message(message.chat.id, 'Пожалуйста, обратитесь к администратору для авторизации')
    add_user_to_postgresql(conn, user_id, username)


def db_connection():
    return psycopg2.connect(
        dbname=config['KHD_KC']['database'],
        user=config['KHD_KC']['user'],
        password=config['KHD_KC']['password'],
        host=config['KHD_KC']['host']
    )


def add_user_to_postgresql(conn, user_id, username):
    try:
        with conn.cursor() as cursor:
        # cursor = conn.cursor()
            cursor.execute('SELECT * FROM nsi.jenkins_bot_users WHERE tg_id = %s', (user_id,))
            existing_user = cursor.fetchone()
            if existing_user:
                cursor.execute('UPDATE nsi.jenkins_bot_users SET name_user = %s WHERE tg_id = %s', (username, user_id))
                conn.commit()
            else:
                cursor.execute('INSERT INTO nsi.jenkins_bot_users (tg_id, name_user) VALUES (%s, %s)', (user_id, username))
                conn.commit()
            print('Пользователь добавлен')
    except Exception as e:
        print('Ошибка при добавлении/обновлении пользователя в PostgreSQL:', e)
    # finally:
    #     cursor.close()


def is_user_authenticated_in_postgresql(conn, user_id):
    try:
        with conn.cursor() as cursor:
        # cursor = conn.cursor()
            cursor.execute('SELECT * FROM nsi.jenkins_bot_users WHERE tg_id = %s AND access = True', (user_id,))
            user = cursor.fetchone()
        return user is not None
    except Exception as e:
        print('Ошибка при проверке авторизации пользователя в PostgreSQL:', e)
    # finally:
    #     cursor.close()

# conn = db_connection()
