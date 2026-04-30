"""
WebSocket 事件处理器
- 处理连接/断线
- 处理房间加入/离开
- 处理编辑锁获取/释放/续期
- 实时广播协作状态变化
"""
from flask import request, session
from flask_jwt_extended import decode_token
from app.collab_manager import (
    join_room,
    leave_room,
    get_room_users,
    broadcast_payload,
    remove_user_all_rooms,
)
from app.models.collaboration import ContractEditLock


def register_socket_events(socketio):
    """注册所有Socket.IO事件"""

    @socketio.on('connect')
    def handle_connect():
        # 验证JWT token（从query参数或headers传递）
        token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return False  # 拒绝无token的连接

        try:
            from flask import current_app
            decoded = decode_token(token, current_app.config['JWT_SECRET_KEY'], ['HS256'])
            request.user_id = decoded['sub']
        except Exception:
            return False

        return True

    @socketio.on('disconnect')
    def handle_disconnect():
        sid = request.sid
        user_id = getattr(request, 'user_id', None)

        # 清理所有房间中的用户
        if user_id:
            # 释放该用户持有的所有锁
            locks = ContractEditLock.query.filter_by(user_id=user_id, is_active=True).all()
            for lock in locks:
                lock.is_active = False
                from app.extensions import db
                db.session.commit()
                
                # 广播锁释放通知给房间内其他用户
                payload = {
                    'type': 'lock_released',
                    'contract_id': lock.contract_id,
                    'released_by_id': user_id,
                    'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
                }
                socketio.emit('collab_event', payload, room=f'contract_{lock.contract_id}', skip_sid=sid)

        # 从所有房间移除
        remove_user_all_rooms(sid)
        
        # 更新各房间的在线状态
        _update_rooms_for_sid(socketio, sid, None)

    @socketio.on('join_contract')
    def handle_join_contract(data):
        """用户进入合同详情页，加入对应房间"""
        contract_id = data.get('contract_id')
        token = data.get('token')
        session_id = data.get('session_id', request.sid)
        user_name = data.get('user_name', '未知用户')

        if not contract_id or not token:
            return {'success': False, 'message': '缺少必要参数'}

        try:
            from flask import current_app
            decoded = decode_token(token, current_app.config['JWT_SECRET_KEY'], ['HS256'])
            user_id = decoded['sub']
            request.user_id = user_id
        except Exception as e:
            return {'success': False, 'message': '认证失败'}

        room = f'contract_{contract_id}'
        
        # 加入Socket.IO房间
        from flask_socketio import join_room as sio_join
        sio_join(room)

        # 注册到协作管理器
        join_room(contract_id, request.sid, {
            'user_id': user_id,
            'user_name': user_name,
            'session_id': session_id,
        })

        # 获取当前房间状态并返回
        users = get_room_users(contract_id)
        lock_info = ContractEditLock.get_lock_info(contract_id)

        # 通知房间内其他用户有新人加入
        emit_payload = {
            'type': 'user_joined',
            'contract_id': contract_id,
            'user': {'user_id': user_id, 'user_name': user_name},
            'online_count': len(users),
            'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
        }
        socketio.emit('collab_event', emit_payload, room=room, skip_sid=request.sid)

        return {
            'success': True,
            'room': room,
            'online_users': users,
            'online_count': len(users),
            'edit_lock': lock_info,
        }

    @socketio.on('leave_contract')
    def handle_leave_contract(data):
        """用户离开合同页面"""
        contract_id = data.get('contract_id')

        if not contract_id:
            return {'success': False}

        room = f'contract_{contract_id}'
        leave_room(contract_id, request.sid)

        from flask_socketio import leave_room as sio_leave
        sio_leave(room)

        # 如果该用户持有锁，释放它
        user_id = getattr(request, 'user_id', None)
        if user_id:
            lock = ContractEditLock.query.filter_by(
                contract_id=contract_id, user_id=user_id, is_active=True
            ).first()
            if lock:
                lock.is_active = False
                from app.extensions import db
                db.session.commit()

        # 广播离开事件
        users = get_room_users(contract_id)
        emit_payload = {
            'type': 'user_left',
            'contract_id': contract_id,
            'user_id': user_id,
            'online_count': len(users),
            'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
        }
        socketio.emit('collab_event', emit_payload, room=room)

        return {'success': True}

    @socketio.on('acquire_lock')
    def handle_acquire_lock(data):
        """尝试获取编辑锁"""
        contract_id = data.get('contract_id')
        session_id = data.get('session_id', request.sid)
        user_id = getattr(request, 'user_id', None)
        user_name = data.get('user_name', '未知用户')

        if not contract_id or not user_id:
            return {'success': False, 'message': '缺少参数'}

        lock_data, error_code = ContractEditLock.acquire_lock(
            contract_id, user_id, user_name, session_id
        )

        if error_code is not None:
            # 锁被占用
            room = f'contract_{contract_id}'
            socketio.emit('collab_event', {
                'type': 'lock_acquired_by_other',
                'contract_id': contract_id,
                **lock_data,
                'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
            }, room=room, skip_sid=request.sid)

            return {'success': False, 'error_code': error_code, **lock_data}

        # 锁获取成功，广播通知
        room = f'contract_{contract_id}'
        socketio.emit('collab_event', {
            'type': 'lock_acquired',
            'contract_id': contract_id,
            'locked_by': user_name,
            'locked_by_id': user_id,
            **lock_data,
            'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
        }, room=room)

        return {'success': True, 'lock': lock_data}

    @socketio.on('release_lock')
    def handle_release_lock(data):
        """释放编辑锁"""
        contract_id = data.get('contract_id')
        session_id = data.get('session_id', request.sid)
        user_id = getattr(request, 'user_id', None)

        if not contract_id or not user_id:
            return {'success': False}

        success, message = ContractEditLock.release_lock(contract_id, user_id, session_id)
        
        if success:
            room = f'contract_{contract_id}'
            socketio.emit('collab_event', {
                'type': 'lock_released',
                'contract_id': contract_id,
                'released_by_id': user_id,
                'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
            }, room=room)

        return {'success': success, 'message': message}

    @socketio.on('heartbeat')
    def handle_heartbeat(data):
        """心跳保活 + 续期锁"""
        contract_ids = data.get('contract_ids', [])
        session_id = data.get('session_id', request.sid)
        user_id = getattr(request, 'user_id', None)

        results = {}
        for cid in contract_ids:
            # 续期锁
            lock_data, err = ContractEditLock.renew_lock(cid, user_id, session_id) if user_id else (None, None)
            results[str(cid)] = {
                'lock_renewed': err is None,
                'lock': lock_data,
            }

        return {'success': True, 'results': results}

    @socketio.on('typing_indicator')
    def handle_typing(data):
        """正在输入指示器"""
        contract_id = data.get('contract_id')
        user_id = getattr(request, 'user_id', None)
        user_name = data.get('user_name', '未知用户')
        field = data.get('field', '')

        if not contract_id:
            return

        room = f'contract_{contract_id}'
        socketio.emit('collab_event', {
            'type': 'user_typing',
            'contract_id': contract_id,
            'user_id': user_id,
            'user_name': user_name,
            'field': field,
            'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
        }, room=room, skip_sid=request.sid)


def _update_rooms_for_sid(socketio, sid, exclude_contract_id):
    """辅助函数：更新sid所在的所有房间的在线状态"""
    pass  # 状态已在broadcast_payload中统一管理
