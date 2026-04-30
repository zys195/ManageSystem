"""
协作会话管理器
- 管理WebSocket连接和房间（每个合同一个房间）
- 支持最多100人同时在线
- 线程安全的状态管理
"""
import threading
from datetime import datetime
from collections import defaultdict

# 全局单例，存储所有房间的在线用户
# 结构: {contract_id: {session_id: user_info}}
_rooms = defaultdict(dict)
_lock = threading.Lock()


def join_room(contract_id: int, session_id: str, user_info: dict):
    """用户加入合同房间"""
    with _lock:
        _rooms[contract_id][session_id] = {
            **user_info,
            'joined_at': datetime.utcnow().isoformat(),
        }


def leave_room(contract_id: int, session_id: str):
    """用户离开合同房间"""
    with _lock:
        if contract_id in _rooms:
            _rooms[contract_id].pop(session_id, None)
            if not _rooms[contract_id]:
                del _rooms[contract_id]


def get_room_users(contract_id: int) -> list:
    """获取房间内所有在线用户"""
    with _lock:
        users = _rooms.get(contract_id, {})
        return [
            {'session_id': sid, **info}
            for sid, info in users.items()
        ]


def get_room_count(contract_id: int) -> int:
    """获取房间在线人数"""
    with _lock:
        return len(_rooms.get(contract_id, {}))


def is_user_online(contract_id: int, session_id: str) -> bool:
    """检查用户是否在房间内"""
    with _lock:
        return session_id in _rooms.get(contract_id, {})


def remove_user_all_rooms(session_id: str):
    """从所有房间移除某用户（断线时调用）"""
    with _lock:
        for contract_id in list(_rooms.keys()):
            if session_id in _rooms[contract_id]:
                del _rooms[contract_id][session_id]
                if not _rooms[contract_id]:
                    del _rooms[contract_id]


def broadcast_payload(contract_id: int) -> dict:
    """生成广播载荷"""
    users = get_room_users(contract_id)
    from app.models.collaboration import ContractEditLock
    lock_info = ContractEditLock.get_lock_info(contract_id)
    return {
        'type': 'presence_update',
        'contract_id': contract_id,
        'online_users': users,
        'online_count': len(users),
        'edit_lock': lock_info,
        'timestamp': datetime.utcnow().isoformat(),
    }
