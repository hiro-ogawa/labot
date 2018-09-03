# -*- coding: utf-8 -*-

# labot.py
# Copyright (c) 2018 Hironori Ogawa
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php

import json
import os
import datetime
import base64
import concurrent.futures
import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from flask import Flask, request, abort, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import *

import laundromat as l
import linepay as pay

app = Flask(__name__)

# upload directory
upload_dir = 'static/temp'
if not os.path.exists(upload_dir):
    os.makedirs(upload_dir)

# load from env
owner_bot_secret = os.environ['OWNER_BOT_SECRET']
owner_bot_token = os.environ['OWNER_BOT_TOKEN']
user_bot_secret = os.environ['USER_BOT_SECRET']
user_bot_token = os.environ['USER_BOT_TOKEN']
user_friend_url = os.environ['USER_FRIEND_URL']
bot_endpoint = os.environ['BOT_ENDPOINT']
owner_lineid_list =  json.loads(os.environ['OWNERLINEID'])
wasure_lineid_list =  json.loads(os.environ['WASUREUSERLINEID'])
debug = os.environ['DEBUG']

# setup LINE Messaging API
bot_api_owner = LineBotApi(owner_bot_token)
handler_owner = WebhookHandler(owner_bot_secret)
bot_api_user = LineBotApi(user_bot_token)
handler_user = WebhookHandler(user_bot_secret)

# static_values
OWNER_ID_DUMMY = '12345678'
SHOP_ID_DUMMY = '98765432'

executor = concurrent.futures.ThreadPoolExecutor()

@app.route('/pay', methods=['get'])
def callback_pay():
    transactionId = request.args.get('transactionId')
    print(transactionId)
    data = json.loads(request.args.get('data'))
    print(data)
    ret = pay.confirm(transactionId, data['amount'], data['currency'])
    print(ret)

    ret = l.post_remote_ope_command(data['sid'], data['mno'])
    if data['mode'] == 'start_washing':
        executor.submit(first_wash, data)
        bot_api_user.push_message(data['uid'], TextSendMessage(text='洗濯を開始しました'))
    elif data['mode'] == 'add_dry':
        executor.submit(additional_dry, data)
        bot_api_user.push_message(data['uid'], TextSendMessage(text='追加乾燥を開始しました'))
    print(ret)

    return render_template('jump.html', title='Aqua LINE Pay', message='支払い完了', friend_url=user_friend_url)
    # return '支払い完了'

@app.route("/user", methods=['POST'])
def callback_user():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    #app.logger.info("Request body: " + body)

    body_dict = json.loads(body)
    print(body_dict)

    # handle VERIFY
    if(len(body_dict.get('events')) == 2):
        if(body_dict["events"][0].get('replyToken') == "00000000000000000000000000000000"):
            if(body_dict["events"][1].get('replyToken') == "ffffffffffffffffffffffffffffffff"):
                #app.logger.info("VERIFY code received")
                return 'OK'

    # handle webhook body
    try:
        handler_user.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@app.route("/owner", methods=['POST'])
def callback_owner():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    #app.logger.info("Request body: " + body)

    body_dict = json.loads(body)
    print(body_dict)

    # handle VERIFY
    if(len(body_dict.get('events')) == 2):
        if(body_dict["events"][0].get('replyToken') == "00000000000000000000000000000000"):
            if(body_dict["events"][1].get('replyToken') == "ffffffffffffffffffffffffffffffff"):
                #app.logger.info("VERIFY code received")
                return 'OK'

    # handle webhook body
    try:
        handler_owner.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

##################
# usesr function #
##################

@handler_user.default()
def default_user(event):
    print(event)

@handler_user.add(FollowEvent)
def handle_follow_event_user(event):
    rich_menu_list = bot_api_user.get_rich_menu_list()
    bot_api_user.link_rich_menu_to_user(event.source.user_id, rich_menu_list[0].rich_menu_id)

