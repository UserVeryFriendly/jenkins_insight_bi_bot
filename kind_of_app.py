# coding: utf-8

import requests
from bs4 import BeautifulSoup
import configparser

config = configparser.ConfigParser()
config.read('D:/GH/nguk/config/global_config.cfg')

SERVER_NAME = config['jenkins_bot']['SERVER_NAME']

def doog_tags(html):
    soup = BeautifulSoup(html, 'html.parser')
    options = soup.find_all('option')
    apps_list = []
    for option in options:
        apps_list.append(option.text)
    return apps_list

def html_build():
    html = ''

    commit_options = ''
    dataset_list = get_dataset_list()
    for dataset in dataset_list:
        for keys in dataset:
            commit_options += f"<option style='font-style: italic' value='{keys}'>{keys}</option>"
    
    html += f'''
        <select id='player_version_h' size='1' name='value'>
            {commit_options}
        </select>
    '''

    return doog_tags(html)

# Вывод только с тэгом
def get_dataset_list():
    url = f'https://{SERVER_NAME}/api/project/listall?key=hf74jcv8e91k2dr14j8c34r84gvc34fg'
    response = requests.get(url, verify=False)
    response_data = response.json()

    sorted_response_data = sorted(response_data, key=lambda x: int(x['id']))

    my_list_of_ids = []

    for item in sorted_response_data:
        if item.get('tags'):
            my_list_of_ids.append(f"{item['id']}:{item['title']}:{item['tags']}".split('\n'))

    return my_list_of_ids


# apps = html_build()
# print(apps)
# for app in apps:
#     print(app)