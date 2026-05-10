from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_socketio import SocketIO
import os

db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()
socketio_async_mode = os.getenv(
    'SOCKETIO_ASYNC_MODE',
    'eventlet' if os.getenv('FLASK_ENV') == 'production' else 'threading',
)
socketio = SocketIO(async_mode=socketio_async_mode, cors_allowed_origins='*', ping_timeout=30, ping_interval=15)