"""多人协同项目数据库模型"""
from datetime import datetime, timedelta
from app.extensions import db


# ============================================================
# 1. 项目 (Project) - 协同工作的核心实体
# ============================================================
class Project(db.Model):
    """项目表 - 多人协同的主体"""
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    code = db.Column(db.String(64), unique=True, index=True)  # 项目编号
    description = db.Column(db.Text)
    
    # 关联合同 (可选)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'))
    
    # 项目状态: planning, active, paused, completed, archived
    status = db.Column(db.String(32), default='planning', index=True)
    
    # 优先级: low, medium, high, urgent
    priority = db.Column(db.String(16), default='medium')
    
    # 时间范围
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    
    # 项目设置
    is_public = db.Column(db.Boolean, default=False)  # 是否公开可见
    
    # 统计字段 (冗余存储，避免频繁聚合查询)
    task_count = db.Column(db.Integer, default=0)
    completed_task_count = db.Column(db.Integer, default=0)
    member_count = db.Column(db.Integer, default=0)
    
    version = db.Column(db.Integer, default=1)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    creator = db.relationship('User', foreign_keys=[created_by])
    contract = db.relationship('Contract', backref='projects')
    members = db.relationship('ProjectMember', back_populates='project', cascade='all, delete-orphan')
    tasks = db.relationship('Task', back_populates='project', cascade='all, delete-orphan')
    comments = db.relationship('Comment', back_populates='project', cascade='all, delete-orphan')
    activities = db.relationship('ActivityLog', back_populates='project', cascade='all, delete-orphan')
    files = db.relationship('ProjectFile', back_populates='project', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'contract_id': self.contract_id,
            'status': self.status,
            'priority': self.priority,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_public': self.is_public,
            'task_count': self.task_count,
            'completed_task_count': self.completed_task_count,
            'member_count': self.member_count,
            'version': self.version,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ============================================================
# 2. 项目成员 (ProjectMember) - 多对多关联 + 角色
# ============================================================
class ProjectMember(db.Model):
    """项目成员表 - 用户与项目的多对多关系，含角色"""
    __tablename__ = 'project_members'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # 项目内角色: owner, manager, member, observer
    role = db.Column(db.String(32), default='member', index=True)
    
    # 邀请信息
    invited_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 成员状态: active, inactive, removed
    status = db.Column(db.String(32), default='active')
    
    # 通知设置
    notify_on_task = db.Column(db.Boolean, default=True)      # 任务变更通知
    notify_on_comment = db.Column(db.Boolean, default=True)     # 评论通知
    notify_on_mention = db.Column(db.Boolean, default=True)     # @提及通知
    notify_digest = db.Column(db.Boolean, default=False)        # 每日摘要

    project = db.relationship('Project', back_populates='members')
    user = db.relationship('User', foreign_keys=[user_id], backref='project_memberships')
    inviter = db.relationship('User', foreign_keys=[invited_by])

    __table_args__ = (
        db.UniqueConstraint('project_id', 'user_id', name='uq_project_member'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'user_id': self.user_id,
            'role': self.role,
            'status': self.status,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'user': self.user.to_dict() if self.user else None,
        }

    @staticmethod
    def check_permission(project_id, user_id, required_roles=None):
        """检查用户在项目中的权限
        
        Args:
            project_id: 项目ID
            user_id: 用户ID
            required_roles: 需要的角色列表，如 ['owner', 'manager']。
                           为 None 时只检查是否为成员
        """
        member = ProjectMember.query.filter_by(
            project_id=project_id, user_id=user_id, status='active'
        ).first()
        
        if not member:
            return False, None
        
        if required_roles is None:
            return True, member.role
            
        role_hierarchy = {'owner': 4, 'manager': 3, 'member': 2, 'observer': 1}
        required_level = max(role_hierarchy.get(r, 0) for r in required_roles)
        user_level = role_hierarchy.get(member.role, 0)
        
        return user_level >= required_level, member.role


# ============================================================
# 3. 任务 (Task) - 项目内的待办事项
# ============================================================
class Task(db.Model):
    """任务表 - 项目内的具体工作项"""
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, index=True)
    
    # 任务标题和描述
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # 父任务 (支持子任务)
    parent_task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))
    
    # 负责人
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    
    # 任务状态: todo, in_progress, in_review, done, cancelled
    status = db.Column(db.String(32), default='todo', index=True)
    
    # 优先级: low, medium, high, urgent
    priority = db.Column(db.String(16), default='medium')
    
    # 任务类型: task, bug, feature, improvement, document
    task_type = db.Column(db.String(32), default='task')
    
    # 时间
    due_date = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # 排序权重
    sort_order = db.Column(db.Integer, default=0)
    
    # 工时估算/实际
    estimated_hours = db.Column(db.Float)
    actual_hours = db.Column(db.Float)
    
    # 标签 (JSON数组存储)
    tags = db.Column(db.JSON, default=list)
    
    # 版本控制
    version = db.Column(db.Integer, default=1)
    
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    project = db.relationship('Project', back_populates='tasks')
    assignee = db.relationship('User', foreign_keys=[assignee_id], backref='assigned_tasks')
    creator = db.relationship('User', foreign_keys=[created_by])
    parent_task = db.relationship('Task', remote_side=[id], backref='sub_tasks')
    comments = db.relationship('Comment', back_populates='task', cascade='all, delete-orphan')
    attachments = db.relationship('TaskAttachment', back_populates='task', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'title': self.title,
            'description': self.description,
            'parent_task_id': self.parent_task_id,
            'assignee_id': self.assignee_id,
            'assignee_name': self.assignee.real_name if self.assignee else None,
            'status': self.status,
            'priority': self.priority,
            'task_type': self.task_type,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'sort_order': self.sort_order,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'tags': self.tags or [],
            'version': self.version,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'comment_count': len(self.comments) if self.comments else 0,
        }


