#!/bin/bash
# 一键启动雅思真经划词助手本地服务 (端口 8777)
cd "$(dirname "$0")"
python3 server.py 8777
