#!/bin/bash

# 激活环境
source ~/pyenv/feishu_gpt/bin/activate

# 关闭已有的
pid=$(ps -aux | grep "python3 app.py" | grep -v grep | awk '{print $2}')
if [ $pid ];then
    kill -9 $pid
fi

# 重新后台启动
cd ~/app/feishu_gpt
nohup python3 app.py &