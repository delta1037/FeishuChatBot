
import openai
from pprint import pformat
from utils_file.utils import log_info, log_error, config


class DianGptApi:
    def __init__(self):
        self.url = config['dian_gpt_url']

    # 对话生成接口
    def chat_gen(self, prompt, system=None, history=None, model_type='DianGPT-1.0', max_tokens=config['max_chars']):
        gpt_result = {
            'answer': '',
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'status': False,
            'error_msg': ''
        }
        messages = []
        if system is not None and system != '':
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
        try:
            completion = openai.ChatCompletion.create(
                api_key="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                api_base='http://xxx.xxx.xxx.xxx:xxxx/v1/chat/completions',
                model="diangpt",
                messages=messages,
                temperature=0.6,
                # seed=42,
                # repetition_penalty=0.8,
            )
            gpt_result['answer'] = completion.choices[0].message.content
            gpt_result['completion_tokens'] = completion['usage']['completion_tokens']
            gpt_result['prompt_tokens'] = completion['usage']['prompt_tokens']
            gpt_result['status'] = True
            log_info("[DianGPT] " + str(messages) + " -> " + str(completion))
        except openai.error.RateLimitError:
            gpt_result['answer'] = '手速太快了，休息一下吧 😴 '
        except Exception as e:
            log_error("[DianGPT] " + str(pformat(e)))
            gpt_result['answer'] = 'DianGPT 出错了，原因在这里 👉🏻 ' + str(pformat(e))
        return gpt_result