@handler_user.add(MessageEvent, message=LocationMessage)
def handle_location_user(event):
    # print(event)
    latitude = event.message.latitude
    longitude = event.message.longitude

    print(latitude, longitude)

    reply_msgs = []
    reply_msgs.append(TextMessage(text='その場所から、一番近い店舗の場所は以下の場所です。'))

    # 店の位置
    shop = l.get_shopinfo_from_coordinate(latitude, longitude)

    # print(shop)
    oid = shop['oid']
    sid = shop['sid']

    reply_msgs.append(LocationSendMessage(
        title = shop['name'],
        address = shop['address'],
        latitude = shop['latitude'],
        longitude = shop['longitude']))

    # 店の外観
    image = l.get_shopimage(oid, sid)
    fname = 'static/temp/{}_shop_outer.jpg'.format(sid)
    with open(fname, "wb") as f:
        f.write(base64.b64decode(image))

    image_url = bot_endpoint + '/' + fname
    print(image_url)

    reply_msgs.append(ImageSendMessage(
        original_content_url = image_url,
        preview_image_url = image_url))

    # 空き状況
    st_list = l.get_operatingstatus(oid, sid)
    print(st_list)

    status_str = '洗濯機の稼働状況は\n'
    for st in st_list:
        status_str += '{}号機({})： {}\n'.format(st['mno'], st['name'], st['state'])
    status_str = status_str[:-1]
    reply_msgs.append(TextMessage(text=status_str))

    bot_api_user.reply_message(event.reply_token, reply_msgs)


def save_content_user(message_id, filename):
    message_content = bot_api_user.get_message_content(message_id)
    with open(filename, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)

def gen_machine_select_msg(oid, sid, msg, mode, data={}):
    mno_list = l.get_machineinfo(oid, sid)

    actions=[[]]
    for mno in mno_list:
        if len(actions[-1]) == 3:
            actions.append([])
        data.update({'mode': mode,
            'mno': mno, 'oid': oid, 'sid': sid})
        actions[-1].append(PostbackAction(
            label='{}号機'.format(mno),
            data=json.dumps(data)))

    columns=[]
    for a in actions:
        columns.append(CarouselColumn(
            text=msg,
            actions=a
        ))
    
    msg = TemplateSendMessage(
        alt_text='場所入力', 
        template=CarouselTemplate(columns=columns)
    )
    return msg

@handler_user.add(MessageEvent, message=ImageMessage)
def handle_image_user(event):
    # 画像がユーザから届いたら必ず忘れ物として処理する
    fname = 'static/temp/' + event.message.id + '.jpg'
    save_content_user(event.message.id, fname)
    image_url = bot_endpoint + '/' + fname

    print(image_url)

    oid = OWNER_ID_DUMMY
    sid = SHOP_ID_DUMMY

    reply_msgs = []
    reply_msgs.append(gen_machine_select_msg(oid, sid, 'どこで見つけましたか？', 'lost_items', {'image_url': image_url}))

    bot_api_user.reply_message(event.reply_token, reply_msgs)

