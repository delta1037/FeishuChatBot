import time
import requests
import openai
from pprint import pformat

from utils_file.utils import log_info, log_error, config

# openai.proxy = config['openai_proxy']


class OpenGptApi:
    def __init__(self):
        # chat gpt key
        self.keys = config['openai_api_keys']
        self.key_idx = 0

    # 对话生成接口
    def chat_gen(self, prompt, system=None, history=None):
        result_template = {
            'answer': '',
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'status': False,
            'error_msg': ''
        }
        return self.__open_ai_chat_gen(gpt_result=result_template, prompt=prompt, system=system, history=history)

    # 图像生成接口
    def image_gen(self, prompt, ai_type='open_ai'):
        result_template = {
            'url': '',
            'path': '',
            'status': False,
            'error_msg': ''
        }
        if ai_type == 'open_ai':
            return self.__open_ai_image_gen(gpt_result=result_template, prompt=prompt)
        else:
            result_template['error_msg'] = 'image gen unknown ai type: ' + ai_type

    # openai的对话生成接口
    def __open_ai_chat_gen(self, gpt_result, prompt, system=None, history=None):
        # 调用 ChatGPT 接口
        messages = []
        if system is not None:
            messages.append(
                {'role': 'system', 'content': system}
            )
        if history is not None:
            for item in history:
                messages.append(
                    {'role': 'user', 'content': item[0]}
                )
                messages.append(
                    {'role': 'assistant', 'content': item[1]}
                )
        messages.append({'role': 'user', 'content': prompt})
        if len(self.keys) == 0:
            gpt_result['error_msg'] = 'chat gpt key is None'
            return gpt_result
        try:
            completion = openai.ChatCompletion.create(
                api_key=self.keys[self.key_idx],
                model="gpt-3.5-turbo",
                messages=messages,
            )
            self.key_idx = (self.key_idx + 1) % len(self.keys)
            gpt_result['answer'] = completion.choices[0].message.content
            gpt_result['completion_tokens'] = completion['usage']['completion_tokens']
            gpt_result['prompt_tokens'] = completion['usage']['prompt_tokens']
            gpt_result['status'] = True
            log_info("[OpenAI] " + str(messages) + " -> " + str(completion))
        except openai.error.RateLimitError as e:
            log_error("[OpenAI] " + str(pformat(e)))
            gpt_result['answer'] = '手速太快了，休息一下吧 😴 '
        except Exception as e:
            log_error("[OpenAI] " + str(pformat(e)))
            gpt_result['answer'] = 'OpenAI 出错了，原因在这里 👉🏻 ' + str(pformat(e))
        return gpt_result

    # openai的图像生成接口
    def __open_ai_image_gen(self, gpt_result, prompt):
        if len(self.keys) == 0:
            gpt_result['error_msg'] = 'chat gpt key is None'
            return gpt_result
        try:
            response = openai.Image.create(
                api_key=self.keys[self.key_idx],
                prompt=prompt,
                n=1,
                size="512x512"
            )
            self.key_idx = (self.key_idx + 1) % len(self.keys)
            log_info("[OpenAI] " + str(prompt) + " -> " + str(response))
            gpt_result['url'] = response['data'][0]['url']
            with requests.get(gpt_result['url']) as r:
                if r.status_code != 200:
                    log_error('[OpenAI] image download failed')
                    return gpt_result
                gpt_result['status'] = True
                time_str = time.strftime("%Y%m%d_%H%M%S", time.localtime())
                http_url = gpt_result['url'][0:gpt_result['url'].find('?')]
                filename = http_url[http_url.rfind('/') + 1:]
                download_path = "./static_image/" + time_str + '_' + filename
                with open(download_path, "wb") as fd:
                    fd.write(r.content)
                    log_info("[OpenAI] image download success")
                gpt_result['path'] = download_path
        except openai.error.RateLimitError:
            gpt_result['error_msg'] = '手速太快了，休息一下吧 😴 '
        except Exception as e:
            log_error("[OpenAI] " + str(pformat(e)))
            gpt_result['error_msg'] = 'OpenAI 出错了，原因在这里 👉🏻 ' + str(pformat(e))
        return gpt_result
