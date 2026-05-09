from datetime import datetime
from decimal import Decimal
from app.extensions import db


class Company(db.Model):
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    credit_code = db.Column(db.String(64))
    address = db.Column(db.String(255))
    contact_person = db.Column(db.String(128))
    contact_phone = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'credit_code': self.credit_code,
            'address': self.address,
            'contact_person': self.contact_person,
            'contact_phone': self.contact_phone,
        }


class Contract(db.Model):
    __tablename__ = 'contracts'

    id = db.Column(db.Integer, primary_key=True)
    serial_no = db.Column(db.String(50), nullable=False, unique=True, index=True)
    contract_no = db.Column(db.String(100), nullable=False, unique=True, index=True)
    contract_name = db.Column(db.String(255), nullable=False)
    project_name = db.Column(db.String(255), nullable=False, index=True)
    contract_type = db.Column(db.String(64), default='general')
    sign_date = db.Column(db.Date)
    effective_date = db.Column(db.Date)
    expire_date = db.Column(db.Date)

    party_a_company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    party_b_company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    owner_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    owner_name = db.Column(db.String(128))
    department_id = db.Column(db.String(128))

    currency = db.Column(db.String(20), default='CNY')
    contract_amount = db.Column(db.Numeric(18, 2), default=0)
    invoiced_amount = db.Column(db.Numeric(18, 2), default=0)
    received_amount = db.Column(db.Numeric(18, 2), default=0)
    paid_amount = db.Column(db.Numeric(18, 2), default=0)
    unreceived_amount = db.Column(db.Numeric(18, 2), default=0)
    unpaid_amount = db.Column(db.Numeric(18, 2), default=0)

    processing_status = db.Column(db.String(50), default='draft')
    quotation_status = db.Column(db.String(50), default='not_started')
    settlement_status = db.Column(db.String(50), default='pending')
    approval_status = db.Column(db.String(50), default='draft')
    archive_status = db.Column(db.String(50), default='unarchived')
    description = db.Column(db.Text)

    version = db.Column(db.Integer, default=1, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False)

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    party_a = db.relationship('Company', foreign_keys=[party_a_company_id])
    party_b = db.relationship('Company', foreign_keys=[party_b_company_id])
    owner = db.relationship('User', foreign_keys=[owner_user_id])

    invoices = db.relationship('ContractInvoice', back_populates='contract', cascade='all, delete-orphan')
    receipts = db.relationship('ContractReceipt', back_populates='contract', cascade='all, delete-orphan')
    payments = db.relationship('ContractPayment', back_populates='contract', cascade='all, delete-orphan')
    acceptances = db.relationship('ContractAcceptance', back_populates='contract', cascade='all, delete-orphan')
    files = db.relationship('ContractFile', back_populates='contract', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'serial_no': self.serial_no,
            'contract_no': self.contract_no,
            'contract_name': self.contract_name,
            'project_name': self.project_name,
            'contract_type': self.contract_type,
            'sign_date': self.sign_date.isoformat() if self.sign_date else None,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'expire_date': self.expire_date.isoformat() if self.expire_date else None,
            'party_a_company_id': self.party_a_company_id,
            'party_b_company_id': self.party_b_company_id,
            'party_a_name': self.party_a.name if self.party_a else None,
            'party_b_name': self.party_b.name if self.party_b else None,
            'owner_user_id': self.owner_user_id,
            'owner_name': self.owner.real_name if self.owner else self.owner_name,
            'department_id': self.department_id,
            'currency': self.currency,
            'contract_amount': float(self.contract_amount or 0),
            'invoiced_amount': float(self.invoiced_amount or 0),
            'received_amount': float(self.received_amount or 0),
            'paid_amount': float(self.paid_amount or 0),
            'unreceived_amount': float(self.unreceived_amount or 0),
            'unpaid_amount': float(self.unpaid_amount or 0),
            'processing_status': self.processing_status,
            'quotation_status': self.quotation_status,
            'settlement_status': self.settlement_status,
            'approval_status': self.approval_status,
            'archive_status': self.archive_status,
            'description': self.description,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ContractInvoice(db.Model):
    __tablename__ = 'contract_invoices'

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), index=True, nullable=False)
    invoice_no = db.Column(db.String(100))
    invoice_type = db.Column(db.String(50))
    company_name = db.Column(db.String(255))
    company_address = db.Column(db.String(255))
    company_phone = db.Column(db.String(64))
    bank_account = db.Column(db.String(128))
    bank_name = db.Column(db.String(255))
    tax_no = db.Column(db.String(128))
    invoice_amount = db.Column(db.Numeric(18, 2), nullable=False)
    invoice_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='valid')
    attachment_id = db.Column(db.Integer, db.ForeignKey('contract_files.id'))
    remark = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    contract = db.relationship('Contract', back_populates='invoices')

    def to_dict(self):
        return {
            'id': self.id,
            'contract_id': self.contract_id,
            'invoice_no': self.invoice_no,
            'invoice_type': self.invoice_type,
            'company_name': self.company_name,
            'company_address': self.company_address,
            'company_phone': self.company_phone,
            'bank_account': self.bank_account,
            'bank_name': self.bank_name,
            'tax_no': self.tax_no,
            'invoice_amount': float(self.invoice_amount or 0),
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'status': self.status,
            'attachment_id': self.attachment_id,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class StandaloneInvoice(db.Model):
    __tablename__ = 'standalone_invoices'

    id = db.Column(db.Integer, primary_key=True)
    buyer_company_name = db.Column(db.String(255), nullable=False)
    invoice_no = db.Column(db.String(100), nullable=False, unique=True, index=True)
    invoice_date = db.Column(db.Date, nullable=False)
    invoice_amount = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'buyer_company_name': self.buyer_company_name,
            'invoice_no': self.invoice_no,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'invoice_amount': float(self.invoice_amount or 0),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ContractReceipt(db.Model):
    __tablename__ = 'contract_receipts'

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), index=True, nullable=False)
    receipt_amount = db.Column(db.Numeric(18, 2), nullable=False)
    receipt_date = db.Column(db.Date)
    receipt_method = db.Column(db.String(50))
    attachment_id = db.Column(db.Integer, db.ForeignKey('contract_files.id'))
    remark = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    contract = db.relationship('Contract', back_populates='receipts')

    def to_dict(self):
        return {
            'id': self.id,
            'contract_id': self.contract_id,
            'receipt_amount': float(self.receipt_amount or 0),
            'receipt_date': self.receipt_date.isoformat() if self.receipt_date else None,
            'receipt_method': self.receipt_method,
            'attachment_id': self.attachment_id,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ContractPayment(db.Model):
    __tablename__ = 'contract_payments'

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), index=True, nullable=False)
    payment_amount = db.Column(db.Numeric(18, 2), nullable=False)
    payment_date = db.Column(db.Date)
    payment_method = db.Column(db.String(50))
    attachment_id = db.Column(db.Integer, db.ForeignKey('contract_files.id'))
    remark = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    contract = db.relationship('Contract', back_populates='payments')

    def to_dict(self):
        return {
            'id': self.id,
            'contract_id': self.contract_id,
            'payment_amount': float(self.payment_amount or 0),
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payment_method': self.payment_method,
            'attachment_id': self.attachment_id,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ContractAcceptance(db.Model):
    __tablename__ = 'contract_acceptances'

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), index=True, nullable=False)
    acceptance_amount = db.Column(db.Numeric(18, 2), nullable=False)
    acceptance_date = db.Column(db.Date)
    acceptance_note = db.Column(db.Text)
    attachment_id = db.Column(db.Integer, db.ForeignKey('contract_files.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    contract = db.relationship('Contract', back_populates='acceptances')

    def to_dict(self):
        return {
            'id': self.id,
            'contract_id': self.contract_id,
            'acceptance_amount': float(self.acceptance_amount or 0),
            'acceptance_date': self.acceptance_date.isoformat() if self.acceptance_date else None,
            'acceptance_note': self.acceptance_note,
            'attachment_id': self.attachment_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ContractFile(db.Model):
    __tablename__ = 'contract_files'

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), index=True, nullable=False)
    file_category = db.Column(db.String(50), nullable=False, index=True)
    origin_name = db.Column(db.String(255), nullable=False)
    storage_name = db.Column(db.String(255), nullable=False, unique=True)
    storage_path = db.Column(db.String(500), nullable=False)
    mime_type = db.Column(db.String(100))
    file_size = db.Column(db.BigInteger, default=0)
    file_hash = db.Column(db.String(128))
    version_no = db.Column(db.Integer, default=1)
    is_latest = db.Column(db.Boolean, default=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)

    contract = db.relationship('Contract', back_populates='files')

    def to_dict(self):
        return {
            'id': self.id,
            'contract_id': self.contract_id,
            'file_category': self.file_category,
            'origin_name': self.origin_name,
            'storage_name': self.storage_name,
            'mime_type': self.mime_type,
            'file_size': self.file_size,
            'version_no': self.version_no,
            'is_latest': self.is_latest,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    module = db.Column(db.String(64), nullable=False)
    action = db.Column(db.String(64), nullable=False)
    resource_type = db.Column(db.String(64), nullable=False)
    resource_id = db.Column(db.String(64), nullable=False)
    request_method = db.Column(db.String(16))
    request_path = db.Column(db.String(255))
    request_ip = db.Column(db.String(64))
    before_data = db.Column(db.Text)
    after_data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'module': self.module,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'request_method': self.request_method,
            'request_path': self.request_path,
            'request_ip': self.request_ip,
            'before_data': self.before_data,
            'after_data': self.after_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }



def recalculate_contract_summary(contract: Contract):
    invoiced = sum((item.invoice_amount or Decimal('0')) for item in contract.invoices if item.status == 'valid')
    received = sum((item.receipt_amount or Decimal('0')) for item in contract.receipts)
    paid = sum((item.payment_amount or Decimal('0')) for item in contract.payments)

    contract.invoiced_amount = invoiced
    contract.received_amount = received
    contract.paid_amount = paid
    amount = contract.contract_amount or Decimal('0')
    contract.unreceived_amount = amount - received
    contract.unpaid_amount = amount - paid

    is_fully_settled = amount > 0 and contract.unreceived_amount <= 0 and contract.unpaid_amount <= 0

    if is_fully_settled:
        contract.settlement_status = 'settled'
    elif received > 0 or paid > 0:
        contract.settlement_status = 'partially_settled'
    else:
        contract.settlement_status = 'pending'

    # A contract cannot be completed while any receivable/payable balance remains.
    if is_fully_settled:
        contract.processing_status = 'completed'
    elif contract.processing_status == 'completed':
        contract.processing_status = 'executing'
