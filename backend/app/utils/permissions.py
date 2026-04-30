from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask import jsonify
from app.models.user import User


def get_current_user():
    user_id = get_jwt_identity()
    if not user_id:
        return None
    return User.query.get(int(user_id))



def require_permissions(*codes):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = get_current_user()
            if not user:
                return jsonify({'message': '用户不存在'}), 401
            user_codes = set(user.permission_codes)
            missing = [code for code in codes if code not in user_codes]
            if missing:
                return jsonify({'message': '权限不足', 'missing_permissions': missing}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