# ============================================================
# 4. 评论 (Comment) - 协作讨论
# ============================================================
class Comment(db.Model):
    """评论表 - 支持对项目和任务的评论"""
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    
    # 评论目标 (多态关联: 可评论项目或任务)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True, index=True)
    
    content = db.Column(db.Text, nullable=False)
    
    # 评论类型: text, system
    comment_type = db.Column(db.String(32), default='text')
    
    # 回复关系
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    reply_to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 回复的目标用户
    
    # @提及的用户 IDs (JSON数组)
    mentioned_user_ids = db.Column(db.JSON, default=list)
    
    # 是否已解决 (用于讨论中的问题确认)
    is_resolved = db.Column(db.Boolean, default=False)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolved_at = db.Column(db.DateTime)
    
    # 编辑记录
    edited_at = db.Column(db.DateTime)
    edit_count = db.Column(db.Integer, default=0)
    
    is_deleted = db.Column(db.Boolean, default=False)  # 软删除

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    project = db.relationship('Project', back_populates='comments')
    task = db.relationship('Task', back_populates='comments')
    author = db.relationship('User', foreign_keys=[created_by], backref='comments')
    parent = db.relationship('Comment', remote_side=[id], backref='replies')
    reply_to_user = db.relationship('User', foreign_keys=[reply_to_user_id])
    resolver = db.relationship('User', foreign_keys=[resolved_by])

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'task_id': self.task_id,
            'content': self.content,
            'comment_type': self.comment_type,
            'parent_id': self.parent_id,
            'reply_to_user_id': self.reply_to_user_id,
            'mentioned_user_ids': self.mentioned_user_ids or [],
            'is_resolved': self.is_resolved,
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'edit_count': self.edit_count,
            'is_deleted': self.is_deleted,
            'created_by': self.created_by,
            'author_name': self.author.real_name if self.author else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reply_count': len(self.replies) if self.replies else 0,
        }


