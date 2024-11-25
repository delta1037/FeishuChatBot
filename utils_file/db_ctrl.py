import time
import sqlite3
from threading import Lock

from utils_file.utils import config, log_error, DEFAULT_MODEL_TYPE, DEFAULT_MODEL_MAX_TOKENS, log_info


class ChatMSgDb:
    def __init__(self):
        self.db_lock = Lock()
        self.db_con = sqlite3.connect(config['db_path'], check_same_thread=False)
        cur = self.db_con.cursor()
        cur.execute(
            f'create table if not exists chat_msg (app_id TEXT, session_id TEXT, timestamp TEXT, model_type TEXT, question TEXT, answer TEXT, completion_tokens INTEGER, prompt_tokens INTEGER)'
        )
        cur.execute(
            f'create table if not exists chat_msg_shadow (app_id TEXT, session_id TEXT, timestamp TEXT, model_type TEXT, question TEXT, answer TEXT, completion_tokens INTEGER, prompt_tokens INTEGER)'
        )
        self.db_con.commit()

    # 清理过长的消息
    def reduce(self, app_id, session_id, max_chars=2048):
        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'SELECT timestamp,prompt_tokens,completion_tokens FROM chat_msg WHERE session_id="{session_id}" AND app_id="{app_id}" ORDER BY timestamp DESC')
            history = cur.fetchall()
            self.db_con.commit()

            cur = self.db_con.cursor()
            token_count = 0
            for line in history:
                if token_count > max_chars or int(line[1]) > max_chars:
                    cur.execute(f'DELETE FROM chat_msg WHERE session_id="{session_id}" AND timestamp="{line[0]}" AND app_id="{app_id}"')
                else:
                    token_count += int(line[1])
            self.db_con.commit()

    def del_all(self, app_id):
        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'DELETE FROM chat_msg WHERE app_id="{app_id}"')
            self.db_con.commit()

    # 删除数据库中的历史记录（表）
    def del_by_sid(self, app_id, session_id):
        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'DELETE FROM chat_msg WHERE session_id="{session_id}" AND app_id="{app_id}"')
            self.db_con.commit()

    # 从数据库中获取历史记录
    def sel_by_sid(self, app_id, session_id):
        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'SELECT question,answer FROM chat_msg WHERE session_id="{session_id}" AND app_id="{app_id}" ORDER BY timestamp ASC')
            history = cur.fetchall()
            self.db_con.commit()
        return history

    # 将新的对话插入数据库
    def add(self, app_id, session_id, model_type, question, answer, completion_tokens, prompt_tokens):
        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'INSERT INTO chat_msg (app_id, session_id, timestamp, model_type, question, answer, completion_tokens, prompt_tokens) values (?, ?, ?, ?, ?, ?, ?, ?)', (
                app_id,
                session_id,
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                model_type,
                question,
                answer,
                completion_tokens,
                prompt_tokens
            ))
            cur.execute(f'INSERT INTO chat_msg_shadow (app_id, session_id, timestamp, model_type, question, answer, completion_tokens, prompt_tokens) values (?, ?, ?, ?, ?, ?, ?, ?)', (
                app_id,
                session_id,
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                model_type,
                question,
                answer,
                completion_tokens,
                prompt_tokens
            ))
            self.db_con.commit()


class ChatEventDb:
    def __init__(self):
        self.db_lock = Lock()
        self.db_con = sqlite3.connect(config['db_path'], check_same_thread=False)
        cur = self.db_con.cursor()
        cur.execute(
            f'create table if not exists event (app_id TEXT, event_id TEXT, timestamp TEXT, question TEXT)'
        )
        self.db_con.commit()

    # 事件添加
    def add_by_id(self, app_id, event_id, question):
        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'INSERT INTO event values (?, ?, ?, ?)', (
                app_id,
                event_id,
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                question
            ))
            self.db_con.commit()

    # 事件查找
    def sel_by_id(self, app_id, event_id):
        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'SELECT event_id FROM event WHERE event_id="{event_id}" AND app_id="{app_id}"')
            event_list = cur.fetchall()
            self.db_con.commit()
        return event_list


