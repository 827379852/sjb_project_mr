"""
Vercel Serverless 入口
"""
import sys
import os

# 添加 backend 目录到 Python 路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app

# Vercel 需要这个 handler
handler = app