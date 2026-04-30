import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


class Config:
    # === 基础配置 ===
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret-key')
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', f"sqlite:///{BASE_DIR / 'contract_system.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    UPLOAD_DIR = os.getenv('UPLOAD_DIR', str(BASE_DIR / 'uploads'))
    CORS_ORIGINS = [item.strip() for item in os.getenv('CORS_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173').split(',') if item.strip()]
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024

    # === 协作编辑配置 ===
    COLLAB_EDIT_LOCK_TIMEOUT = int(os.getenv('COLLAB_EDIT_LOCK_TIMEOUT', '300'))  # 锁超时5分钟
    COLLAB_HEARTBEAT_INTERVAL = int(os.getenv('COLLAB_HEARTBEAT_INTERVAL', '15'))  # 心跳间隔15秒
    COLLAB_MAX_ONLINE_USERS = int(os.getenv('COLLAB_MAX_ONLINE_USERS', '100'))  # 最大同时在线人数

    # === 生产环境配置（通过环境变量覆盖） ===
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', '7999'))
