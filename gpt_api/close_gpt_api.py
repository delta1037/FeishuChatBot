import openai
import tiktoken
from pprint import pformat

from utils_file.utils import log_info, log_error, config


class CloseGptApi:
    @staticmethod
    def num_tokens_from_string(string: str, encoding_name: str) -> int:
        """Returns the number of tokens in a text string."""
        encoding = tiktoken.encoding_for_model(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens

    # 对话生成接口
    @staticmethod
    def chat_gen(prompt, system=None, history=None, model_type='gpt-3.5-turbo', max_tokens=config['max_chars']):
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
            tokens = CloseGptApi.num_tokens_from_string(prompt, model_type)
            if tokens > max_tokens:
                gpt_result['answer'] = '你的输入太长了，我理解不了 😭'
                return gpt_result
            completion = openai.ChatCompletion.create(
                api_key=config['closeai_api_keys'][0],
                api_base='https://api.closeai-proxy.xyz/v1',
                model=model_type,
                messages=messages,
                max_tokens=max_tokens
            )
            gpt_result['answer'] = completion.choices[0].message.content
            gpt_result['completion_tokens'] = completion['usage']['completion_tokens']
            gpt_result['prompt_tokens'] = completion['usage']['prompt_tokens']
            gpt_result['status'] = True
            log_info("[OpenAI] " + str(messages) + " -> " + str(completion))
        except openai.error.RateLimitError:
            gpt_result['answer'] = '手速太快了，休息一下吧 😴 '
        except Exception as e:
            log_error("[OpenAI] " + str(pformat(e)))
            gpt_result['answer'] = 'OpenAI 出错了，原因在这里 👉🏻 ' + str(pformat(e))
        return gpt_result
