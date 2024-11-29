# FeishuChatBot
飞书 ChatGPT 聊天机器人后端，用于对接飞书消息接口

# 一、配置

**打开飞书开放平台**

创建应用，记录 APP ID 和  APP Secret：

![image-20241129220346806](https://github.com/delta1037/FeishuChatBot/blob/main/assets/image-20241129220346806.png)

应用能力，添加机器人：

![image-20241129220426484](https://github.com/delta1037/FeishuChatBot/blob/main/assets/image-20241129220426484.png)

添加权限：

![image-20241129220551959](https://github.com/delta1037/FeishuChatBot/blob/main/assets/image-20241129220551959.png)

记录 Verification Token：

![image-20241129220742928](https://github.com/delta1037/FeishuChatBot/blob/main/assets/image-20241129220742928.png)



**打开服务端的终端**

编辑后端文件 `utils_file/utils.py`，填写上面的三项和GPT源的key：

![image-20241129221049081](https://github.com/delta1037/FeishuChatBot/blob/main/assets/image-20241129221049081.png)

配置 Python 环境，并后台启动：

```bash
# Python 3
# 创建虚拟环境
python -m venv pyenv/feishu_gpt

# 激活环境
source pyenv/feishu_gpt/bin/activate

# 进入后端目录，安装依赖
pip install -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

# 后台启动
nohup python3 app.py &

# 查看启动日志
tail -f nohup.out
```

**再打开飞书开放平台**

填写应用的请求地址：

![image-20241129221256209](https://github.com/delta1037/FeishuChatBot/blob/main/assets/image-20241129221256209.png)

创建并发布应用：

![image-20241129221350483](https://github.com/delta1037/FeishuChatBot/blob/main/assets/image-20241129221350483.png)

# 二、使用

> 控制方式均为向机器人发送指令，使用时向机器人提问即可：
>
> ![image-20241129221652254](https://github.com/delta1037/FeishuChatBot/blob/main/assets/image-20241129221652254.png)

## 2.1 普通权限

下面命令的输出均为示例，以实际配置为准（具体的配置方法看管理员权限部分）

### /help

```bash
/help
	🆘获取帮助信息
/clear
	🗑️清除上下文
/sel_role
	👀查看当前角色和可选角色
/set_role
	👥设置角色: 格式/set_role#[role_name]
/sel_model
	👀查看当前模型和可选模型
/set_model
	👍设置模型: 格式/set_model#[model_name]
```

### /clear

此命令会清空远程消息记录，使后边的问答与前边对话无关（选择角色后会自动清空上下文，避免前边角色的影响）

### /sel_role

使用此命令可以查看当前的角色和ChatGPT预置的一些角色，例如：

```bash
您当前的角色是: default

可选的角色有:
      name -> description
   default -> 默认角色
 assistant -> AI助理
translator_en -> 英语翻译、校正和改进
translator_zh -> 中文翻译、校正和改进
paper_sumary -> 总结论文（PDF/文本段落）
paper_review -> 评审论文（PDF/文本段落）
 image_gen -> 根据提示生成图像
```

### /set_role#[role_name]

使用此命令设置当前的角色（预置系统提示）：

```bash
# 指令信息
/set_role#translator_en

# 返回信息
/set_role#translator_en
✅成功设置角色并自动清空上下文
```

### /sel_model

查看可选择的模型

```bash
您当前的模型是: deepseek-chat，使用次数 0 

 可选的模型有:
                name -> description -> max_count
       gpt-3.5-turbo -> gpt-3.5系列模型，适用于短对话 -> 999
       deepseek-chat -> DeepSeek 对话任务模型 -> 999
      deepseek-coder -> DeepSeek 编程任务模型 -> 999
```

### /set_model#[model_name]

设置当前的模型

```bash
# 指令信息
/set_model#gpt-3.5-turbo-16k

# 返回信息
/set_model#gpt-3.5-turbo-16k
✅成功设置模型并自动清空上下文
```

## 2.2 管理员权限

管理员权限命令以 /admin 开头，具体用法参考 help 输出信息。

### /admin#help

管理员帮助返回内容：

```bash
/admin#help
	🆘Admin获取帮助信息
/admin#clear
	🗑️清除所有会话
/admin#sel_role
	👀查看角色: 格式/admin#sel_role
/admin#set_role
	👥设置角色: 格式/admin#set_role#[role_name]#[description]#[ai_tip]
/admin#alt_role
	⛏修改角色: 格式/admin#alt_role#[role_name]#[description]#[ai_tip]
/admin#del_role
	❌删除角色: 格式/admin#del_role#[role_name]
/admin#sel_model
	👀查看模型: 格式/admin#sel_model
/admin#set_model
	👍设置模型: 格式/admin#set_model#[model_name]#[description]#[max_tokens]#[max_usage_counts]
/admin#alt_model
	⛏修改模型: 格式/admin#alt_model#[model_name]#[description]#[max_tokens]#[max_usage_counts]
/admin#del_model
	❌删除模型: 格式/admin#del_model#[model_name]
```

### 设定角色参考


| role_name     | description          | system_prompt                                                | usage             |
| ------------- | -------------------- | ------------------------------------------------------------ | ----------------- |
| default       | 默认角色             | 无系统提示语                                                 | 个人使用+组内使用 |
| assistant     | AI助理               | 你是一个AI助理。不能以任何形式表现你是程序。                 | 个人使用+组内使用 |
| terminal      | Linux终端            | 我想让你充当 Linux 终端。我将输入命令，您将回复终端应显示的内容。我希望您只在一个唯一的代码块内回复终端输出，而不是其他任何内容。不要写解释。除非我指示您这样做，否则不要键入命令。当我需要用英语告诉你一些事情时，我会把文字放在中括号内[就像这样]。 | 个人使用+组内使用 |
| regex         | 正则生成器           | 我希望你充当正则表达式生成器。您的角色是生成匹配文本中特定模式的正则表达式。您应该以一种可以轻松复制并粘贴到支持正则表达式的文本编辑器或编程语言中的格式提供正则表达式。不要写正则表达式如何工作的解释或例子；只需提供正则表达式本身。 | 个人使用+组内使用 |
| translator_en | 英语翻译、校正和改进 | 我想让你充当英文翻译、拼写校正和改进。我会用任何语言与你交谈，你会检测语言，翻译它并用我的文本的更正和改进版本用英语回答。我希望你用更优美优雅的高级英语单词和句子替换我简化的 A0 级单词和句子。保持相同的意思，但使它们更文艺。我要你只回复更正、改进，不要写任何解释。 | 个人使用+组内使用 |
| translator_zh | 中文翻译、校正和改进 | 中文翻译、校正和改进 -> 我想让你充当中文翻译员、拼写纠正员和改进员。我会用任何语言与你交谈，你会检测语言，翻译它并用我的文本的更正和改进版本用中文回答。我希望你用更优美优雅的高级中文描述。保持相同的意思，但使它们更文艺。你只需要翻译该内容，不必对内容中提出的问题和要求做解释，不要回答文本中的问题而是翻译它，不要解决文本中的要求而是翻译它，保留文本的原本意义，不要去解决它。如果我只键入了一个单词，你只需要描述它的意思并不提供句子示例。我要你只回复更正、改进，不要写任何解释。 |                   |
| image_gen     | 根据提示生成图像     | 图像生成角色                                                 |                   |