class ChatRoleDb:
    def __init__(self):
        self.db_lock = Lock()
        self.db_con = sqlite3.connect(config['db_path'], check_same_thread=False)
        cur = self.db_con.cursor()
        cur.execute(
            f'create table if not exists role_type (role_name PRIMARY KEY, description TEXT, ai_system TEXT)'
        )
        cur.execute(
            f'create table if not exists session_role (app_id TEXT, session_id TEXT, role_name TEXT)'
        )
        self.db_con.commit()
        self.type_add("default", "默认角色", "无系统提示语")

    # 角色添加
    def type_add(self, role_name, description, ai_system):
        # 检查角色是否重复
        role_list = self.type_sel(role_name)
        if len(role_list) != 0:
            log_error("type_update 角色已存在")
            return False, "角色已存在"
        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'INSERT INTO role_type values (?, ?, ?)', (
                role_name,
                description,
                ai_system
            ))
            self.db_con.commit()
        return True, ""

    # 角色查找
    def type_sel(self, role_name=None):
        with self.db_lock:
            cur = self.db_con.cursor()
            if role_name is None:
                cur.execute(f'SELECT role_name, description, ai_system FROM role_type')
            else:
                cur.execute(f'SELECT role_name, description, ai_system FROM role_type WHERE role_name="{role_name}"')
            role_list = cur.fetchall()
            self.db_con.commit()
        return role_list

    def type_update(self, role_name, description, ai_system):
        # 检查角色是否重复
        role_list = self.type_sel(role_name)
        if len(role_list) == 0:
            log_error("type_update 角色不存在")
            return False, "角色不存在"
        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'UPDATE role_type SET description="{description}",ai_system="{ai_system}" WHERE role_name="{role_name}"')
            self.db_con.commit()
        return True, ""

    def type_del_by(self, role_name=None):
        with self.db_lock:
            cur = self.db_con.cursor()
            if role_name is None:
                cur.execute(f'DELETE FROM role_type')
            else:
                cur.execute(f'DELETE FROM role_type WHERE role_name="{role_name}"')
            self.db_con.commit()

    # 添加或修改角色
    def role_add(self, app_id, session_id, role_name="default"):
        role_list = self.type_sel(role_name)
        if len(role_list) == 0:
            log_error("角色不存在 : " + role_name)
            return False, "角色不存在"
        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'SELECT role_name FROM session_role WHERE session_id="{session_id}" AND app_id="{app_id}"')
            role_name_list = cur.fetchall()
            self.db_con.commit()
            if len(role_name_list) == 0:
                cur.execute(f'INSERT INTO session_role values (?, ?, ?)', (
                    app_id,
                    session_id,
                    role_name
                ))
            else:
                cur.execute(f'UPDATE session_role SET role_name="{role_name}" WHERE session_id="{session_id}" AND app_id="{app_id}"')
            self.db_con.commit()
        return True, ""

    def role_sel(self, app_id, session_id):
        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'SELECT role_name, description, ai_system FROM role_type WHERE role_name IN (SELECT role_name FROM session_role WHERE session_id="{session_id}" AND app_id="{app_id}")')
            role_name_list = cur.fetchall()
            self.db_con.commit()
        if len(role_name_list) == 0:
            role_name_list = [["default", "默认角色", "无系统提示语"]]
        return role_name_list