@handler_user.add(PostbackEvent)
def handle_postback_user(event):
    print("postback_user", event)

    data = json.loads(event.postback.data)
    print(data)

    mode = data['mode']
    if(mode == 'get_course'):
        # 回す
        oid = data['oid']
        sid = data['sid']
        mno = data['mno']

        print(oid,sid,mno)

        courselist = l.get_course(oid, sid, mno)

        actions = []
        for c in courselist:
            print(c['name'])

            data.update({'mode': 'start_washing', 'amount': c['amount'], 'currency': c['currency']})

            actions.append(PostbackTemplateAction(
                label=c['name'],
                data=json.dumps(data)
            ))

        msg = TemplateSendMessage(
            alt_text='Course Select',
            template=ButtonsTemplate(
                text='コースを選んでください',
                actions=actions,
            )
        )

        bot_api_user.reply_message(event.reply_token, msg)


    elif((mode == 'start_washing') or (mode == 'add_dry')):
        amount = data['amount']
        currency = data['currency']
        mno = data['mno']

        # data['mode'] = 'pay_wash'
        data['uid'] = event.source.user_id

        # LINE Pay
        orderid = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        params='?data={}'.format(json.dumps(data))
        ret = pay.reserve_request(
            '{}号機'.format(mno),
            amount, currency, bot_endpoint+'/pay'+params, orderid)
        print(ret)
        weburl = ret['info']['paymentUrl']['web']
        print(weburl)

        msg = TemplateSendMessage(
            alt_text='LINE Pay',
            template=ButtonsTemplate(
                # thumbnail_image_url='https://scdn.line-apps.com/linepay/partner/images/logo/linepay_logo_238x78_v3.png',
                text='下のボタンを押して支払いを完了してください',
                actions=[
                    URITemplateAction(
                        label='LINE Pay 決済',
                        uri=weburl
                    )
                ]
            )
        )
        bot_api_user.reply_message(event.reply_token, msg)

    elif mode == 'no_dry':
        bot_api_user.reply_message(event.reply_token, TextSendMessage(text = 'ご利用ありがとうございました'))

    elif mode == 'richmenu':
        data = data['data']
        print(data)
        if data == [1, 0]:
            oid = OWNER_ID_DUMMY
            sid = SHOP_ID_DUMMY

            reply_msgs = []
            reply_msgs.append(gen_machine_select_msg(oid, sid, '何号機で洗濯しますか？', 'get_course'))

            bot_api_user.reply_message(event.reply_token,         reply_msgs)
        elif data == [0, 1]:
            bot_api_user.reply_message(event.reply_token, TemplateSendMessage(
                alt_text='upload image',
                template=ButtonsTemplate(
                    # title='Menu',
                    text='忘れ物の画像を送信して下さい',
                    actions=[
                        URIAction(
                            label='カメラを起動する',
                            uri='line://nv/camera/'
                        ),
                        URIAction(
                            label='カメラロールを開く',
                            uri='line://nv/cameraRoll/single'
                        ),
                    ]
                )
            ))
    elif mode == 'lost_items':
        reply_msgs = []
        reply_msgs.append(TextSendMessage(text='ご連絡ありがとうございました。店舗オーナーに連絡しました。'))

        send_msgs = []
        image_url = data['image_url']
        send_msgs.append(ImageSendMessage(
            original_content_url = image_url,
            preview_image_url = image_url))

        oid = '20180183'
        id_list = l.get_memberid(oid)
        id0 = id_list[0]
        id1 = id_list[1]
        confirm_template = ConfirmTemplate(
            text='忘れ物通報：{}号機\n通報者ID:{}\n前回利用者ID:{}\n前回利用者に通知しますか？'.format(data['mno'], id0, id1),
            actions=[
                PostbackTemplateAction(
                    label='Yes',
                    data=json.dumps({'mode': 'lost_item_notify', 'ans': True, 'image_url': image_url, 'id_to': id1})),
                PostbackTemplateAction(
                    label='No',
                    data=json.dumps({'mode': 'lost_item_notify', 'ans': False})),
        ])
        send_msgs.append(TemplateSendMessage(alt_text='忘れ物通知', template=confirm_template))

        bot_api_user.reply_message(event.reply_token, reply_msgs)
        if len(owner_lineid_list):
            bot_api_owner.multicast(owner_lineid_list, send_msgs)
        uid = event.source.user_id
        if not uid in owner_lineid_list:
            try:
                bot_api_owner.push_message(uid, send_msgs)
            except:
                pass

@handler_user.add(BeaconEvent)
def handle_beacon_user(event):
    print(event)

    oid = OWNER_ID_DUMMY
    sid = SHOP_ID_DUMMY
    shopname = l.get_shopname(oid, sid)

    if event.beacon.type == 'enter':

        mes1 = TextSendMessage(text = 'ようこそ 『{}』店へ!!'.format(shopname))
        mes2 = TextSendMessage(text = '『洗濯機が20%長く稼働出来るクーポン』が当たりました！！')
        COUPON_IMG = '/static/text_raijou_present.png'
        image_url = bot_endpoint + COUPON_IMG
        img1 = ImageSendMessage(
            original_content_url = image_url,
            preview_image_url = image_url,
        )
        msgs = [mes1, img1, mes2]
        bot_api_user.reply_message(event.reply_token, msgs)

    elif event.beacon.type == 'leave':
        mes = '『{}』店へのご来店誠にありがとうございました\nまたのご利用を心よりお待ちしております'.format(shopname)
        bot_api_user.reply_message(event.reply_token, TextSendMessage(text = mes))


##################
# owner function #
##################
@handler_owner.default()
def default_owner(event):
    print(event)

@handler_owner.add(FollowEvent)
def handle_follow_event_owner(event):
    rich_menu_list = bot_api_owner.get_rich_menu_list()
    bot_api_owner.link_rich_menu_to_user(event.source.user_id, rich_menu_list[0].rich_menu_id)

def gen_sales_plot(oid, fname):
    ret = l.get_salesdetailsinfo(oid)

    daylysales = {}
    for r in ret:
        daylysales[r['date']] = daylysales.get(r['date'], 0) + r['amount']

    dates = []
    vals = []
    for k, v in daylysales.items():
        y = int(k[0:4])
        m = int(k[5:7])
        d = int(k[8:10])
        dates.append(datetime.datetime(y,m,d))
        vals.append(v)
    print(vals)

    plt.plot(dates, vals)
    plt.xticks(rotation=70)
    plt.grid(True)
    plt.subplots_adjust(bottom=0.2, right=0.95, top=0.95)
    plt.savefig(fname)
    plt.close()

