"""数据库初始化脚本 - 创建所有表结构 + 初始化示例数据"""
from app import create_app
from app.extensions import db

app, _ = create_app()

with app.app_context():
    # 1. 创建表
    db.create_all()
    print('✅ 所有表创建完成！')

    # 列出已创建的表
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f'📋 已创建 {len(tables)} 张表: {", ".join(tables)}')

    # 2. 初始化种子数据（与 flask seed 相同逻辑）
    from datetime import datetime
    from pathlib import Path
    from app.models.user import User, Role, Permission, Department
    from app.models.contract import Company, Contract

    Path(app.config['UPLOAD_DIR']).mkdir(parents=True, exist_ok=True)

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
        pm_user = User.query.filter_by(username='pm1').first()
        sales_user = User.query.filter_by(username='sales1').first()
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
        db.session.flush()

    db.session.commit()

    # ========== 协同项目种子数据 ==========
    from app.models.collaboration import Project, ProjectMember, Task
    admin_user = User.query.filter_by(username='admin').first()
    pm_user = User.query.filter_by(username='pm1').first()
    sales_user = User.query.filter_by(username='sales1').first()
    
    # 示例项目 1: 合同管理平台一期
    project1 = Project.query.filter_by(code='PRJ-2026-001').first()
    if not project1:
        project1 = Project(
            name='合同管理平台一期',
            code='PRJ-2026-001',
            description='企业级合同管理系统的设计与开发，包含合同全生命周期管理功能',
            status='active',
            priority='high',
            start_date=datetime(2026, 3, 1),
            end_date=datetime(2026, 7, 31),
            created_by=admin_user.id if admin_user else None,
        )
        db.session.add(project1)
        db.session.flush()

        # 项目成员
        members_data = [
            (admin_user, 'owner'),
            (pm_user, 'manager'),
            (sales_user, 'member'),
        ]
        for user, role in members_data:
            if user and not ProjectMember.query.filter_by(project_id=project1.id, user_id=user.id).first():
                member = ProjectMember(project_id=project1.id, user_id=user.id, role=role)
                db.session.add(member)

        # 项目任务示例
        tasks_data = [
            ('需求分析与设计', '完成系统需求调研和详细设计文档', 'done', pm_user),
            ('数据库设计', '设计完整的数据库表结构和ER图', 'done', pm_user),
            ('后端API开发', '实现合同CRUD、权限控制等核心接口', 'in_progress', pm_user),
            ('前端界面开发', '基于Vue3开发响应式前端界面', 'todo', sales_user),
            ('多人协同模块', '实现实时编辑锁、评论、通知等功能', 'todo', pm_user),
            ('系统集成测试', '完成全功能测试和性能优化', 'todo', None),
            ('用户培训文档', '编写操作手册和培训材料', 'todo', sales_user),
        ]
        for title, desc, status, assignee in tasks_data:
            task = Task(
                project_id=project1.id,
                title=title,
                description=desc,
                status=status,
                priority='high' in [title] and 'high' or 'medium',
                assignee_id=assignee.id if assignee else None,
                created_by=admin_user.id if admin_user else None,
            )
            db.session.add(task)

    # 示例项目 2: 移动端APP开发
    project2 = Project.query.filter_by(code='PRJ-2026-002').first()
    if not project2:
        project2 = Project(
            name='移动端APP开发项目',
            code='PRJ-2026-002',
            description='配套移动端应用，支持合同审批、文件查看、消息通知等功能',
            status='planning',
            priority='medium',
            start_date=datetime(2026, 5, 1),
            end_date=datetime(2026, 9, 30),
            created_by=sales_user.id if sales_user else None,
        )
        db.session.add(project2)
        db.session.flush()

        for user, role in [(sales_user, 'owner'), (pm_user, 'manager')]:
            if user and not ProjectMember.query.filter_by(project_id=project2.id, user_id=user.id).first():
                db.session.add(ProjectMember(project_id=project2.id, user_id=user.id, role=role))

    db.session.commit()

    print('✅ 种子数据初始化完成！')
    print('管理员账号：admin / Admin123!')
    print('财务账号：finance1 / Finance123!')
    print('项目账号：pm1 / Project123!')
    print('销售账号：sales1 / Sales123!')
