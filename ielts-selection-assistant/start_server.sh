#!/bin/bash
# 一键启动本地雅思图片静态服务器 (端口 8777)
cd "$(dirname "$0")"
python3 serve_images.py 8777
