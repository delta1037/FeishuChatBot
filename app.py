import json
from time import sleep
from queue import Queue
from pprint import pformat
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, abort

from gpt_api import open_ai_api, close_ai_api, dian_ai_api, deep_seek_api
from feishu.feishu import FeiShu
from utils_file.utils import log_info, log_error, config, DEFAULT_MODEL_TYPE, DEFAULT_MODEL_TOKENS_BIAS
from utils_file.db_ctrl import ChatMSgDb, ChatEventDb, ChatRoleDb, ChatPaper, ChatImage, ChatModelDb

# 注册错误处理，收集日志
# from werkzeug.exceptions import HTTPException

# 普通用户帮助信息
HELP_MESSAGE = '/help\n\t🆘获取帮助信息'
HELP_MESSAGE += '\n/clear\n\t🗑️清除上下文'
HELP_MESSAGE += '\n/sel_role\n\t👀查看当前角色和可选角色'
HELP_MESSAGE += '\n/set_role\n\t👥设置角色: 格式/set_role#[role_name]'
HELP_MESSAGE += '\n/sel_model\n\t👀查看当前模型和可选模型'
HELP_MESSAGE += '\n/set_model\n\t👍设置模型: 格式/set_model#[model_name]'

# 管理员用户帮助信息
ADMIN_HELP_MESSAGE = '\n/admin#help\n\t🆘Admin获取帮助信息'
ADMIN_HELP_MESSAGE += '\n/admin#clear\n\t🗑️清除所有会话'
ADMIN_HELP_MESSAGE += '\n/admin#sel_role\n\t👀查看角色: 格式/admin#sel_role'
ADMIN_HELP_MESSAGE += '\n/admin#set_role\n\t👥设置角色: 格式/admin#set_role#[role_name]#[description]#[ai_tip]'
ADMIN_HELP_MESSAGE += '\n/admin#alt_role\n\t⛏修改角色: 格式/admin#alt_role#[role_name]#[description]#[ai_tip]'
ADMIN_HELP_MESSAGE += '\n/admin#del_role\n\t❌删除角色: 格式/admin#del_role#[role_name]'
ADMIN_HELP_MESSAGE += '\n/admin#sel_model\n\t👀查看模型: 格式/admin#sel_model'
ADMIN_HELP_MESSAGE += '\n/admin#set_model\n\t👍设置模型: 格式/admin#set_model#[model_name]#[description]#[max_tokens]#[max_usage_counts]'
ADMIN_HELP_MESSAGE += '\n/admin#alt_model\n\t⛏修改模型: 格式/admin#alt_model#[model_name]#[description]#[max_tokens]#[max_usage_counts]'
ADMIN_HELP_MESSAGE += '\n/admin#del_model\n\t❌删除模型: 格式/admin#del_model#[model_name]'

app = Flask(__name__)

pool = ThreadPoolExecutor(max_workers=3)

msg_queue = Queue()
msg_queue_lock = Lock()

db_msg = ChatMSgDb()
db_event = ChatEventDb()
db_role = ChatRoleDb()
db_model = ChatModelDb()
db_paper = ChatPaper()
db_image = ChatImage()

BOT_NUMS = 3
PROCESSORS = {}