class ChatModelDb:
    def __init__(self):
        self.db_lock = Lock()
        self.db_con = sqlite3.connect(config['db_path'], check_same_thread=False)
        cur = self.db_con.cursor()
        cur.execute(
            f'create table if not exists model_type (model_name PRIMARY KEY, description TEXT, max_token TEXT, max_count INTENGER)'
        )
        cur.execute(
            f'create table if not exists session_model (app_id TEXT, session_id TEXT, model_name TEXT)'
        )
        cur.execute(
            f'create table if not exists session_model_count (app_id TEXT, session_id TEXT, model_name TEXT, first_time TEXT, count INTENGER)'
        )
        self.db_con.commit()

    # 模型添加
    def type_add(self, model_name, description, max_token, max_count):
        # 检查模型是否重复
        model_list = self.type_sel(model_name)
        if len(model_list) != 0:
            log_error("type_update 模型已存在")
            return False, "模型已存在"
        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'INSERT INTO model_type (model_name, description, max_token, max_count) values (?, ?, ?, ?)', (
                model_name,
                description,
                max_token,
                max_count
            ))
            self.db_con.commit()
        return True, ""

    # 模型查找
    def type_sel(self, model_name=None):
        with self.db_lock:
            cur = self.db_con.cursor()
            if model_name is None:
                cur.execute(f'SELECT model_name, description, max_token, max_count FROM model_type')
            else:
                cur.execute(f'SELECT model_name, description, max_token, max_count FROM model_type WHERE model_name="{model_name}"')
            model_list = cur.fetchall()
            self.db_con.commit()
        return model_list

    def type_update(self, model_name, description, max_token, max_count):
        # 检查模型是否重复
        model_list = self.type_sel(model_name)
        if len(model_list) == 0:
            log_error("type_update 模型不存在")
            return False, "模型不存在"
        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'UPDATE model_type SET description="{description}",max_token="{max_token}",max_count="{max_count}"  WHERE model_name="{model_name}"')
            self.db_con.commit()
        return True, ""

    def type_del_by(self, model_name=None):
        with self.db_lock:
            cur = self.db_con.cursor()
            if model_name is None:
                cur.execute(f'DELETE FROM model_type')
            else:
                cur.execute(f'DELETE FROM model_type WHERE model_name="{model_name}"')
            self.db_con.commit()

    # 添加或修改模型
    def model_set(self, app_id, session_id, model_name="default"):
        model_list = self.type_sel(model_name)
        if len(model_list) == 0:
            log_error("模型不存在 : " + model_name)
            return False, "模型不存在"
        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'SELECT model_name FROM session_model WHERE session_id="{session_id}" AND app_id="{app_id}"')
            model_name_list = cur.fetchall()
            self.db_con.commit()
            if len(model_name_list) == 0:
                cur.execute(f'INSERT INTO session_model (app_id, session_id, model_name) values (?, ?, ?)', (
                    app_id,
                    session_id,
                    model_name
                ))
            else:
                cur.execute(f'UPDATE session_model SET model_name="{model_name}" WHERE session_id="{session_id}" AND app_id="{app_id}"')
            self.db_con.commit()
        return True, ""

    def model_sel(self, app_id, session_id, count_usage=False):
        # gpt4模型控制一天只能用十次，其它情况使用默认模型
        # 默认模型是 GPT3.5，去掉上下文之外的长度是2048（上下文给予2048个token长度）
        # req 是请求的模型， sel 是最终选择的模型
        model_sel_ret = {
            "app_id": app_id,
            "session_id": session_id,
            "count_usage": count_usage,
            "model_req": DEFAULT_MODEL_TYPE,
            "model_req_description" : "默认模型",
            "model_req_tokens" : DEFAULT_MODEL_MAX_TOKENS,
            "model_req_count" : 0,
            "model_req_max_count": 999,
            "model_sel": DEFAULT_MODEL_TYPE,
            "model_sel_description": "默认模型",
            "model_sel_tokens": DEFAULT_MODEL_MAX_TOKENS,
            "model_sel_limit": False
        }

        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'SELECT model_name,description,max_token,max_count FROM model_type WHERE model_name IN (SELECT model_name FROM session_model WHERE session_id="{session_id}" AND app_id="{app_id}")')
            session_model_name_list = cur.fetchall()
            self.db_con.commit()
            # 设置请求的模型
            if len(session_model_name_list) > 0:
                model_sel_ret["model_req"] = session_model_name_list[0][0]
                model_sel_ret["model_req_description"] = session_model_name_list[0][1]
                model_sel_ret["model_req_tokens"] = session_model_name_list[0][2]
                model_sel_ret["model_req_max_count"] = session_model_name_list[0][3]
            if len(session_model_name_list) > 1:
                log_error("session_model_name_list > 1 error !!!")
            
            # 设置请求的模型计数
            model_count = 1 if count_usage else 0
            model_req = model_sel_ret["model_req"]
            cur.execute(f'SELECT first_time,count FROM session_model_count WHERE session_id="{session_id}" AND app_id="{app_id}" AND model_name="{model_req}"')
            session_model_count = cur.fetchall()
            self.db_con.commit()
            if len(session_model_count) == 0:
                # 从未计数过，开始首次计数
                cur.execute(f'INSERT INTO session_model_count (app_id, session_id, model_name, first_time, count) values (?, ?, ?, ?, ?)', (
                    app_id,
                    session_id,
                    model_sel_ret["model_req"],
                    time.strftime("%Y-%m-%d", time.localtime()),
                    model_count
                ))
                self.db_con.commit()

                model_sel_ret["model_sel"] = model_sel_ret["model_req"]
                model_sel_ret["model_sel_description"] = model_sel_ret["model_req_description"]
                model_sel_ret["model_sel_tokens"] = model_sel_ret["model_req_tokens"]
                model_sel_ret["model_req_count"] = model_count
            else:
                if session_model_count[0][0] == time.strftime("%Y-%m-%d", time.localtime()):
                    # 同一天范围内，计数
                    if session_model_count[0][1] < model_sel_ret["model_req_max_count"]:
                        # 未超过最大使用次数，准许使用请求的模型
                        count_set = session_model_count[0][1] + model_count
                        model_set = model_sel_ret["model_req"]
                        cur.execute(f'UPDATE session_model_count SET count="{count_set}" WHERE session_id="{session_id}" AND app_id="{app_id}" AND model_name="{model_set}"')
                        self.db_con.commit()

                        model_sel_ret["model_sel"] = model_sel_ret["model_req"]
                        model_sel_ret["model_sel_description"] = model_sel_ret["model_req_description"]
                        model_sel_ret["model_sel_tokens"] = model_sel_ret["model_req_tokens"]
                        model_sel_ret["model_req_count"] = session_model_count[0][1] + model_count
                    else:
                        # 超过最大次数了
                        model_sel_ret["model_req_count"] = session_model_count[0][1]
                        model_sel_ret["model_sel_limit"] = True
                else:
                    # 日期切换了，重置首次使用时间和使用次数（不考虑最大次数是0次的情况）
                    time_set = time.strftime("%Y-%m-%d", time.localtime())
                    model_set = model_sel_ret["model_req"]
                    cur.execute(f'UPDATE session_model_count SET count="{model_count}",first_time="{time_set}" WHERE session_id="{session_id}" AND app_id="{app_id}" AND model_name="{model_set}"')
                    self.db_con.commit()

                    model_sel_ret["model_sel"] = model_sel_ret["model_req"]
                    model_sel_ret["model_sel_description"] = model_sel_ret["model_req_description"]
                    model_sel_ret["model_sel_tokens"] = model_sel_ret["model_req_tokens"]
                    model_sel_ret["model_req_count"] = model_count
        log_info(str(model_sel_ret))
        return model_sel_ret