def gen_ope_plot(oid, sid, fname):
    ope_list = l.get_opedetailsinfo_from_shopid(oid, sid)

    mcount = {}
    for o in ope_list:
        mcount[o] = mcount.get(o, 0) + 1

    label = []
    mno = []
    vals = []
    for k in sorted(mcount.keys()):
        mno.append(int(k))
        label.append(k)
        vals.append(mcount[k])

    plt.bar(mno, vals, tick_label=label, align="center")
    plt.savefig(fname)
    plt.close()

@handler_owner.add(PostbackEvent)
def handle_postback_owner(event):
    postback = json.loads(event.postback.data)
    mode = postback.get('mode')
    if mode == 'richmenu':
        data = postback['data']
        print(data)
        if data == [0, 0]:
            oid = OWNER_ID_DUMMY

            reply_msgs=[]
            msg = '売上データを取得してグラフを作成しています。\nOwner ID: {}'.format(oid)
            reply_msgs.append(TextSendMessage(text=msg))
            bot_api_owner.reply_message(event.reply_token, reply_msgs)

            fname = 'static/temp/{}.png'.format(event.reply_token)
            gen_sales_plot(oid, fname)
            image_url = bot_endpoint + '/' + fname
            image_message = ImageSendMessage(
                original_content_url = image_url,
                preview_image_url = image_url
            )
            bot_api_owner.push_message(event.source.user_id, image_message)

        if data == [1, 0]:
            oid = OWNER_ID_DUMMY
            sid = SHOP_ID_DUMMY

            reply_msgs=[]
            msg = '稼働状況データを取得してグラフを作成しています。\nOwner ID: {}\nShop ID: {}'.format(oid, sid)
            reply_msgs.append(TextSendMessage(text=msg))
            bot_api_owner.reply_message(event.reply_token, reply_msgs)

            fname = 'static/temp/{}.png'.format(event.reply_token)
            gen_ope_plot(oid, sid, fname)
            image_url = bot_endpoint + '/' + fname
            image_message = ImageSendMessage(
                original_content_url = image_url,
                preview_image_url = image_url
            )
            bot_api_owner.push_message(event.source.user_id, image_message)

    if mode == 'lost_item_notify':
        reply_msgs=[]
        if(postback['ans']):
            reply_msgs.append(TextSendMessage(text='会員ID:{}に通知しました'.format(postback['id_to'])))

            # 忘れた人に送るメッセージ
            send_msgs=[]
            image_url = postback['image_url']
            send_msgs.append(ImageSendMessage(
                original_content_url = image_url,
                preview_image_url = image_url))
            send_msgs.append(TextSendMessage(text='お店に上記のものをお忘れではありませんか？'))
            if len(wasure_lineid_list):
                bot_api_user.multicast(wasure_lineid_list, send_msgs)
            uid = event.source.user_id
            if not uid in wasure_lineid_list:
                try:
                    bot_api_user.push_message(uid, send_msgs)
                except:
                    pass

        else:
            reply_msgs.append(TextSendMessage(text='通知しません'))
        bot_api_owner.reply_message(event.reply_token, reply_msgs)


        
###################
# common function #
###################
def first_wash(data):
    t0 = datetime.datetime.now()
    uid = data['uid']
    print('start first wash {}'.format(uid))
    while True:
        dt = datetime.datetime.now() - t0
        if(dt.seconds > 10):
            print('finish first wash {}'.format(uid))
            data.update({'mode': 'add_dry', 'amount': 100, 'currency': 'JPY'})

            msgs = [
                TemplateSendMessage(
                    alt_text='追加乾燥確認',
                    template=ConfirmTemplate(
                        text='洗濯乾燥が終了しましたが乾燥が不十分のようです\n追加で乾燥させますか？',
                        actions=[
                            PostbackTemplateAction(
                                label='はい',
                                data=json.dumps(data)
                            ),
                            PostbackTemplateAction(
                                label='いいえ',
                                data=json.dumps({'mode': 'no_dry'})
                            ),
                        ]
                    )
                ),
            ]
            bot_api_user.push_message(uid, msgs)
            return

def additional_dry(data):
    t0 = datetime.datetime.now()
    uid = data['uid']
    print('start second wash {}'.format(uid))
    while True:
        dt = datetime.datetime.now() - t0
        if(dt.seconds > 10):
            print('finish second wash {}'.format(uid))
            bot_api_user.push_message(uid, TextSendMessage(text = '洗濯乾燥が終了しました\nご利用ありがとうございました'))
            return


if __name__ == "__main__":
    app.run(debug=debug, port=5000)
