from app import create_app
from app.config import Config

app, socketio = create_app()


if __name__ == '__main__':
    # 必须用 socketio.run() 而非 flask run，否则 WebSocket 会报
    # "AssertionError: write() before start_response" 和 ECONNRESET
    socketio.run(app, host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, allow_unsafe_werkzeug=True)


@app.cli.command('run')
def run_dev():
    """开发服务器（支持 WebSocket）"""
    socketio.run(app, host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, allow_unsafe_werkzeug=True)


@app.cli.command('run-socketio')
def run_socketio():
    """使用 SocketIO 服务器启动（支持 WebSocket）"""
    socketio.run(app, host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, allow_unsafe_werkzeug=True)