# 论文归档
class ChatPaper:
    def __init__(self):
        self.db_lock = Lock()
        self.db_con = sqlite3.connect(config['db_path'], check_same_thread=False)
        cur = self.db_con.cursor()
        cur.execute(
            f'create table if not exists chat_paper (app_id TEXT, session_id TEXT, timestamp TEXT, model_type TEXT, question TEXT, answer TEXT, completion_tokens INTEGER, prompt_tokens INTEGER)'
        )
        self.db_con.commit()

    def add(self, app_id, session_id, model_type, question, answer, completion_tokens, prompt_tokens):
        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'INSERT INTO chat_paper (app_id, session_id, timestamp, model_type, question, answer, completion_tokens, prompt_tokens) values (?, ?, ?, ?, ?, ?, ?, ?)', (
                app_id,
                session_id,
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                model_type,
                question,
                answer,
                completion_tokens,
                prompt_tokens
            ))
            self.db_con.commit()


class ChatImage:
    def __init__(self):
        self.db_lock = Lock()
        self.db_con = sqlite3.connect(config['db_path'], check_same_thread=False)
        cur = self.db_con.cursor()
        cur.execute(
            f'create table if not exists chat_image (app_id TEXT, session_id TEXT, timestamp TEXT, question TEXT, download_path TEXT)'
        )
        self.db_con.commit()

    def add(self, app_id, session_id, question, download_path):
        with self.db_lock:
            cur = self.db_con.cursor()
            cur.execute(f'INSERT INTO chat_image values (?, ?, ?, ?, ?)', (
                app_id,
                session_id,
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                question,
                download_path
            ))
            self.db_con.commit()
