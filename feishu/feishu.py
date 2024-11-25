import json
import os
import time

import requests
from requests_toolbelt import MultipartEncoder

from utils_file.parser_paper import parse_paper
from utils_file.utils import log_error, log_info

REPLY_URL = 'https://open.feishu.cn/open-apis/im/v1/messages/{}/reply'
TOKEN_URL = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
DOWNLOAD_URL = 'https://open.feishu.cn/open-apis/im/v1/messages/{}/resources/{}?type=file'
UPLOAD_IMAGE_URL = 'https://open.feishu.cn/open-apis/im/v1/images'


class FeiShu:
    def __init__(self, app_data):
        # 密钥信息
        self.app_data = app_data
        # tenant_token
        self.tenant_token = ''

    # 接收消息解析（包含文本内容和PDF文件的解析）
    def __msg_parse(self, message):
        msg = ''
        msg_type = ''
        msg_id = message['message_id']
        status = True
        # 不支持文本和pdf文件以外的消息
        msg_content = json.loads(message['content'])
        # print("msg_content", msg_content)
        if message['message_type'] == 'text':
            msg_type = 'text'
            # 消息内容
            msg = msg_content['text']
            # 群里@的消息进一步处理
            mentions = message.get('mentions', [])
            for mention in mentions:
                msg = msg.replace(mention['key'], '')
            msg = msg.strip()
        elif message['message_type'] == 'file' and msg_content['file_name'].endswith('.pdf'):
            # 如果是pdf文件，下载并解析内容
            msg_type = 'pdf'
            time_str = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            download_path = "./static_file/" + time_str + '_' + msg_content['file_name']
            ret = self.__download_file(message['message_id'], msg_content['file_key'], download_path)
            if not ret or not os.path.exists(download_path):
                log_error(f"[MSG] file {download_path} download error")
                status = False
                msg = "文件接收失败"
            else:
                log_info("start parser pdf")
                msg = parse_paper(download_path, msg_content['file_name'][0:msg_content['file_name'].rfind('.')])
        return status, msg_type, msg_id, msg

    def __tenant_refresh(self):
        tenant_data = {'app_id': self.app_data['app_id'], 'app_secret': self.app_data['app_secret']}
        log_info('[TENANT] token expired, renewing..., post ' + TOKEN_URL + ' with data ' + str(tenant_data))
        with requests.post(TOKEN_URL, data=tenant_data) as r:
            if r.status_code == 200:
                self.tenant_token = r.json()['tenant_access_token']
                log_info('[TENANT] token expired, renew success, post ' + TOKEN_URL + ' with data ' + str(tenant_data))
            else:
                log_error('[TENANT] token expired, renew error, post ' + TOKEN_URL + ' with data ' + str(tenant_data) + ' result is ' + str(r.json()))

    # 接收文件消息
    def __download_file(self, msg_id, file_key, download_path, again=False):
        url = DOWNLOAD_URL.format(msg_id, file_key)
        headers = {
            'Authorization': 'Bearer ' + self.tenant_token,
        }
        log_info("[FILE] download file msg:" + msg_id + " file_key:" + file_key + " download_path:" + download_path)
        with requests.get(url, headers=headers) as r:
            if r.status_code == 200:
                with open(download_path, "wb") as code:
                    code.write(r.content)
                    log_info(f"[FILE] file {download_path} download success")
                    return True
            else:
                log_info(f"[FILE] file {download_path} download failed, again={str(again)}")

        # token失效或过期，重新获取
        if again:
            return False
        else:
            self.__tenant_refresh()
            return self.__download_file(msg_id, file_key, download_path, True)

    # 回复图片消息
    def upload_image(self, image_path, again=False):
        url = UPLOAD_IMAGE_URL
        headers = {
            'Authorization': 'Bearer ' + self.tenant_token,
        }
        form = {
            'image_type': 'message',
            'image': (open(image_path, 'rb'))
        }
        multi_form = MultipartEncoder(form)
        headers['Content-Type'] = multi_form.content_type

        log_info("[IMAGE] post " + url + " -> " + str(image_path))
        with requests.post(url, data=multi_form, headers=headers) as r:
            content = json.loads(r.content.decode("utf-8"))
            if r.status_code == 200:
                # 文件上传成功
                log_info("[IMAGE] post " + url + " with " + str(image_path) + ' return -> ' + str(content))
                return content['data']['image_key']
            else:
                log_error('[IMAGE] post error result -> ' + str(content))
        # 重新发送消息
        if not again:
            # token失效或过期，重新获取
            self.__tenant_refresh()
            return self.upload_image(image_path, True)
        else:
            log_error('[IMAGE] image upload failed twice')
            return ''

    # 接收并解析消息
    def recv_msg(self, event):
        # print("event", event)
        chat_id = event['message']['chat_id']
        send_id = event['sender']['sender_id']['user_id']
        session_id = str(chat_id) + '-' + str(send_id)
        # print("recv_msg")
        status, msg_type, msg_id, msg = self.__msg_parse(event['message'])
        return status, msg_type, msg_id, msg, session_id

    def reply_msg(self, msg_id, msg, msg_type='text', again=False):
        url = REPLY_URL.format(msg_id)
        headers = {
            'Authorization': 'Bearer ' + self.tenant_token,
        }
        if msg_type == 'text':
            data = {
                'content': json.dumps({'text': msg}),
                'msg_type': 'text',
            }
        elif msg_type == 'image':
            # 先做图像上传
            msg = self.upload_image(msg)
            if msg == '':
                log_error(f"[MSG] [{msg_id}] image msg reply error")
                return 400
            # 图像上传成功，封装消息体
            data = {
                'content': json.dumps({'image_key': msg}),
                'msg_type': 'image',
            }
        else:
            log_error(f"[MSG] [{msg_id}] msg type {msg_type} unknown")
            data = {
                'content': json.dumps({'text': '未知的消息类型 ： ' + msg_type}),
                'msg_type': 'text',
            }
        log_info(f"[MSG] [{msg_id}] post msg " + url + " -> " + str(data))
        with requests.post(url, data, headers=headers) as r:
            if r.status_code == 200:
                log_info(f"[MSG] [{msg_id}] post msg " + url + " -> " + str(data) + " success")
                return 200
            else:
                content = json.loads(r.content.decode("utf-8"))
                log_error(f'[MSG] [{msg_id}] post msg error result -> ' + str(content))

        # 重新发送消息
        if not again:
            # token失效或过期，重新获取
            self.__tenant_refresh()
            return self.reply_msg(msg_id, msg, msg_type, True)
        else:
            log_error(f"[MSG] [{msg_id}] post msg failed twice")
            return 400
