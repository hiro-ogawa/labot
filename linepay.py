# -*- coding: utf-8 -*-

# linepay.py
# Copyright (c) 2018 Hironori Ogawa
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php

import os
import requests
import json
from pprint import pprint

# load from env
pay_id = os.environ['PAY_ID']
pay_secret = os.environ['PAY_SECRET']
pay_endpoint = os.environ['PAY_ENDPOINT']

headers = {
    'Content-Type': 'application/json',
    'X-LINE-ChannelId': pay_id,
    'X-LINE-ChannelSecret': pay_secret,
}

def request(transactionId=None, orderId=None):
    url = pay_endpoint
    payload = {}
    if transactionId:
        payload['transactionId'] = transactionId
    if orderId:
        payload['orderId'] = orderId
    r = requests.get(url, headers=headers, params=payload)

    return json.loads(r.text)

def reserve_request(productName, amount, currency, confirmUrl, orderId):
    url = pay_endpoint + '/request'
    payload = {
        'productName': productName,
        'amount': amount,
        'currency': currency,
        'confirmUrl': confirmUrl,
        'orderId': orderId,
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload))
    return json.loads(r.text)

def confirm(transactionId, amount, currency):
    url = pay_endpoint + '/{}/confirm'.format(transactionId)
    payload = {
        'amount': amount,
        'currency': currency,
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload))
    return json.loads(r.text)