def chat_bot():
    log_info("[BOT] bot thread start")
    while True:
        with msg_queue_lock:
            # log_info("chat bot: ", msg_queue.empty(), api_key)
            if msg_queue.empty():
                sleep(1)
                continue
            # 获取消息
            message = msg_queue.get()
        log_info("[BOT] get a msg from queue -> " + str(message))

        app_id = message['header']['app_id']
        # print("app id", app_id)
        if app_id not in PROCESSORS:
            log_error(f"[BOT] app id {app_id} is unknown")
        processor: FeiShu = PROCESSORS[app_id]
        # print(processor)
        status, msg_type, msg_id, msg, session_id = processor.recv_msg(message['event'])

        log_info("[BOT] status: " + str(status))
        log_info("[BOT] session_id: " + session_id)
        log_info("[BOT] msg_type: " + msg_type)
        log_info("[BOT] msg_id: " + msg_id)
        log_info("[BOT] msg: " + msg)

        # 过滤消息
        if not status:
            log_error(f"[BOT] [{msg_id}] parser msg failed")
            processor.reply_msg(msg_id, '❌' + msg)
            continue
        if msg == "":
            log_error(f"[BOT] [{msg_id}] invalid msg")
            processor.reply_msg(msg_id, '❌不支持的消息类型')
            continue
        if '@_all' in msg:
            log_info(f"[BOT] [{msg_id}] invalid at all")
            continue
        # 斜杠开头的按命令处理
        if msg[0] == '/':
            if msg.startswith('/admin#clear'):
                log_info(f"[BOT] [{msg_id}] admin clean all data")
                db_msg.del_all(app_id)
                processor.reply_msg(msg_id, '✅已清除所有会话')
                continue
            if msg.startswith('/admin#set_role#'):
                log_info(f"[BOT] [{msg_id}] admin set role " + msg)
                msg_list = msg.split('#')
                if len(msg_list) < 5:
                    processor.reply_msg(msg_id, '❌设置角色格式错误')
                else:
                    status, error_msg = db_role.type_add(role_name=msg_list[2], description=msg_list[3],
                                                         ai_system=msg_list[4])
                    if status:
                        processor.reply_msg(msg_id, '✅成功添加角色')
                    else:
                        processor.reply_msg(msg_id, '❌' + error_msg)
                continue
            if msg.startswith('/admin#alt_role#'):
                log_info(f"[BOT] [{msg_id}] admin alt role " + msg)
                msg_list = msg.split('#')
                if len(msg_list) < 5:
                    processor.reply_msg(msg_id, '❌修改角色格式错误')
                else:
                    status, error_msg = db_role.type_update(role_name=msg_list[2], description=msg_list[3],
                                                            ai_system=msg_list[4])
                    if status:
                        processor.reply_msg(msg_id, '✅成功修改角色')
                    else:
                        processor.reply_msg(msg_id, '❌' + error_msg)
                continue
            if msg.startswith('/admin#del_role#'):
                log_info(f"[BOT] [{msg_id}] admin del role " + msg)
                msg_list = msg.split('#')
                if len(msg_list) < 3:
                    processor.reply_msg(msg_id, '❌清除角色格式错误')
                else:
                    db_role.type_del_by(role_name=msg_list[2])
                    processor.reply_msg(msg_id, '✅成功删除角色')
                continue
            if msg.startswith('/admin#sel_role'):
                log_info(f"[BOT] [{msg_id}] admin sel role " + msg)
                msg_reply = "可选的角色有:\n" + "{:>10} -> {} -> {}".format("name", "description", "ai_tip")
                all_roles = db_role.type_sel()
                for line in all_roles:
                    msg_reply += '\n' + "{:>10} -> {} -> {}".format(line[0], line[1], line[2])
                processor.reply_msg(msg_id, msg_reply)
                continue
            if msg.startswith('/admin#set_model#'):
                log_info(f"[BOT] [{msg_id}] admin set model " + msg)
                msg_list = msg.split('#')
                if len(msg_list) < 6:
                    processor.reply_msg(msg_id, '❌设置模型格式错误')
                else:
                    status, error_msg = db_model.type_add(model_name=msg_list[2], description=msg_list[3],
                                                          max_token=msg_list[4], max_count=msg_list[5])
                    if status:
                        processor.reply_msg(msg_id, '✅成功添加模型')
                    else:
                        processor.reply_msg(msg_id, '❌' + error_msg)
                continue
            if msg.startswith('/admin#alt_model#'):
                log_info(f"[BOT] [{msg_id}] admin alt model " + msg)
                msg_list = msg.split('#')
                if len(msg_list) < 6:
                    processor.reply_msg(msg_id, '❌修改模型格式错误')
                else:
                    status, error_msg = db_model.type_update(model_name=msg_list[2], description=msg_list[3],
                                                             max_token=msg_list[4], max_count=msg_list[5])
                    if status:
                        processor.reply_msg(msg_id, '✅成功修改模型')
                    else:
                        processor.reply_msg(msg_id, '❌' + error_msg)
                continue
            if msg.startswith('/admin#del_model#'):
                log_info(f"[BOT] [{msg_id}] admin del model " + msg)
                msg_list = msg.split('#')
                if len(msg_list) < 3:
                    processor.reply_msg(msg_id, '❌清除模型格式错误')
                else:
                    db_model.type_del_by(model_name=msg_list[2])
                    processor.reply_msg(msg_id, '✅成功删除模型')
                continue
            if msg.startswith('/admin#sel_model'):
                log_info(f"[BOT] [{msg_id}] admin sel model " + msg)
                msg_reply = "可选的模型有:\n" + "%20s -> %s -> %s -> %s" % (
                "name", "description", "max_token", "max_count")
                all_models = db_model.type_sel()
                for line in all_models:
                    msg_reply += '\n' + "%20s -> %s -> %s -> %s" % (line[0], line[1], line[2], line[3])
                processor.reply_msg(msg_id, msg_reply)
                continue
            if msg.startswith('/admin#help'):
                log_info(f"[BOT] [{msg_id}] admin return help")
                processor.reply_msg(msg_id, ADMIN_HELP_MESSAGE)
                continue
            if msg.startswith('/clear'):
                log_info(f"[BOT] [{msg_id}] clean user data")
                db_msg.del_by_sid(app_id, session_id)
                processor.reply_msg(msg_id, '✅上下文已清除')
                continue
            if msg.startswith('/sel_role'):
                log_info(f"[BOT] [{msg_id}] sel user role")
                role_sel = db_role.role_sel(app_id, session_id)
                msg_reply = "您当前的角色是: " \
                            + role_sel[0][0] + "\n\n可选的角色有:\n" + "{:>10} -> {}".format("name", "description")
                all_roles = db_role.type_sel()
                for line in all_roles:
                    msg_reply += '\n' + "{:>10} -> {}".format(line[0], line[1])
                processor.reply_msg(msg_id, msg_reply)
                continue
            if msg.startswith('/set_role'):
                log_info(f"[BOT] [{msg_id}] set user role")
                msg_list = msg.split('#')
                if len(msg_list) < 2:
                    processor.reply_msg(msg_id, '❌角色设置格式错误')
                else:
                    log_info(f"[BOT] [{msg_id}] set user role " + msg_list[1])
                    status, error_msg = db_role.role_add(app_id, session_id, msg_list[1])
                    if status:
                        db_msg.del_by_sid(app_id, session_id)
                        processor.reply_msg(msg_id, '✅成功设置角色并自动清空上下文')
                    else:
                        processor.reply_msg(msg_id, '❌' + error_msg)
                continue
            if msg.startswith('/sel_model'):
                log_info(f"[BOT] [{msg_id}] sel user model")
                model_sel_ret = db_model.model_sel(app_id, session_id)
                if not model_sel_ret["model_sel_limit"]:
                    msg_reply = "您当前的模型是: " + str(model_sel_ret["model_sel"]) + "，" \
                                + "使用次数 " + str(model_sel_ret["model_req_count"]) + " \n\n " \
                                + "可选的模型有:\n" + "%20s -> %s -> %s" % ("name", "description", "max_count")
                else:
                    msg_reply = "您当前的模型是: " + str(model_sel_ret["model_req"]) + "，" \
                                + "使用次数 " + str(model_sel_ret["model_req_count"]) + ", " \
                                + "超过当天最大使用量 " + str(model_sel_ret["model_req_max_count"]) + "，" \
                                + "正在使用默认的 " + str(model_sel_ret["model_sel"]) + " 模型\n\n " \
                                + "可选的模型有:\n" + "%20s -> %s -> %s" % ("name", "description", "max_count")
                all_models = db_model.type_sel()
                for line in all_models:
                    msg_reply += '\n' + "%20s -> %s -> %s" % (line[0], line[1], line[3])
                processor.reply_msg(msg_id, msg_reply)
                continue
            if msg.startswith('/set_model'):
                log_info(f"[BOT] [{msg_id}] set user model")
                msg_list = msg.split('#')
                if len(msg_list) < 2:
                    processor.reply_msg(msg_id, '❌模型设置格式错误')
                else:
                    log_info(f"[BOT] [{msg_id}] set user model " + msg_list[1])
                    status, error_msg = db_model.model_set(app_id, session_id, msg_list[1])
                    if status:
                        db_msg.del_by_sid(app_id, session_id)
                        processor.reply_msg(msg_id, '✅成功设置模型并自动清空上下文')
                    else:
                        processor.reply_msg(msg_id, '❌' + error_msg)
                continue
            if msg.startswith('/help'):
                log_info(f"[BOT] [{msg_id}] return help")
                db_msg.del_by_sid(app_id, session_id)
                processor.reply_msg(msg_id, HELP_MESSAGE)
                continue
            processor.reply_msg(msg_id, '❌' + "未知的命令类型" + '\n' + HELP_MESSAGE)
            continue
        try:
            # 调用openai前清理一下消息
            log_info(f"[BOT] [{msg_id}] clean chat id")
            db_msg.reduce(app_id, session_id, DEFAULT_MODEL_TOKENS_BIAS)

            # 调用open_ai
            log_info(f"[BOT] [{msg_id}] call open ai")
            role_sel = db_role.role_sel(app_id, session_id)
            if len(role_sel) == 0 or role_sel[0][0] == "default" or "test" in role_sel[0][0]:
                system_info = ""
            else:
                system_info = role_sel[0][2]
            if msg_type == 'pdf' and 'paper_' not in role_sel[0][0]:
                # 文件类型消息，但是非paper类的角色
                processor.reply_msg(msg_id, '❌' + "没有选择处理论文的角色，您当前角色是: " + role_sel[0][0])
                continue
            if msg_type == 'pdf' or 'paper_' in role_sel[0][0]:
                # 总结文件时，自动清空上下文，防止token过多
                log_info(f"[BOT] [{msg_id}] paper_summary, auto clean msg")
                db_msg.del_by_sid(app_id, session_id)
            if msg_type == 'pdf':
                processor.reply_msg(msg_id, "PDF文件解析内容:\n" + msg)
            if 'image_' in role_sel[0][0]:
                image_result = open_ai_api.image_gen(prompt=msg)
                if not image_result['status']:
                    log_error(f"[BOT] [{msg_id}] return with error msg " + image_result['error_msg'])
                    processor.reply_msg(msg_id, image_result['error_msg'] + "\n使用说明:\n" + HELP_MESSAGE)
                    continue
                # 文件返回成功，返回图片消息
                log_info(f"[BOT] [{msg_id}] return image " + image_result['path'])
                db_image.add(app_id, session_id, msg, image_result['path'])
                processor.reply_msg(msg_id, image_result['path'], msg_type='image')
            else:
                model_sel_ret = db_model.model_sel(app_id, session_id, count_usage=True)
                model_type = model_sel_ret["model_sel"]
                max_tokens = model_sel_ret["model_sel_tokens"]
                ret_prefix = ""
                if model_sel_ret["model_sel_limit"]:
                    model_req = model_sel_ret["model_req"]
                    ret_prefix = f"❌ 今日模型 {model_req} 调用次数已达上限, 自动切换为默认模型 {model_type} \n\n"

                if "gpt-4" in model_type:
                    # gpt 4 禁止使用history和关闭系统提示
                    system_info = None
                    history = None
                else:
                    history = db_msg.sel_by_sid(app_id, session_id)
                if model_type.startswith("DianGPT"):
                    log_info(f"[BOT] [{msg_id}] use dian ai chat api")
                    gpt_result = dian_ai_api.chat_gen(
                        prompt=msg,
                        system=system_info,
                        history=history,
                        model_type=model_type,
                        max_tokens=int(max_tokens)
                    )
                elif model_type.startswith("deepseek-"):
                    log_info(f"[BOT] [{msg_id}] use deepseek ai chat api")
                    gpt_result = deep_seek_api.chat_gen(
                        prompt=msg,
                        system=system_info,
                        history=history,
                        model_type=model_type,
                        max_tokens=int(max_tokens)
                    )
                else:
                    log_info(f"[BOT] [{msg_id}] use close ai chat api")
                    gpt_result = close_ai_api.chat_gen(
                        prompt=msg,
                        system=system_info,
                        history=history,
                        model_type=model_type,
                        max_tokens=int(max_tokens)
                    )
                # 归档消息记录
                if msg_type == 'text' and 'paper_' not in role_sel[0][0]:
                    log_info(f"[BOT] [{msg_id}] archive msg")
                    db_msg.add(app_id,
                               session_id,
                               model_type,
                               msg, gpt_result['answer'],
                               gpt_result['completion_tokens'],
                               gpt_result['prompt_tokens'])
                else:
                    # 论文数据额外归档，要不然太大了
                    log_info(f"[BOT] [{msg_id}] archive paper")
                    db_paper.add(app_id,
                                 session_id,
                                 model_type,
                                 msg, gpt_result['answer'],
                                 gpt_result['completion_tokens'],
                                 gpt_result['prompt_tokens'])
                # 返回消息
                log_info(f"[BOT] [{msg_id}] return answer")
                if gpt_result['status']:
                    processor.reply_msg(msg_id, ret_prefix + gpt_result['answer'])
                else:
                    processor.reply_msg(msg_id, ret_prefix + gpt_result['answer'] + "\n使用说明:\n" + HELP_MESSAGE)
        except Exception as e:
            print(e)
            log_error(f"[BOT] [{msg_id}] " + str(pformat(e)))
            processor.reply_msg(msg_id, 'BOT 出错了，原因 👉🏻 ' + str(pformat(e)) + "\n\n使用说明:\n" + HELP_MESSAGE)


