# coding: utf-8
import re

from jenkinsapi.jenkins import Jenkins
import time
import configparser
import warnings
from urllib3.exceptions import InsecureRequestWarning

warnings.simplefilter('ignore', InsecureRequestWarning)

config = configparser.ConfigParser()
config.read('D:/GH/nguk/config/global_config.cfg')

LINES_NUMBER = 15  # Количество последних строк из консоли билда
jenkins_url = 'https://jenkins.new-mmc.com'

username = config['jenkins_bot']['username']
password = config['jenkins_bot']['password']
job_name = config['jenkins_bot']['job_name']


def get_build_console_output(build):
    console_output = build.get_console()
    corrected_console_output = console_output.encode('latin1').decode('utf-8')
    corrected_console_output = corrected_console_output.splitlines()
    corrected_console_output = '\n'.join(corrected_console_output[-LINES_NUMBER:])
    return corrected_console_output


def deploy_app(app_id, app_name, app_tag):
    parameters = {
        'SERVER_NAME': config['jenkins_bot']['SERVER_NAME'],
        'KIND_OF_APP': f'{app_id}:{app_name}:[{app_tag}]',
        'APP_VERSION': app_tag,
        'DEPLOY_TARGET': config['jenkins_bot']['DEPLOY_TARGET'],
        'DREMIO_CONNECTOR': config['jenkins_bot']['DREMIO_CONNECTOR'],
        'NGINX_TEMPLATE': config['jenkins_bot']['NGINX_TEMPLATE']
    }

    server = Jenkins(jenkins_url, username=username, password=password, ssl_verify=False)
    job = server[job_name]

    # Запуск работы
    job.invoke(build_params=parameters)
    print('Start job')


    # last_build_num = -1
    while job.is_queued_or_running() or job.is_running():
        print('Всё еще в работе')

        # build_num = job.get_last_build()
        # if last_build_num != build_num:
        #     last_build_num = build_num

        time.sleep(5)

    # last_build_num = re.search(r'#\d+', str(last_build_num)).group()

    last_build = job.get_last_build()

    print('Джоба закончила работу. Статус:')
    if last_build.is_good():
        print('Успешно')
        return True, None  # deploy_status, console_log
    else:
        print('Неудача')

        corrected_console_output = get_build_console_output(last_build)
        # print(f'Вывод {LINES_NUMBER} строк логов билда:')
        # print(corrected_console_output)

        return False, corrected_console_output  # deploy_status, console_log

# if __name__=='__main__':
#     app_id = '27'
#     app_name = 'Test'
#     app_tag = 'test'
#     deploy_app(app_id, app_name, app_tag)
