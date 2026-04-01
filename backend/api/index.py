"""
Vercel Serverless 入口
"""
from app.main import app

# Vercel 需要这个 handler
handler = app