# ============================================================
# 5. 编辑锁 (ContractEditLock) - 原有功能保留
# ============================================================
class ContractEditLock(db.Model):
    """合同编辑锁 - 实现悲观锁，同一时间只允许一人编辑"""
    __tablename__ = 'contract_edit_locks'

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=False, unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_name = db.Column(db.String(128), nullable=False)
    lock_acquired_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    lock_expires_at = db.Column(db.DateTime, nullable=False)
    session_id = db.Column(db.String(128), index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    user = db.relationship('User', backref='edit_locks')
    contract = db.relationship('Contract', backref='edit_lock')

    def to_dict(self):
        return {
            'id': self.id,
            'contract_id': self.contract_id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'lock_acquired_at': self.lock_acquired_at.isoformat() if self.lock_acquired_at else None,
            'lock_expires_at': self.lock_expires_at.isoformat() if self.lock_expires_at else None,
            'session_id': self.session_id,
            'is_active': self.is_active,
        }

    @staticmethod
    def acquire_lock(contract_id, user_id, user_name, session_id, timeout_seconds=300):
        now = datetime.utcnow()
        ContractEditLock.query.filter(
            ContractEditLock.is_active == True,
            ContractEditLock.lock_expires_at < now
        ).update({'is_active': False})

        existing_lock = ContractEditLock.query.filter_by(
            contract_id=contract_id, is_active=True
        ).first()

        if existing_lock:
            if existing_lock.user_id == user_id and existing_lock.session_id == session_id:
                existing_lock.lock_expires_at = now + timedelta(seconds=timeout_seconds)
                db.session.commit()
                return existing_lock.to_dict(), None
            else:
                remaining_seconds = int((existing_lock.lock_expires_at - now).total_seconds())
                return {
                    'message': f'该合同正在被 {existing_lock.user_name} 编辑',
                    'locked_by': existing_lock.user_name,
                    'locked_by_id': existing_lock.user_id,
                    'lock_acquired_at': existing_lock.lock_acquired_at.isoformat(),
                    'expires_in': max(remaining_seconds, 0),
                }, 409

        existing_inactive = ContractEditLock.query.filter_by(
            contract_id=contract_id, is_active=False
        ).first()

        if existing_inactive:
            existing_inactive.user_id = user_id
            existing_inactive.user_name = user_name
            existing_inactive.session_id = session_id
            existing_inactive.lock_acquired_at = now
            existing_inactive.lock_expires_at = now + timedelta(seconds=timeout_seconds)
            existing_inactive.is_active = True
            db.session.commit()
            return existing_inactive.to_dict(), None

        new_lock = ContractEditLock(
            contract_id=contract_id,
            user_id=user_id,
            user_name=user_name,
            session_id=session_id,
            lock_expires_at=now + timedelta(seconds=timeout_seconds),
            is_active=True,
        )
        db.session.add(new_lock)
        db.session.commit()
        return new_lock.to_dict(), None

    @staticmethod
    def release_lock(contract_id, user_id, session_id):
        lock = ContractEditLock.query.filter_by(
            contract_id=contract_id, user_id=user_id, is_active=True,
        ).first()
        if not lock:
            return True, '无活跃的编辑锁'
        lock.is_active = False
        db.session.commit()
        return True, '编辑锁已释放'

    @staticmethod
    def renew_lock(contract_id, user_id, session_id, timeout_seconds=300):
        now = datetime.utcnow()
        lock = ContractEditLock.query.filter_by(
            contract_id=contract_id, user_id=user_id,
            session_id=session_id, is_active=True,
        ).first()
        if lock:
            lock.lock_expires_at = now + timedelta(seconds=timeout_seconds)
            db.session.commit()
            return lock.to_dict(), None
        return {'message': '未找到有效锁或会话不匹配'}, 404

    @staticmethod
    def get_lock_info(contract_id):
        now = datetime.utcnow()
        lock = ContractEditLock.query.filter_by(contract_id=contract_id, is_active=True).first()
        if not lock:
            return None
        data = lock.to_dict()
        data['expires_in'] = max(int((lock.lock_expires_at - now).total_seconds()), 0)
        return data


# ============================================================
# 6. 通知 (Notification) - 系统消息推送
# ============================================================
class Notification(db.Model):
    """通知表 - 系统内消息通知"""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # 通知类型: task_assigned, task_due, comment_mention, 
    #          project_invited, system_announcement
    notification_type = db.Column(db.String(64), nullable=False, index=True)
    
    # 标题和内容
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text)
    
    # 关联资源
    resource_type = db.Column(db.String(64))   # project, task, comment, contract
    resource_id = db.Column(db.String(64))     # 对应资源的 ID
    
    # 发送者
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # 状态: unread, read, archived
    status = db.Column(db.String(32), default='unread', index=True)
    
    # 动作按钮 (JSON)
    actions = db.Column(db.JSON)  # [{'label': '查看', 'url': '/...'}, ...]

    sent_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime)

    user = db.relationship('User', foreign_keys=[user_id], backref='notifications')
    sender = db.relationship('User', foreign_keys=[sender_id])

    def to_dict(self):
        return {
            'id': self.id,
            'notification_type': self.notification_type,
            'title': self.title,
            'content': self.content,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'sender_id': self.sender_id,
            'sender_name': self.sender.real_name if self.sender else '系统',
            'status': self.status,
            'actions': self.actions or [],
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
        }

    @staticmethod
    def create(user_ids, notification_type, title, content, **kwargs):
        """批量创建通知
        
        Args:
            user_ids: 目标用户ID列表
            notification_type: 通知类型
            title: 标题
            content: 内容
            **kwargs: resource_type, resource_id, sender_id, actions
        """
        notifications = []
        for uid in user_ids:
            notif = Notification(
                user_id=uid,
                notification_type=notification_type,
                title=title,
                content=content,
                resource_type=kwargs.get('resource_type'),
                resource_id=kwargs.get('resource_id'),
                sender_id=kwargs.get('sender_id'),
                actions=kwargs.get('actions'),
            )
            notifications.append(notif)
        db.session.add_all(notifications)
        db.session.commit()
        return len(notifications)


