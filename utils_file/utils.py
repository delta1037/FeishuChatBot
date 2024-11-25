import time

config = {
    "apps": {
        "cli_123456789": {
            "type": "feishu",
            "app_id": "cli_123456789",
            "app_secret": "xxxxxxxxxxxxx",
            "verification_token": "xxxxxxxxxxx",
        }
    },
    "openai_api_keys": [
        "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    ],
    "closeai_api_keys": [
        "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    ],
    "deep_seek_api_keys": [
        "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    ],
    "openai_proxy": "127.0.0.1:8080",
    "dian_gpt_url": "127.0.0.1:6006/v1/chat/completions",
    "max_chars": 2048,
    "db_path": "chatgpt.db",
    "gpt4_mpd": 10
}

DEFAULT_MODEL_TYPE = 'deepseek-chat'
DEFAULT_MODEL_MAX_TOKENS = 2048
# 默认的最大上下文长度
DEFAULT_MODEL_TOKENS_BIAS = 2048


def log_error(msg: str):
    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open('error.log', 'a') as f:
        f.write(time_str + ' ' + msg)
        f.write("\n")
        print(msg)


def log_info(msg: str):
    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open('info.log', 'a') as f:
        f.write(time_str + ' ' + msg)
        f.write("\n")
        print(msg)
