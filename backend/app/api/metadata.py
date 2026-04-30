from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.models.user import User, Role, Department
from app.models.contract import Company
from app.utils.permissions import require_permissions


meta_bp = Blueprint('meta', __name__, url_prefix='/api/meta')


@meta_bp.get('/roles')
@jwt_required()
def list_roles():
    return jsonify([item.to_dict() for item in Role.query.order_by(Role.id.asc()).all()])


@meta_bp.get('/users')
@jwt_required()
def list_users():
    users = User.query.order_by(User.id.asc()).all()
    return jsonify([{'id': u.id, 'real_name': u.real_name, 'username': u.username} for u in users])


@meta_bp.get('/departments')
@jwt_required()
def list_departments():
    rows = Department.query.order_by(Department.id.asc()).all()
    return jsonify([{'id': d.id, 'name': d.name} for d in rows])


@meta_bp.get('/companies')
@jwt_required()
def list_companies():
    rows = Company.query.order_by(Company.id.asc()).all()
    return jsonify([item.to_dict() for item in rows])


@meta_bp.post('/companies')
@require_permissions('company:create')
def create_company():
    from flask import request
    data = request.get_json() or {}
    company = Company(
        name=(data.get('name') or '').strip(),
        credit_code=(data.get('credit_code') or '').strip() or None,
        address=(data.get('address') or '').strip() or None,
        contact_person=(data.get('contact_person') or '').strip() or None,
        contact_phone=(data.get('contact_phone') or '').strip() or None,
    )
    if not company.name:
        return jsonify({'message': '单位名称不能为空'}), 400
    if Company.query.filter_by(name=company.name).first():
        return jsonify({'message': '单位已存在'}), 400
    from app.extensions import db
    db.session.add(company)
    db.session.commit()
    return jsonify(company.to_dict()), 201