# ============================================================
# 7. 活动日志 (ActivityLog) - 项目动态时间线
# ============================================================
class ActivityLog(db.Model):
    """活动日志表 - 记录项目中发生的所有事件"""
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, index=True)
    
    # 操作用户
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # 动作类型:
    # project_created, project_updated, project_status_changed
    # member_joined, member_left, member_role_changed
    # task_created, task_updated, task_status_changed, task_assigned
    # comment_created, comment_replied, file_uploaded
    action = db.Column(db.String(64), nullable=False, index=True)
    
    # 描述 (模板渲染后的可读文本)
    description = db.Column(db.Text, nullable=False)
    
    # 关联资源元数据 (JSON)
    extra_data = db.Column(db.JSON, default=dict)
    
    # 关联资源
    entity_type = db.Column(db.String(64))   # project, task, comment, file, member
    entity_id = db.Column(db.String(64))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    project = db.relationship('Project', back_populates='activities')
    user = db.relationship('User', backref='activities')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'user_id': self.user_id,
            'user_name': self.user.real_name if self.user else '系统',
            'action': self.action,
            'description': self.description,
            'extra_data': self.extra_data or {},
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def log(project_id, action, description, user_id=None, **kwargs):
        """快速记录活动日志"""
        activity = ActivityLog(
            project_id=project_id,
            user_id=user_id,
            action=action,
            description=description,
            extra_data=kwargs.get('extra_data'),
            entity_type=kwargs.get('entity_type'),
            entity_id=kwargs.get('entity_id'),
        )
        db.session.add(activity)
        db.session.commit()
        return activity


