from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_socketio import SocketIO

db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()
socketio = SocketIO(async_mode='threading', cors_allowed_origins='*', ping_timeout=30, ping_interval=15)
