import json
from flask import request
from app.extensions import db
from app.models.contract import AuditLog



def log_action(user_id, module, action, resource_type, resource_id, before_data=None, after_data=None):
    log = AuditLog(
        user_id=user_id,
        module=module,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        request_method=request.method if request else None,
        request_path=request.path if request else None,
        request_ip=request.headers.get('X-Forwarded-For', request.remote_addr) if request else None,
        before_data=json.dumps(before_data, ensure_ascii=False) if before_data is not None else None,
        after_data=json.dumps(after_data, ensure_ascii=False) if after_data is not None else None,
    )
    db.session.add(log)
