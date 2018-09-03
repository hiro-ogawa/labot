# -*- coding: utf-8 -*-

# laundromat.py
# Copyright (c) 2018 Hironori Ogawa
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
import base64

def post_remote_ope_command(sid, mno):
    print(sid, mno)
    return 'OK'

def get_shopinfo_from_coordinate(latitude, longitude):
    info_dict = {
        'sid': 'sid',
        'oid': 'oid',
        'name': 'とあるコインランドリー',
        'address': '皇居',
        'latitude': '35.6847988',
        'longitude': '139.7492607',
    }
    return info_dict

def get_shopimage(oid, sid):
    fname = 'shopimage/coin_laundry.jpg'
    with open(fname, "rb") as f:
        ret = base64.b64encode(f.read())
    return ret

def get_operatingstatus(oid, sid):
    info_list = [{
        'mno': '01',
        'name': '洗濯機',
        'state': '空',
    }]
    return info_list

def get_machineinfo(oid, sid):
    m_list = ['01']
    return m_list

def get_course(oid, sid, mno):
    c_list = [{
        'name': '標準コース',
        'amount': 1000,
        'currency': 'JPY',
    }]
    return c_list

def get_memberid(oid):
    m_list = [
        '123',
        '456',
    ]
    return m_list

def get_shopname(oid, sid):
    return 'とあるコインランドリー'

def get_salesdetailsinfo(oid):
    ret = [{
        'date': '2018/07/17',
        'amount': 100,
    }]
    return ret

def get_opedetailsinfo_from_shopid(oid, sid):
    ret = ['01']
    return ret
