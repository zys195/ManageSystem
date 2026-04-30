"""
协作编辑锁 REST API
- 获取/释放/查询编辑锁
- 查询合同在线用户
- 支持HTTP方式的锁管理（作为WebSocket的补充）
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.utils.permissions import get_current_user
from app.models.collaboration import ContractEditLock

collab_bp = Blueprint('collaboration', __name__, url_prefix='/api')


@collab_bp.post('/contracts/<int:contract_id>/lock')
@jwt_required()
def acquire_edit_lock(contract_id):
    """获取合同编辑锁（HTTP方式）"""
    user = get_current_user()
    data = request.get_json() or {}
    session_id = data.get('session_id', f'http_{user.id}')
    timeout = int(request.args.get('timeout', 300))

    lock_data, error_code = ContractEditLock.acquire_lock(
        contract_id, user.id, user.real_name or user.username, session_id, timeout
    )

    if error_code is not None:
        return jsonify(lock_data), error_code

    return jsonify({'success': True, 'lock': lock_data})


@collab_bp.delete('/contracts/<int:contract_id>/lock')
@jwt_required()
def release_edit_lock(contract_id):
    """释放合同编辑锁（HTTP方式）"""
    user = get_current_user()
    data = request.get_json() or {}
    session_id = data.get('session_id', f'http_{user.id}')

    success, message = ContractEditLock.release_lock(contract_id, user.id, session_id)
    if not success:
        return jsonify({'message': message}), 400

    return jsonify({'message': message})


@collab_bp.get('/contracts/<int:contract_id>/lock')
@jwt_required()
def get_lock_status(contract_id):
    """获取合同当前锁状态"""
    lock_info = ContractEditLock.get_lock_info(contract_id)
    return jsonify({
        'lock': lock_info,
        'is_locked': lock_info is not None,
    })


@collab_bp.post('/contracts/<int:contract_id>/lock/heartbeat')
@jwt_required()
def heartbeat_lock(contract_id):
    """心跳续期编辑锁"""
    user = get_current_user()
    data = request.get_json() or {}
    session_id = data.get('session_id', f'http_{user.id}')
    timeout = int(request.args.get('timeout', 300))

    lock_data, error = ContractEditLock.renew_lock(contract_id, user.id, session_id, timeout)

    if error is not None:
        return jsonify(lock_data), error

    return jsonify({'success': True, 'lock': lock_data})


@collab_bp.get('/contracts/<int:contract_id>/online-users')
@jwt_required()
def get_online_users(contract_id):
    """获取合同的在线用户信息"""
    info = ContractEditLock.get_contract_online_users(contract_id)
    return jsonify(info)
