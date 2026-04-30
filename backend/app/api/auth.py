from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required

from app.extensions import db
from app.models.user import User
from app.utils.permissions import get_current_user


auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.post('/login')
def login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'message': '用户名或密码错误'}), 401
    if user.status != 'active':
        return jsonify({'message': '用户已禁用'}), 403

    user.last_login_at = datetime.utcnow()
    db.session.commit()

    token = create_access_token(identity=str(user.id), expires_delta=timedelta(hours=8))
    return jsonify({
        'token': token,
        'user': user.to_dict(),
    })


@auth_bp.get('/me')
@jwt_required()
def me():
    user = get_current_user()
    if not user:
        return jsonify({'message': '用户不存在'}), 401
    return jsonify(user.to_dict())


@auth_bp.post('/change-password')
@jwt_required()
def change_password():
    user = get_current_user()
    if not user:
        return jsonify({'message': '用户不存在'}), 401

    data = request.get_json() or {}
    current_password = data.get('current_password') or ''
    new_password = data.get('new_password') or ''

    if not current_password or not new_password:
        return jsonify({'message': '请填写原密码和新密码'}), 400
    if len(new_password) < 6:
        return jsonify({'message': '新密码至少需要 6 位'}), 400
    if not user.check_password(current_password):
        return jsonify({'message': '原密码不正确'}), 400
    if user.check_password(new_password):
        return jsonify({'message': '新密码不能与原密码相同'}), 400

    user.set_password(new_password)
    db.session.commit()
    return jsonify({'message': '密码修改成功'})
