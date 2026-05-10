"""生产环境启动脚本 - 使用 eventlet WSGI 服务器（支持 WebSocket）"""
import eventlet
eventlet.monkey_patch()

from app import create_app
from flask_socketio import SocketIO

app, socketio = create_app()

if __name__ == '__main__':
    # eventlet 生产服务器，支持高并发 WebSocket
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