# ============================================================
# 8. 项目文件 (ProjectFile) - 项目级文件管理
# ============================================================
class ProjectFile(db.Model):
    """项目文件表 - 项目共享文件"""
    __tablename__ = 'project_files'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, index=True)
    
    # 上传者
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 文件信息
    origin_name = db.Column(db.String(255), nullable=False)
    storage_name = db.Column(db.String(255), nullable=False, unique=True)
    storage_path = db.Column(db.String(500), nullable=False)
    mime_type = db.Column(db.String(100))
    file_size = db.Column(db.BigInteger, default=0)
    file_hash = db.Column(db.String(128))
    
    # 文件分类: document, image, archive, other
    file_category = db.Column(db.String(50), default='other')
    
    # 文件描述
    description = db.Column(db.Text)
    
    # 文件夹路径 (支持目录结构, 如 '/设计文档/')
    folder_path = db.Column(db.String(255), default='/')
    
    # 版本号
    version_no = db.Column(db.Integer, default=1)
    is_latest = db.Column(db.Boolean, default=True)
    
    # 上传来源 (可选关联到某个任务)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)  # 软删除

    project = db.relationship('Project', back_populates='files')
    uploader = db.relationship('User', foreign_keys=[uploaded_by], backref='uploaded_project_files')
    task = db.relationship('Task', backref='project_files')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'origin_name': self.origin_name,
            'storage_name': self.storage_name,
            'mime_type': self.mime_type,
            'file_size': self.file_size,
            'file_category': self.file_category,
            'description': self.description,
            'folder_path': self.folder_path,
            'version_no': self.version_no,
            'is_latest': self.is_latest,
            'task_id': self.task_id,
            'uploaded_by': self.uploaded_by,
            'uploader_name': self.uploader.real_name if self.uploader else None,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


# ============================================================
# 9. 任务附件 (TaskAttachment) - 任务专属文件
# ============================================================
class TaskAttachment(db.Model):
    """任务附件表 - 关联到具体任务的文件"""
    __tablename__ = 'task_attachments'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    origin_name = db.Column(db.String(255), nullable=False)
    storage_name = db.Column(db.String(255), nullable=False, unique=True)
    storage_path = db.Column(db.String(500), nullable=False)
    mime_type = db.Column(db.String(100))
    file_size = db.Column(db.BigInteger, default=0)
    file_hash = db.Column(db.String(128))
    
    description = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)

    task = db.relationship('Task', back_populates='attachments')
    uploader = db.relationship('User', foreign_keys=[uploaded_by], backref='task_attachments')

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'origin_name': self.origin_name,
            'storage_name': self.storage_name,
            'mime_type': self.mime_type,
            'file_size': self.file_size,
            'description': self.description,
            'uploaded_by': self.uploaded_by,
            'uploader_name': self.uploader.real_name if self.uploader else None,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


# ============================================================
# 10. 审批历史 (ApprovalHistory) - 合同审批流程记录
# ============================================================
class ApprovalHistory(db.Model):
    """审批历史表 - 记录合同每一次审批流转"""
    __tablename__ = 'approval_history'

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=False, index=True)

    # 动作类型: submit / approve / reject / resubmit
    action = db.Column(db.String(32), nullable=False, index=True)

    # 操作人
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    operator_name = db.Column(db.String(128), nullable=False)

    # 审批意见
    comment = db.Column(db.Text)

    # 变更前后的审批状态
    from_status = db.Column(db.String(50))
    to_status = db.Column(db.String(50))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    contract = db.relationship('Contract', backref='approval_history')
    operator = db.relationship('User', backref='approval_actions')

    def to_dict(self):
        return {
            'id': self.id,
            'contract_id': self.contract_id,
            'action': self.action,
            'operator_id': self.operator_id,
            'operator_name': self.operator_name,
            'comment': self.comment,
            'from_status': self.from_status,
            'to_status': self.to_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
