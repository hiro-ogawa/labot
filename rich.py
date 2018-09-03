#!/usr/bin/python
# -*- coding: utf-8 -*-

# rich.py
# Copyright (c) 2018 Hironori Ogawa
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php

import os
import sys
import traceback
import json
from linebot import LineBotApi, WebhookHandler
from linebot.models import *

import time

# load from env
owner_bot_secret = os.environ['OWNER_BOT_SECRET']
owner_bot_token = os.environ['OWNER_BOT_TOKEN']
user_bot_secret = os.environ['USER_BOT_SECRET']
user_bot_token = os.environ['USER_BOT_TOKEN']

# setup LINE Messaging API
bot_api_owner = LineBotApi(owner_bot_token)
handler_owner = WebhookHandler(owner_bot_secret)
bot_api_user = LineBotApi(user_bot_token)
handler_user = WebhookHandler(user_bot_secret)

def get_user_rich_menu_areas():
    areas = [
        RichMenuArea(
            bounds=RichMenuBounds(x=0, y=0, width=1250, height=843),
            action=URIAction(
                label='位置情報',
                uri='line://nv/location')),
        RichMenuArea(
            bounds=RichMenuBounds(x=1250, y=0, width=1250, height=843),
            action=PostbackAction(
                data=json.dumps({
                    'mode': 'richmenu',
                    'data': [1, 0]}))),
        RichMenuArea(
            bounds=RichMenuBounds(x=0, y=843, width=1250, height=843),
            action=PostbackAction(
                data=json.dumps({
                    'mode': 'richmenu',
                    'data': [0, 1]}))),
    ]
    return areas

def new_richmenu(api, name, chat_bar_text, fname, areas=None):
    rich_menu_list = api.get_rich_menu_list()
    for rich_menu in rich_menu_list:
        api.delete_rich_menu(rich_menu.rich_menu_id)

    if not areas:
        areas = []
        for x in range(2):
            for y in range(2):
                areas.append(RichMenuArea(
                    bounds=RichMenuBounds(x=1250*x, y=843*y, width=1250, height=843),
                    action=PostbackAction(
                        data=json.dumps({
                            'mode': 'richmenu',
                            'data': [x, y]}))))

    rich_menu_to_create = RichMenu(
        size=RichMenuSize(width=2500, height=1686),
        selected=True,
        name=name,
        chat_bar_text=chat_bar_text,
        areas=areas,
    )
    rich_menu_id = api.create_rich_menu(rich_menu_to_create)
    with open(fname, 'rb') as f:
        api.set_rich_menu_image(rich_menu_id, 'image/jpeg', f)

if __name__ == "__main__":
    new_richmenu(bot_api_owner, 'Owner', 'オーナーメニュー', 'static/richmenu/owner.jpg')

    new_richmenu(bot_api_user, 'User', 'ユーザーメニュー', 'static/richmenu/user.jpg', get_user_rich_menu_areas())

    rich_menu_list = bot_api_owner.get_rich_menu_list()
    for rich_menu in rich_menu_list:
        print(rich_menu)

    rich_menu_list = bot_api_user.get_rich_menu_list()
    for rich_menu in rich_menu_list:
        print(rich_menu)