@app.route('/api', methods=['POST'])
def api():
    request_data = request.get_json()
    print(request_data)
    # challenge认证
    if "challenge" in request_data:
        log_info("[APP] do challenge")
        return jsonify({'challenge': request_data["challenge"]})
    # 基本内容校验
    if 'header' not in request_data or 'event' not in request_data:
        log_info("[APP] error conn")
        abort(403)
    # 头信息认证
    headers = request_data['header']
    app_id = headers.get('app_id')
    if app_id not in config['apps']:
        log_info("[APP] app not found")
        abort(403)
    app_data = config['apps'][app_id]
    if headers.get('token') != app_data['verification_token']:
        log_info("[APP] verification failed")
        abort(403)
    # 检查消息是否重复发送
    event_id = request_data['header']['event_id']
    event_list = db_event.sel_by_id(app_id, event_id)
    if event_list is not None and len(event_list) > 0:
        log_error(f"[APP] msg repeat, event={event_id}")
        return jsonify({}), 200
    log_info(f"[APP] recv msg , event={event_id}")
    db_event.add_by_id(app_id, event_id, json.dumps(request_data))

    # 把所有的消息丢给线程处理
    log_info(f"[APP] put msg to queue, event={event_id}")
    msg_queue.put(request_data)
    return jsonify({}), 200


# @app.errorhandler(HTTPException)
# def handle_exception(e):
#     """Return JSON instead of HTML for HTTP errors."""
#     # start with the correct headers and status code from the error
#     # 获取request中的关键字段，并写入到文件中

#     response = e.get_response()
#     # replace the body with JSON
#     response.data = json.dumps({
#         "code": 200,
#         "name": "o oh ~",
#         "description": "scan me as you scan, used for parper data",
#     })
#     response.content_type = "application/json"
#     return response

if __name__ == '__main__':
    # 初始化消息处理器
    for s_app_id in config['apps']:
        if config['apps'][s_app_id]['type'] == 'feishu':
            log_info("[APP] init app id:" + s_app_id)
            PROCESSORS[s_app_id] = FeiShu(config['apps'][s_app_id])
        else:
            log_error("[APP] unknown app type:" + config['apps'][s_app_id]['type'])
    for idx in range(BOT_NUMS):
        log_info(f"[APP] start chat bot at idx {idx}")
        pool.submit(chat_bot)
    app.run(host='0.0.0.0', port=7777, debug=False)
