from pathlib import Path
from flask import Flask, jsonify
from sqlalchemy import inspect, text

from app.config import Config
from app.extensions import db, jwt, cors, socketio
from app.models import User, Role, Permission, Department, Company, Contract, StandaloneInvoice
from app.api.auth import auth_bp
from app.api.metadata import meta_bp
from app.api.contracts import contract_bp
from app.api.collaboration import collab_bp



def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    Path(app.config['UPLOAD_DIR']).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})
    socketio.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(meta_bp)
    app.register_blueprint(contract_bp)
    app.register_blueprint(collab_bp)

    with app.app_context():
        inspector = inspect(db.engine)
        if inspector.has_table('contracts'):
            columns = {column['name'] for column in inspector.get_columns('contracts')}
            if 'owner_name' not in columns:
                db.session.execute(text('ALTER TABLE contracts ADD COLUMN owner_name VARCHAR(128)'))
                db.session.commit()
        if inspector.has_table('contract_invoices'):
            columns = {column['name'] for column in inspector.get_columns('contract_invoices')}
            invoice_columns = {
                'company_name': 'VARCHAR(255)',
                'company_address': 'VARCHAR(255)',
                'company_phone': 'VARCHAR(64)',
                'bank_account': 'VARCHAR(128)',
                'bank_name': 'VARCHAR(255)',
                'tax_no': 'VARCHAR(128)',
            }
            for column_name, column_type in invoice_columns.items():
                if column_name not in columns:
                    db.session.execute(text(f'ALTER TABLE contract_invoices ADD COLUMN {column_name} {column_type}'))
            db.session.commit()
        if not inspector.has_table('standalone_invoices'):
            StandaloneInvoice.__table__.create(db.engine)

    @app.get('/api/health')
    def health():
        return jsonify({'message': 'ok'})

    @app.errorhandler(ValueError)
    def handle_value_error(err):
        db.session.rollback()
        return jsonify({'message': str(err)}), 400

    @app.errorhandler(Exception)
    def handle_unexpected_error(err):
        from werkzeug.exceptions import HTTPException
        if isinstance(err, HTTPException):
            return err
        db.session.rollback()
        return jsonify({'message': '服务器内部错误', 'detail': str(err)}), 500

    @app.cli.command('init-db')
    def init_db_command():
        db.create_all()
        print('数据库表已创建。')

    @app.cli.command('seed')
    def seed_command():
        db.create_all()

        # Departments
        sales = Department.query.filter_by(name='销售部').first() or Department(name='销售部')
        finance = Department.query.filter_by(name='财务部').first() or Department(name='财务部')
        project = Department.query.filter_by(name='项目部').first() or Department(name='项目部')
        admin_dept = Department.query.filter_by(name='综合管理部').first() or Department(name='综合管理部')
        db.session.add_all([sales, finance, project, admin_dept])
        db.session.flush()

        permission_map = {
            'contract:create': ('新增合同', 'contract'),
            'contract:update': ('编辑合同', 'contract'),
            'contract:delete': ('删除合同', 'contract'),
            'contract:view': ('查看合同', 'contract'),
            'invoice:create': ('新增开票', 'finance'),
            'receipt:create': ('新增收款', 'finance'),
            'payment:create': ('新增付款', 'finance'),
            'acceptance:create': ('新增验收', 'acceptance'),
            'file:upload': ('上传文件', 'file'),
            'file:download': ('下载文件', 'file'),
            'file:delete': ('删除文件', 'file'),
            'audit:view': ('查看审计日志', 'audit'),
            'company:create': ('新增单位', 'company'),
        }

        permissions = {}
        for code, (name, module) in permission_map.items():
            row = Permission.query.filter_by(code=code).first()
            if not row:
                row = Permission(code=code, name=name, module=module)
                db.session.add(row)
            permissions[code] = row
        db.session.flush()

        role_defs = {
            'admin': ('系统管理员', list(permission_map.keys())),
            'finance': ('财务人员', ['contract:view', 'invoice:create', 'receipt:create', 'payment:create', 'file:download']),
            'project_manager': ('项目经理', ['contract:view', 'contract:update', 'acceptance:create', 'file:upload', 'file:download']),
            'sales': ('销售人员', ['contract:view', 'contract:create', 'contract:update', 'file:upload', 'file:download', 'company:create']),
            'viewer': ('只读用户', ['contract:view', 'file:download']),
        }

        role_rows = {}
        for code, (name, permission_codes) in role_defs.items():
            role = Role.query.filter_by(code=code).first()
            if not role:
                role = Role(code=code, name=name)
                db.session.add(role)
            db.session.flush()
            role.permissions = [permissions[item] for item in permission_codes]
            role_rows[code] = role

        users = [
            ('admin', 'Admin123!', '系统管理员', admin_dept, ['admin']),
            ('finance1', 'Finance123!', '财务测试账号', finance, ['finance']),
            ('pm1', 'Project123!', '项目经理测试账号', project, ['project_manager']),
            ('sales1', 'Sales123!', '销售测试账号', sales, ['sales']),
        ]
        for username, password, real_name, dept, role_codes in users:
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username, real_name=real_name, department=dept, status='active')
                user.set_password(password)
                db.session.add(user)
                db.session.flush()
            user.roles = [role_rows[item] for item in role_codes]

        company_a = Company.query.filter_by(name='甲方示例科技有限公司').first()
        if not company_a:
            company_a = Company(name='甲方示例科技有限公司', contact_person='张总', contact_phone='13800000001')
            db.session.add(company_a)
        company_b = Company.query.filter_by(name='乙方示例服务有限公司').first()
        if not company_b:
            company_b = Company(name='乙方示例服务有限公司', contact_person='李经理', contact_phone='13800000002')
            db.session.add(company_b)
        db.session.flush()

        if not Contract.query.filter_by(contract_no='HT-2026-0001').first():
            admin_user = User.query.filter_by(username='admin').first()
            sample_contract = Contract(
                serial_no='20260001',
                contract_no='HT-2026-0001',
                contract_name='合同管理系统实施合同',
                project_name='合同管理平台一期',
                contract_type='software',
                party_a_company_id=company_a.id,
                party_b_company_id=company_b.id,
                owner_user_id=admin_user.id if admin_user else None,
                department_id=admin_dept.name,
                contract_amount=98000,
                processing_status='executing',
                quotation_status='completed',
                approval_status='approved',
                archive_status='unarchived',
                created_by=admin_user.id if admin_user else None,
                updated_by=admin_user.id if admin_user else None,
            )
            db.session.add(sample_contract)

        db.session.commit()
        print('初始化数据完成。')
        print('管理员账号：admin / Admin123!')
        print('财务账号：finance1 / Finance123!')
        print('项目账号：pm1 / Project123!')
        print('销售账号：sales1 / Sales123!')

    # 注册 SocketIO 事件处理器
    from app.socket_events import register_socket_events
    register_socket_events(socketio)

    return app, socketio
