import hashlib
import os
import re
import tempfile
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file, current_app
from sqlalchemy import or_
from flask_jwt_extended import jwt_required

from openpyxl import load_workbook

from app.extensions import db, socketio
from app.models.contract import (
    Contract,
    ContractInvoice,
    StandaloneInvoice,
    ContractReceipt,
    ContractPayment,
    ContractAcceptance,
    ContractFile,
    Company,
    AuditLog,
    recalculate_contract_summary,
)
from app.models.collaboration import ApprovalHistory
from app.utils.audit import log_action
from app.utils.permissions import require_permissions, get_current_user


contract_bp = Blueprint('contracts', __name__, url_prefix='/api')


STATUS_FIELDS = {
    'processing_status', 'quotation_status', 'settlement_status', 'archive_status'
}


def _broadcast_contract_update(contract_id: int, event_type: str, user_name: str = None, extra_data: dict = None):
    """通过WebSocket广播合同更新事件给房间内所有用户"""
    payload = {
        'type': event_type,
        'contract_id': contract_id,
        'user': user_name,
        'timestamp': datetime.utcnow().isoformat(),
    }
    if extra_data:
        payload.update(extra_data)
    socketio.emit('collab_event', payload, room=f'contract_{contract_id}')



def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, '%Y-%m-%d').date()



def parse_decimal(value, field_name='金额'):
    if value in (None, ''):
        return Decimal('0')
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f'{field_name}格式不正确')


def parse_invoice_ocr_text(text):
    compact = re.sub(r'[ \t]+', ' ', text or '')
    lines = [line.strip() for line in compact.splitlines() if line.strip()]

    buyer = ''
    for index, line in enumerate(lines):
        if ('购买方' in line or '购 买 方' in line) and index + 1 < len(lines):
            buyer = re.sub(r'^(名称|购买方|购方)[:：\s]*', '', lines[index + 1]).strip()
        if not buyer and ('名称' in line or '购买方' in line):
            candidate = re.sub(r'^.*?(名称|购买方|购方)[:：\s]*', '', line).strip()
            if len(candidate) >= 3:
                buyer = candidate
        if not buyer and any(token in line for token in ['有限公司', '有限责任公司', '集团']):
            buyer = re.sub(r'^(名称|购买方|购方)[:：\s]*', '', line).strip()
        if buyer:
            break

    invoice_no = ''
    number_match = re.search(r'(?:发票号码|发票编号|票据号码|号码)[:：\s]*([0-9A-Z]{6,30})', compact, re.IGNORECASE)
    if number_match:
        invoice_no = number_match.group(1).strip()
    else:
        fallback_number = re.search(r'\b([0-9]{8,20})\b', compact)
        if fallback_number:
            invoice_no = fallback_number.group(1).strip()

    invoice_date = ''
    date_match = re.search(r'(20\d{2})[年\-/.](\d{1,2})[月\-/.](\d{1,2})', compact)
    if date_match:
        year, month, day = date_match.groups()
        invoice_date = f'{year}-{int(month):02d}-{int(day):02d}'

    raw_amount = ''
    amount_match = re.search(r'(?:价税合计|小写|合计金额|金额)[:：\s￥¥]*([0-9,]+\.\d{2})', compact)
    if not amount_match:
        amount_match = re.search(r'[￥¥]\s*([0-9,]+\.\d{2})', compact)
    if amount_match:
        raw_amount = amount_match.group(1)
    invoice_amount = 0
    if raw_amount:
        invoice_amount = parse_decimal(raw_amount.replace(',', ''), '发票金额')

    return {
        'buyer_company_name': buyer,
        'invoice_no': invoice_no,
        'invoice_date': invoice_date,
        'invoice_amount': invoice_amount,
    }



def contract_detail(contract: Contract):
    data = contract.to_dict()
    data['invoices'] = [item.to_dict() for item in contract.invoices]
    data['receipts'] = [item.to_dict() for item in contract.receipts]
    data['payments'] = [item.to_dict() for item in contract.payments]
    data['acceptances'] = [item.to_dict() for item in contract.acceptances]
    data['files'] = [item.to_dict() for item in contract.files if not item.deleted_at]
    data['approval_history'] = [item.to_dict() for item in
                                ApprovalHistory.query.filter_by(contract_id=contract.id)
                                .order_by(ApprovalHistory.created_at.asc()).all()]
    return data


def refresh_contract_summary(contract: Contract):
    before = (
        contract.invoiced_amount,
        contract.received_amount,
        contract.paid_amount,
        contract.unreceived_amount,
        contract.unpaid_amount,
        contract.processing_status,
        contract.settlement_status,
    )
    recalculate_contract_summary(contract)
    after = (
        contract.invoiced_amount,
        contract.received_amount,
        contract.paid_amount,
        contract.unreceived_amount,
        contract.unpaid_amount,
        contract.processing_status,
        contract.settlement_status,
    )
    if before != after:
        db.session.commit()


def normalize_owner_fields(data):
    owner_user_id = data.get('owner_user_id')
    owner_name = (data.get('owner_name') or '').strip() or None

    if owner_user_id not in (None, ''):
        return int(owner_user_id), None
    return None, owner_name


def normalize_party_company(data, id_key, name_key):
    company_id = data.get(id_key)
    company_name = (data.get(name_key) or '').strip()

    if company_id not in (None, ''):
        company = Company.query.get(int(company_id))
        if not company:
            raise ValueError('单位不存在或已被删除')
        return company.id

    if company_name:
        return _ensure_company(company_name).id

    return None



def get_contract_or_404(contract_id):
    contract = Contract.query.filter_by(id=contract_id, is_deleted=False).first()
    if not contract:
        return None, (jsonify({'message': '合同不存在'}), 404)
    return contract, None


@contract_bp.get('/dashboard/summary')
@require_permissions('contract:view')
def dashboard_summary():
    total = Contract.query.filter_by(is_deleted=False).count()
    executing = Contract.query.filter_by(is_deleted=False, processing_status='executing').count()
    completed = Contract.query.filter_by(is_deleted=False, processing_status='completed').count()
    pending_settlement = Contract.query.filter(Contract.is_deleted.is_(False), Contract.settlement_status != 'settled').count()
    recent_contracts = Contract.query.filter_by(is_deleted=False).order_by(Contract.created_at.desc()).limit(5).all()
    invoice_total = StandaloneInvoice.query.count()
    invoice_amount = db.session.query(db.func.coalesce(db.func.sum(StandaloneInvoice.invoice_amount), 0)).scalar() or 0
    recent_invoices = StandaloneInvoice.query.order_by(StandaloneInvoice.created_at.desc()).limit(5).all()
    return jsonify({
        'total_contracts': total,
        'executing_contracts': executing,
        'archived_contracts': completed,
        'pending_settlement_contracts': pending_settlement,
        'recent_contracts': [item.to_dict() for item in recent_contracts],
        'invoice_total': invoice_total,
        'invoice_amount': float(invoice_amount),
        'recent_invoices': [item.to_dict() for item in recent_invoices],
    })


@contract_bp.get('/invoices')
@require_permissions('contract:view')
def list_invoices():
    page = max(int(request.args.get('page', 1)), 1)
    page_size = min(max(int(request.args.get('page_size', 10)), 1), 100)
    keyword = (request.args.get('keyword') or '').strip()

    query = StandaloneInvoice.query
    if keyword:
        query = query.filter(
            or_(
                StandaloneInvoice.buyer_company_name.ilike(f'%{keyword}%'),
                StandaloneInvoice.invoice_no.ilike(f'%{keyword}%'),
            )
        )

    pagination = query.order_by(StandaloneInvoice.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
    total_amount = db.session.query(db.func.coalesce(db.func.sum(StandaloneInvoice.invoice_amount), 0)).scalar() or 0
    return jsonify({
        'items': [item.to_dict() for item in pagination.items],
        'total': pagination.total,
        'page': page,
        'page_size': page_size,
        'total_amount': float(total_amount),
    })


@contract_bp.post('/invoices')
@require_permissions('invoice:create')
def create_invoice_record():
    data = request.get_json() or {}
    buyer_company_name = (data.get('buyer_company_name') or '').strip()
    invoice_no = (data.get('invoice_no') or '').strip()
    invoice_date = data.get('invoice_date')
    invoice_amount = parse_decimal(data.get('invoice_amount'), '发票金额')
    user = get_current_user()

    if not buyer_company_name or not invoice_no or not invoice_date or invoice_amount <= 0:
        return jsonify({'message': '请填写必填信息'}), 400
    if StandaloneInvoice.query.filter_by(invoice_no=invoice_no).first():
        return jsonify({'message': '发票编号已存在'}), 400

    item = StandaloneInvoice(
        buyer_company_name=buyer_company_name,
        invoice_no=invoice_no,
        invoice_date=parse_date(invoice_date),
        invoice_amount=invoice_amount,
        created_by=user.id if user else None,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@contract_bp.post('/invoices/ocr-upload')
@require_permissions('invoice:create')
def upload_invoice_images():
    files = request.files.getlist('files')
    if not files:
        return jsonify({'message': '请先选择发票图片'}), 400

    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        return jsonify({'message': 'OCR模块没有实现'}), 500

    created = []
    failed = []
    user = get_current_user()

    for file_obj in files:
        filename = file_obj.filename or 'invoice-image'
        suffix = Path(filename).suffix or '.png'
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                file_obj.save(tmp.name)
                temp_path = tmp.name

            text = pytesseract.image_to_string(Image.open(temp_path), lang='chi_sim+eng')
            parsed = parse_invoice_ocr_text(text)
            if not parsed['buyer_company_name'] or not parsed['invoice_no'] or not parsed['invoice_date'] or parsed['invoice_amount'] <= 0:
                failed.append({'filename': filename, 'message': '未能识别完整发票信息'})
                continue
            if StandaloneInvoice.query.filter_by(invoice_no=parsed['invoice_no']).first():
                failed.append({'filename': filename, 'message': '发票编号已存在'})
                continue

            item = StandaloneInvoice(
                buyer_company_name=parsed['buyer_company_name'],
                invoice_no=parsed['invoice_no'],
                invoice_date=parse_date(parsed['invoice_date']),
                invoice_amount=parsed['invoice_amount'],
                created_by=user.id if user else None,
            )
            db.session.add(item)
            db.session.flush()
            created.append(item.to_dict())
        except pytesseract.TesseractNotFoundError:
            db.session.rollback()
            return jsonify({'message': 'OCR模块没有实现'}), 500
        except Exception as exc:
            failed.append({'filename': filename, 'message': str(exc)})
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    db.session.commit()
    return jsonify({
        'message': f'OCR处理完成：新增 {len(created)} 条，失败 {len(failed)} 条',
        'created': created,
        'failed': failed,
    })


@contract_bp.delete('/invoices/<int:invoice_id>')
@require_permissions('invoice:create')
def delete_invoice_record(invoice_id):
    item = StandaloneInvoice.query.get(invoice_id)
    if not item:
        return jsonify({'message': '发票不存在'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': '删除成功'})


@contract_bp.get('/invoices/export')
@require_permissions('contract:view')
def export_invoices():
    from io import BytesIO
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    keyword = (request.args.get('keyword') or '').strip()
    query = StandaloneInvoice.query
    if keyword:
        query = query.filter(
            or_(
                StandaloneInvoice.buyer_company_name.ilike(f'%{keyword}%'),
                StandaloneInvoice.invoice_no.ilike(f'%{keyword}%'),
            )
        )
    rows = query.order_by(StandaloneInvoice.created_at.desc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = '发票列表'
    headers = ['购买方公司名称', '发票编号', '日期', '金额']
    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='155EEF', end_color='155EEF', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin', color='D0D5DD'),
        right=Side(style='thin', color='D0D5DD'),
        top=Side(style='thin', color='D0D5DD'),
        bottom=Side(style='thin', color='D0D5DD'),
    )

    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center')

    for row_idx, item in enumerate(rows, start=2):
        values = [
            item.buyer_company_name,
            item.invoice_no,
            item.invoice_date.isoformat() if item.invoice_date else '',
            float(item.invoice_amount or 0),
        ]
        for col_idx, value in enumerate(values, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            if col_idx == 4:
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal='right')

    for col, width in zip(['A', 'B', 'C', 'D'], [32, 22, 16, 16]):
        ws.column_dimensions[col].width = width
    ws.freeze_panes = 'A2'

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f"发票列表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(buffer, as_attachment=True, download_name=filename,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@contract_bp.get('/contracts')
@require_permissions('contract:view')
def list_contracts():
    page = max(int(request.args.get('page', 1)), 1)
    page_size = min(max(int(request.args.get('page_size', 10)), 1), 100)
    keyword = (request.args.get('keyword') or '').strip()
    processing_status = (request.args.get('processing_status') or '').strip()
    approval_status = (request.args.get('approval_status') or '').strip()
    raw_ids = (request.args.get('ids') or '').strip()

    query = Contract.query.filter_by(is_deleted=False)
    if raw_ids:
        try:
            selected_ids = [int(item) for item in raw_ids.split(',') if item.strip()]
        except ValueError:
            return jsonify({'message': '导出合同选择参数不正确'}), 400
        if not selected_ids:
            return jsonify({'message': '请选择要导出的合同'}), 400
        query = query.filter(Contract.id.in_(selected_ids))
    if keyword:
        query = query.filter(
            or_(
                Contract.project_name.ilike(f'%{keyword}%'),
                Contract.contract_name.ilike(f'%{keyword}%'),
                Contract.contract_no.ilike(f'%{keyword}%'),
            )
        )
    if processing_status:
        query = query.filter_by(processing_status=processing_status)
    if approval_status:
        query = query.filter_by(approval_status=approval_status)

    pagination = query.order_by(Contract.updated_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
    return jsonify({
        'items': [item.to_dict() for item in pagination.items],
        'total': pagination.total,
        'page': page,
        'page_size': page_size,
    })


@contract_bp.get('/contracts/export')
@require_permissions('contract:view')
def export_contracts():
    """导出合同数据为 Excel 文件，支持按当前筛选条件导出"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from io import BytesIO
    from urllib.parse import parse_qs

    keyword = (request.args.get('keyword') or '').strip()
    processing_status = (request.args.get('processing_status') or '').strip()
    approval_status = (request.args.get('approval_status') or '').strip()
    raw_ids = (request.args.get('ids') or '').strip()

    query = Contract.query.filter_by(is_deleted=False)
    if raw_ids:
        try:
            selected_ids = [int(item) for item in raw_ids.split(',') if item.strip()]
        except ValueError:
            return jsonify({'message': '导出合同选择参数不正确'}), 400
        if not selected_ids:
            return jsonify({'message': '请选择要导出的合同'}), 400
        query = query.filter(Contract.id.in_(selected_ids))
    if keyword:
        query = query.filter(
            or_(
                Contract.project_name.ilike(f'%{keyword}%'),
                Contract.contract_name.ilike(f'%{keyword}%'),
                Contract.contract_no.ilike(f'%{keyword}%'),
            )
        )
    if processing_status:
        query = query.filter_by(processing_status=processing_status)
    if approval_status:
        query = query.filter_by(approval_status=approval_status)

    contracts = query.order_by(Contract.updated_at.desc()).all()

    # 创建工作簿
    wb = Workbook()
    ws = wb.active
    ws.title = "合同台账"

    # 表头样式
    header_font = Font(bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(start_color="155Eef", end_color="155Eef", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color='D0D5DD'),
        right=Side(style='thin', color='D0D5DD'),
        top=Side(style='thin', color='D0D5DD'),
        bottom=Side(style='thin', color='D0D5DD'),
    )

    headers = [
        "序号", "项目名称", "合同名称", "合同号", "合同类型",
        "甲方单位", "乙方单位", "签订日期", "合同金额",
        "已开票金额", "已收款金额", "已付款金额",
        "未收款金额", "未付款金额", "处理状态", "结清状态", "审批状态", "备注"
    ]

    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # 数据行样式
    data_alignment = Alignment(vertical="center")
    money_alignment = Alignment(horizontal="right", vertical="center")

    status_map_cn = {
        "draft": "草稿", "executing": "执行中", "completed": "已完成",
        "pending": "未结清", "partially_settled": "部分结清", "settled": "已结清",
        "not_started": "未开始", "in_progress": "进行中", "done": "已完成",
        "pending_approval": "审批中", "approved": "已通过",
        "general": "通用", "service": "服务", "software": "软件", "imported": "导入",
    }

    for row_idx, contract in enumerate(contracts, start=2):
        d = contract.to_dict()
        party_a_name = d.get('party_a_name', '')
        party_b_name = d.get('party_b_name', '')

        row_data = [
            d.get('serial_no', ''),
            d.get('project_name', ''),
            d.get('contract_name', ''),
            d.get('contract_no', ''),
            status_map_cn.get(d.get('contract_type', ''), d.get('contract_type', '')),
            party_a_name,
            party_b_name,
            str(d.get('sign_date') or ''),
            float(d.get('contract_amount') or 0),
            float(d.get('invoiced_amount') or 0),
            float(d.get('received_amount') or 0),
            float(d.get('paid_amount') or 0),
            float(d.get('unreceived_amount') or 0),
            float(d.get('unpaid_amount') or 0),
            status_map_cn.get(d.get('processing_status', ''), d.get('processing_status', '')),
            status_map_cn.get(d.get('settlement_status', ''), d.get('settlement_status', '')),
            status_map_cn.get(d.get('approval_status', ''), d.get('approval_status', '')),
            d.get('description', ''),
        ]

        for col_idx, value in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            if col_idx >= 9 and col_idx <= 14:
                cell.alignment = money_alignment
                cell.number_format = '#,##0.00'
            else:
                cell.alignment = data_alignment

    # 设置列宽
    col_widths = [16, 22, 22, 18, 10, 20, 20, 12, 14, 14, 14, 14, 14, 14, 10, 10, 10, 30]
    for idx, width in enumerate(col_widths, start=1):
        ws.column_dimensions[chr(64 + idx) if idx <= 26 else f'A{chr(64 + idx - 26)}'].width = width

    # 冻结首行
    ws.freeze_panes = 'A2'

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"合同台账导出_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(buffer, as_attachment=True, download_name=filename,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@contract_bp.post('/contracts')
@require_permissions('contract:create')
def create_contract():
    data = request.get_json() or {}
    user = get_current_user()

    required_fields = ['serial_no', 'contract_no', 'contract_name', 'project_name']
    missing_fields = [field for field in required_fields if not data.get(field)]
    if not (data.get('party_a_company_id') or data.get('party_a_name')):
        missing_fields.append('party_a_name')
    if not (data.get('party_b_company_id') or data.get('party_b_name')):
        missing_fields.append('party_b_name')
    if missing_fields:
        return jsonify({'message': '缺少必填字段', 'fields': missing_fields}), 400

    if Contract.query.filter_by(contract_no=data['contract_no']).first():
        return jsonify({'message': '合同号已存在'}), 400

    owner_user_id, owner_name = normalize_owner_fields(data)
    party_a_company_id = normalize_party_company(data, 'party_a_company_id', 'party_a_name')
    party_b_company_id = normalize_party_company(data, 'party_b_company_id', 'party_b_name')

    contract = Contract(
        serial_no=data['serial_no'],
        contract_no=data['contract_no'],
        contract_name=data['contract_name'],
        project_name=data['project_name'],
        contract_type=data.get('contract_type') or None,
        sign_date=parse_date(data.get('sign_date')),
        effective_date=parse_date(data.get('effective_date')),
        expire_date=parse_date(data.get('expire_date')),
        party_a_company_id=party_a_company_id,
        party_b_company_id=party_b_company_id,
        owner_user_id=owner_user_id,
        owner_name=owner_name,
        department_id=data.get('department_id') or None,
        currency=data.get('currency') or 'CNY',
        contract_amount=parse_decimal(data.get('contract_amount'), '合同金额'),
        processing_status=data.get('processing_status') or 'draft',
        quotation_status=data.get('quotation_status') or 'not_started',
        approval_status=data.get('approval_status') or 'draft',
        archive_status=data.get('archive_status') or 'unarchived',
        description=data.get('description') or None,
        created_by=user.id,
        updated_by=user.id,
    )
    recalculate_contract_summary(contract)
    db.session.add(contract)
    db.session.flush()
    log_action(user.id, 'contract', 'create', 'contract', contract.id, before_data=None, after_data=contract.to_dict())
    db.session.commit()
    return jsonify(contract.to_dict()), 201


@contract_bp.get('/contracts/<int:contract_id>')
@require_permissions('contract:view')
def get_contract(contract_id):
    contract, error = get_contract_or_404(contract_id)
    if error:
        return error
    refresh_contract_summary(contract)
    return jsonify(contract_detail(contract))


@contract_bp.put('/contracts/<int:contract_id>')
@require_permissions('contract:update')
def update_contract(contract_id):
    contract, error = get_contract_or_404(contract_id)
    if error:
        return error
    data = request.get_json() or {}
    user = get_current_user()

    version = int(data.get('version') or 0)
    if version != contract.version:
        return jsonify({'message': '该合同已被其他人修改，请刷新后重试', 'current_version': contract.version}), 409

    before = contract.to_dict()
    for field in ['serial_no', 'contract_no', 'contract_name', 'project_name', 'contract_type', 'currency', 'description']:
        if field in data:
            setattr(contract, field, data.get(field) or None)

    for field in ['sign_date', 'effective_date', 'expire_date']:
        if field in data:
            setattr(contract, field, parse_date(data.get(field)))

    if 'party_a_company_id' in data or 'party_a_name' in data:
        contract.party_a_company_id = normalize_party_company(data, 'party_a_company_id', 'party_a_name')

    if 'party_b_company_id' in data or 'party_b_name' in data:
        contract.party_b_company_id = normalize_party_company(data, 'party_b_company_id', 'party_b_name')

    if 'owner_user_id' in data or 'owner_name' in data:
        contract.owner_user_id, contract.owner_name = normalize_owner_fields(data)

    if 'department_id' in data:
        contract.department_id = data['department_id'] or None

    if 'contract_amount' in data:
        contract.contract_amount = parse_decimal(data.get('contract_amount'), '合同金额')

    for field in STATUS_FIELDS:
        if field in data:
            setattr(contract, field, data.get(field))

    contract.version += 1
    contract.updated_by = user.id
    recalculate_contract_summary(contract)
    log_action(user.id, 'contract', 'update', 'contract', contract.id, before_data=before, after_data=contract.to_dict())
    db.session.commit()
    _broadcast_contract_update(contract_id, 'contract_updated', user.real_name or user.username)
    return jsonify(contract.to_dict())


@contract_bp.delete('/contracts/<int:contract_id>')
@require_permissions('contract:delete')
def delete_contract(contract_id):
    contract, error = get_contract_or_404(contract_id)
    if error:
        return error
    user = get_current_user()
    before = contract.to_dict()
    contract.is_deleted = True
    contract.updated_by = user.id
    log_action(user.id, 'contract', 'delete', 'contract', contract.id, before_data=before, after_data={'is_deleted': True})
    db.session.commit()
    return jsonify({'message': '删除成功'})


@contract_bp.post('/contracts/<int:contract_id>/status')
@require_permissions('contract:update')
def update_contract_status(contract_id):
    contract, error = get_contract_or_404(contract_id)
    if error:
        return error
    data = request.get_json() or {}
    field_name = data.get('field_name')
    new_value = data.get('new_value')
    if field_name not in STATUS_FIELDS:
        return jsonify({'message': '状态字段不合法'}), 400
    user = get_current_user()
    before = contract.to_dict()
    setattr(contract, field_name, new_value)
    contract.version += 1
    contract.updated_by = user.id
    log_action(user.id, 'contract', 'status_update', 'contract', contract.id, before_data=before, after_data=contract.to_dict())
    db.session.commit()
    return jsonify(contract.to_dict())


@contract_bp.post('/contracts/<int:contract_id>/invoices')
@require_permissions('invoice:create')
def add_invoice(contract_id):
    contract, error = get_contract_or_404(contract_id)
    if error:
        return error
    data = request.get_json() or {}
    user = get_current_user()
    item = ContractInvoice(
        contract_id=contract.id,
        invoice_no=data.get('invoice_no'),
        invoice_type=data.get('invoice_type'),
        company_name=data.get('company_name'),
        company_address=data.get('company_address'),
        company_phone=data.get('company_phone'),
        bank_account=data.get('bank_account'),
        bank_name=data.get('bank_name'),
        tax_no=data.get('tax_no'),
        invoice_amount=parse_decimal(data.get('invoice_amount'), '开票金额'),
        invoice_date=parse_date(data.get('invoice_date')),
        status=data.get('status') or 'valid',
        remark=data.get('remark'),
        created_by=user.id,
    )
    db.session.add(item)
    db.session.flush()
    recalculate_contract_summary(contract)
    log_action(user.id, 'finance', 'create_invoice', 'invoice', item.id, after_data=item.to_dict())
    db.session.commit()
    return jsonify(item.to_dict()), 201


@contract_bp.post('/contracts/<int:contract_id>/receipts')
@require_permissions('receipt:create')
def add_receipt(contract_id):
    contract, error = get_contract_or_404(contract_id)
    if error:
        return error
    data = request.get_json() or {}
    user = get_current_user()
    item = ContractReceipt(
        contract_id=contract.id,
        receipt_amount=parse_decimal(data.get('receipt_amount'), '收款金额'),
        receipt_date=parse_date(data.get('receipt_date')),
        receipt_method=data.get('receipt_method'),
        remark=data.get('remark'),
        created_by=user.id,
    )
    db.session.add(item)
    db.session.flush()
    recalculate_contract_summary(contract)
    log_action(user.id, 'finance', 'create_receipt', 'receipt', item.id, after_data=item.to_dict())
    db.session.commit()
    return jsonify(item.to_dict()), 201


@contract_bp.post('/contracts/<int:contract_id>/payments')
@require_permissions('payment:create')
def add_payment(contract_id):
    contract, error = get_contract_or_404(contract_id)
    if error:
        return error
    data = request.get_json() or {}
    user = get_current_user()
    item = ContractPayment(
        contract_id=contract.id,
        payment_amount=parse_decimal(data.get('payment_amount'), '付款金额'),
        payment_date=parse_date(data.get('payment_date')),
        payment_method=data.get('payment_method'),
        remark=data.get('remark'),
        created_by=user.id,
    )
    db.session.add(item)
    db.session.flush()
    recalculate_contract_summary(contract)
    log_action(user.id, 'finance', 'create_payment', 'payment', item.id, after_data=item.to_dict())
    db.session.commit()
    return jsonify(item.to_dict()), 201


@contract_bp.post('/contracts/<int:contract_id>/acceptances')
@require_permissions('acceptance:create')
def add_acceptance(contract_id):
    contract, error = get_contract_or_404(contract_id)
    if error:
        return error
    data = request.get_json() or {}
    user = get_current_user()
    item = ContractAcceptance(
        contract_id=contract.id,
        acceptance_amount=parse_decimal(data.get('acceptance_amount'), '验收金额'),
        acceptance_date=parse_date(data.get('acceptance_date')),
        acceptance_note=data.get('acceptance_note'),
        created_by=user.id,
    )
    db.session.add(item)
    db.session.flush()
    log_action(user.id, 'acceptance', 'create_acceptance', 'acceptance', item.id, after_data=item.to_dict())
    db.session.commit()
    return jsonify(item.to_dict()), 201


@contract_bp.post('/contracts/<int:contract_id>/files')
@require_permissions('file:upload')
def upload_contract_file(contract_id):
    contract, error = get_contract_or_404(contract_id)
    if error:
        return error
    user = get_current_user()
    file_obj = request.files.get('file')
    category = request.form.get('file_category', 'other')
    if not file_obj:
        return jsonify({'message': '缺少文件'}), 400

    upload_dir = Path(current_app.config['UPLOAD_DIR']) / str(contract.id) / category
    upload_dir.mkdir(parents=True, exist_ok=True)

    origin_name = file_obj.filename
    suffix = Path(origin_name).suffix
    storage_name = f"{uuid.uuid4().hex}{suffix}"
    storage_path = upload_dir / storage_name

    content = file_obj.read()
    file_size = len(content)
    if file_size > 5 * 1024 * 1024:
        return jsonify({'message': f'文件大小为 {file_size / (1024 * 1024):.1f}MB，超过 5MB 限制'}), 413
    file_hash = hashlib.sha256(content).hexdigest()
    with open(storage_path, 'wb') as fw:
        fw.write(content)

    current_latest = ContractFile.query.filter_by(contract_id=contract.id, file_category=category, is_latest=True, deleted_at=None).all()
    version_no = 1
    if current_latest:
        version_no = max(item.version_no for item in current_latest) + 1
        for item in current_latest:
            item.is_latest = False

    file_row = ContractFile(
        contract_id=contract.id,
        file_category=category,
        origin_name=origin_name,
        storage_name=storage_name,
        storage_path=str(storage_path),
        mime_type=file_obj.mimetype,
        file_size=len(content),
        file_hash=file_hash,
        version_no=version_no,
        is_latest=True,
        uploaded_by=user.id,
    )
    db.session.add(file_row)
    db.session.flush()
    log_action(user.id, 'file', 'upload', 'contract_file', file_row.id, after_data=file_row.to_dict())
    db.session.commit()
    _broadcast_contract_update(contract_id, 'file_uploaded', user.real_name or user.username, {'file': file_row.to_dict()})
    return jsonify(file_row.to_dict()), 201


@contract_bp.get('/files/<int:file_id>/download')
@require_permissions('file:download')
def download_file(file_id):
    file_row = ContractFile.query.filter_by(id=file_id).first()
    if not file_row or file_row.deleted_at:
        return jsonify({'message': '文件不存在'}), 404
    if not os.path.exists(file_row.storage_path):
        return jsonify({'message': '文件已丢失'}), 404
    return send_file(file_row.storage_path, as_attachment=True, download_name=file_row.origin_name)


@contract_bp.delete('/files/<int:file_id>')
@require_permissions('file:delete')
def delete_file(file_id):
    file_row = ContractFile.query.filter_by(id=file_id).first()
    if not file_row or file_row.deleted_at:
        return jsonify({'message': '文件不存在'}), 404
    user = get_current_user()
    before = file_row.to_dict()
    file_row.deleted_at = datetime.utcnow()
    file_row.is_latest = False
    log_action(user.id, 'file', 'delete', 'contract_file', file_row.id, before_data=before, after_data={'deleted_at': file_row.deleted_at.isoformat()})
    db.session.commit()
    return jsonify({'message': '文件已删除'})


@contract_bp.get('/audit-logs')
@require_permissions('audit:view')
def list_audit_logs():
    page = max(int(request.args.get('page', 1)), 1)
    page_size = min(max(int(request.args.get('page_size', 20)), 1), 100)
    pagination = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
    return jsonify({
        'items': [item.to_dict() for item in pagination.items],
        'total': pagination.total,
        'page': page,
        'page_size': page_size,
    })


# ==================== Excel 导入相关工具函数 ====================

AUTO_CONTRACT_PREFIX = "AUTO-HT"
AUTO_PROJECT_PREFIX = "XM"


def _parse_import_decimal(value):
    """安全解析数值"""
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value).strip())
    except Exception:
        return Decimal("0")


def _parse_import_date(value):
    """智能解析中文/数字日期"""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    m = re.search(r"(20\d{2})[年\-/]?(\d{1,2})[月\-/]?(\d{1,2})", text)
    if m:
        y, mo, d = map(int, m.groups())
        try:
            return datetime(y, mo, d).date()
        except ValueError:
            return None
    if re.fullmatch(r"20\d{6}", text):
        try:
            return datetime.strptime(text, "%Y%m%d").date()
        except ValueError:
            return None
    try:
        return datetime.strptime(text, '%Y-%m-%d').date()
    except Exception:
        return None


def _ensure_company(name):
    """查找或创建公司"""
    name = (name or "").strip()
    if not name:
        return None
    row = Company.query.filter_by(name=name).first()
    if row:
        return row
    row = Company(name=name)
    db.session.add(row)
    db.session.flush()
    return row


def _unique_contract_no(raw_contract_no, row_index):
    """确保合同号唯一"""
    base = (raw_contract_no or "").strip()
    if not base:
        base = f"{AUTO_CONTRACT_PREFIX}-{row_index:04d}"
    candidate = base
    suffix = 1
    while Contract.query.filter_by(contract_no=candidate).first():
        suffix += 1
        candidate = f"{base}-{suffix}"
    return candidate


def _unique_project_code(row_index):
    """确保项目号唯一"""
    candidate = f"{AUTO_PROJECT_PREFIX}-{row_index:04d}"
    suffix = 1
    while Contract.query.filter_by(serial_no=candidate).first():
        suffix += 1
        candidate = f"{AUTO_PROJECT_PREFIX}-{row_index:04d}-{suffix}"
    return candidate


@contract_bp.post('/contracts/import')
@require_permissions('contract:create')
def import_contracts_from_excel():
    """从上传的 Excel 文件批量导入合同"""
    import re as _re
    from datetime import datetime as _datetime

    user = get_current_user()

    # ========== 1. 文件校验 ==========
    file_obj = request.files.get('file')
    if not file_obj:
        return jsonify({'message': '请选择要导入的 Excel 文件'}), 400

    filename = file_obj.filename or ''
    if not filename.lower().endswith(('.xlsx', '.xls')):
        return jsonify({'message': '仅支持 .xlsx 或 .xls 格式的 Excel 文件'}), 400

    sheet_name = request.form.get('sheet') or None

    # ========== 2. 字段映射配置 ==========
    # normalize_header 之后的标准化 key -> 后端字段名
    FIELD_ALIASES = {
        # 项目名称
        'projectname': 'project_name',
        'project_name': 'project_name',
        '项目': 'project_name',
        '项目名称': 'project_name',
        '工程名称': 'project_name',
        # 合同号
        'contractno': 'contract_no',
        'contract_no': 'contract_no',
        '编号': 'contract_no',
        '合同号': 'contract_no',
        '合同编号': 'contract_no',
        '合同编码': 'contract_no',
        # 合同金额
        'contractamount': 'contract_amount',
        'contract_amount': 'contract_amount',
        'amount': 'contract_amount',
        '总金额': 'contract_amount',
        '合同金额': 'contract_amount',
        '金额': 'contract_amount',
        # 签订日期
        'signdate': 'sign_date',
        'sign_date': 'sign_date',
        '签订日期': 'sign_date',
        '合同签订日期': 'sign_date',
        '签约日期': 'sign_date',
        # 乙方单位
        'partyb': 'party_b',
        'party_b': 'party_b',
        '乙方': 'party_b',
        '乙方单位': 'party_b',
        '乙方名称': 'party_b',
        'secondparty': 'party_b',
        # 甲方单位
        'partya': 'party_a',
        'party_a': 'party_a',
        '甲方': 'party_a',
        '甲方单位': 'party_a',
        '甲方名称': 'party_a',
        'firstparty': 'party_a',
        # 已收/已开
        'receivedopened': 'received_opened',
        'received_opened': 'received_opened',
        '已收已开': 'received_opened',
        '已收/已开': 'received_opened',
        '已收款已开票': 'received_opened',
        # 已付款金
        'paidamount': 'paid_amount',
        'paid_amount': 'paid_amount',
        '已付款金': 'paid_amount',
        '已付款金额': 'paid_amount',
        '已付款': 'paid_amount',
        # 验收金额
        'acceptanceamount': 'acceptance_amount',
        'acceptance_amount': 'acceptance_amount',
        '验收金额': 'acceptance_amount',
        '已验收金额': 'acceptance_amount',
        # 备注
        'remark': 'description',
        'remarks': 'description',
        'note': 'description',
        '说明': 'description',
        '备注': 'description',
    }

    REQUIRED_FIELDS = ['project_name', 'contract_no', 'contract_amount', 'sign_date', 'party_a', 'party_b']

    # ========== 3. 工具函数 ==========
    def normalize_header(raw):
        """标准化表头：去空格/换行/制表符，英文小写，替换斜杠/驼峰等"""
        if raw is None:
            return ''
        s = str(raw).strip()
        # 去除换行、制表符、多余空格
        s = _re.sub(r'[\r\n\t]+', '', s)
        s = _re.sub(r'\s+', '', s)
        # 替换 / 为空格后统一小写
        s = s.replace('/', '').replace('\\', '')
        # 驼峰转下划线：contractNo -> contract_no
        s = _re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), s)
        s = s.lower().strip('_')
        return s

    def parse_import_decimal(value):
        """安全解析金额"""
        if value in (None, ''):
            return Decimal('0')
        try:
            return Decimal(str(value).strip())
        except Exception:
            return None  # 返回 None 表示解析失败

    def parse_import_date(value):
        """智能解析日期，支持 Excel 日期类型和多种字符串格式"""
        if value is None or value == '':
            return None
        if isinstance(value, _datetime):
            return value.date()
        text = str(value).strip()
        if not text:
            return None
        # 匹配 2025-01-01 / 2025/01/01 / 2025.01.01 / 2025年01月01日
        m = _re.search(r'(20\d{2})[\-年/.]?(\d{1,2})[\-月/.]?(\d{1,2})', text)
        if m:
            y, mo, d = map(int, m.groups())
            try:
                return _datetime(y, mo, d).date()
            except ValueError:
                return None
        # 匹配纯数字 20250101
        if _re.fullmatch(r'20\d{6}', text):
            try:
                return _datetime.strptime(text, '%Y%m%d').date()
            except ValueError:
                return None
        return None

    # ========== 4. 读取 Excel ==========
    try:
        wb = load_workbook(file_obj, data_only=True)
    except Exception:
        return jsonify({'message': '导入失败：无法读取 Excel 文件，请检查文件是否损坏'}), 400

    try:
        if sheet_name and sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
        else:
            ws = wb.active

        if ws.max_row < 2:
            return jsonify({'message': '导入失败：Excel 文件没有数据行，请检查文件内容'}), 400

        # ========== 5. 解析表头 ==========
        raw_headers = [cell.value for cell in ws[1]]
        normalized_map = {}  # normalized_key -> col_index
        for idx, raw in enumerate(raw_headers):
            if raw is None:
                continue
            norm_key = normalize_header(raw)
            if norm_key and norm_key not in normalized_map:
                normalized_map[norm_key] = idx

        # 映射到后端字段：backend_field -> col_index
        field_col_map = {}
        for norm_key, col_idx in normalized_map.items():
            backend_field = FIELD_ALIASES.get(norm_key)
            if backend_field and backend_field not in field_col_map:
                field_col_map[backend_field] = col_idx

        # ========== 6. 必填字段校验 ==========
        missing = [f for f in REQUIRED_FIELDS if f not in field_col_map]
        if missing:
            name_map = {
                'project_name': '项目名称',
                'contract_no': '合同号',
                'contract_amount': '合同金额',
                'sign_date': '签订日期',
                'party_a': '甲方单位',
                'party_b': '乙方单位',
            }
            missing_names = '、'.join(name_map.get(f, f) for f in missing)
            return jsonify({'message': f'导入失败：Excel 缺少必填字段：{missing_names}'}), 400

        # ========== 7. 逐行导入 ==========
        imported = 0
        skipped = 0
        errors = []
        created_contracts = []

        for excel_row_no, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            try:
                # 空行检查
                if all(v is None or str(v).strip() == '' for v in row):
                    continue

                # 读取必填字段
                project_name = str(row[field_col_map['project_name']] or '').strip()
                if not project_name:
                    skipped += 1
                    continue

                raw_contract_no = str(row[field_col_map['contract_no']] or '').strip()

                # 合同金额（必填，必须是数字)
                contract_amount = parse_import_decimal(row[field_col_map['contract_amount']])
                if contract_amount is None:
                    errors.append(f'第 {excel_row_no} 行合同金额格式不正确')
                    continue

                # 签订日期（必填）
                sign_date_raw = row[field_col_map['sign_date']]
                sign_date = parse_import_date(sign_date_raw)
                if sign_date is None:
                    errors.append(f'第 {excel_row_no} 行签订日期格式不正确')
                    continue

                # 甲乙方
                party_a_name = str(row[field_col_map['party_a']] or '').strip() or '未命名甲方'
                party_b_name = str(row[field_col_map['party_b']] or '').strip() or '未命名乙方'
                party_a = _ensure_company(party_a_name)
                party_b = _ensure_company(party_b_name)

                # 可选金额字段
                received_opened = parse_import_decimal(
                    row[field_col_map['received_opened']]
                ) if 'received_opened' in field_col_map else Decimal('0')
                if received_opened is None:
                    errors.append(f'第 {excel_row_no} 行已收/已开格式不正确')
                    continue

                paid_amount = parse_import_decimal(
                    row[field_col_map['paid_amount']]
                ) if 'paid_amount' in field_col_map else Decimal('0')
                if paid_amount is None:
                    errors.append(f'第 {excel_row_no} 行已付款金格式不正确')
                    continue

                acceptance_amount = parse_import_decimal(
                    row[field_col_map['acceptance_amount']]
                ) if 'acceptance_amount' in field_col_map else Decimal('0')
                if acceptance_amount is None:
                    errors.append(f'第 {excel_row_no} 行验收金额格式不正确')
                    continue

                # 备注
                description = None
                if 'description' in field_col_map:
                    desc_val = row[field_col_map['description']]
                    description = str(desc_val).strip() if desc_val is not None else None

                # 生成唯一合同号和项目号
                contract_no = _unique_contract_no(raw_contract_no, excel_row_no - 1)
                project_code = _unique_project_code(excel_row_no - 1)

                # 去重判断
                if Contract.query.filter_by(project_name=project_name, contract_no=contract_no).first():
                    skipped += 1
                    continue

                # 计算状态
                unreceived_amount = contract_amount - received_opened
                unpaid_amount = contract_amount - paid_amount
                settlement_status = "settled" if unreceived_amount <= 0 and unpaid_amount <= 0 else (
                    "partially_settled" if (received_opened > 0 or paid_amount > 0) else "pending"
                )
                processing_status = "completed" if settlement_status == "settled" else "executing"

                contract = Contract(
                    serial_no=project_code,
                    contract_no=contract_no,
                    contract_name=project_name,
                    project_name=project_name,
                    contract_type="imported",
                    sign_date=sign_date,
                    party_a_company_id=party_a.id,
                    party_b_company_id=party_b.id,
                    currency="CNY",
                    contract_amount=contract_amount,
                    invoiced_amount=received_opened,
                    received_amount=received_opened,
                    paid_amount=paid_amount,
                    unreceived_amount=unreceived_amount,
                    unpaid_amount=unpaid_amount,
                    processing_status=processing_status,
                    settlement_status=settlement_status,
                    approval_status="approved",
                    archive_status="unarchived",
                    description=description,
                    created_by=user.id,
                    updated_by=user.id,
                )
                db.session.add(contract)
                db.session.flush()

                if received_opened > 0:
                    db.session.add(ContractInvoice(
                        contract_id=contract.id,
                        invoice_amount=received_opened,
                        invoice_date=sign_date,
                        status='valid',
                        remark='Imported from Excel',
                        created_by=user.id,
                    ))
                    db.session.add(ContractReceipt(
                        contract_id=contract.id,
                        receipt_amount=received_opened,
                        receipt_date=sign_date,
                        receipt_method='Excel import',
                        remark='Imported from Excel',
                        created_by=user.id,
                    ))
                if paid_amount > 0:
                    db.session.add(ContractPayment(
                        contract_id=contract.id,
                        payment_amount=paid_amount,
                        payment_date=sign_date,
                        payment_method='Excel import',
                        remark='Imported from Excel',
                        created_by=user.id,
                    ))
                if acceptance_amount > 0:
                    db.session.add(ContractAcceptance(
                        contract_id=contract.id,
                        acceptance_amount=acceptance_amount,
                        acceptance_date=sign_date,
                        acceptance_note='Imported from Excel',
                        created_by=user.id,
                    ))
                db.session.flush()
                recalculate_contract_summary(contract)

                created_contracts.append(contract.to_dict())

                log_action(user.id, 'contract', 'import', 'contract', contract.id,
                           before_data=None, after_data=contract.to_dict())

                imported += 1

                if imported % 100 == 0:
                    db.session.commit()

            except (ValueError, TypeError) as row_err:
                errors.append(f'第 {excel_row_no} 行数据格式错误：{str(row_err)}')
                continue
            except Exception as row_err:
                errors.append(f'第 {excel_row_no} 行处理失败：{str(row_err)}')
                continue

        db.session.commit()

        error_summary = ''
        if errors:
            error_summary = '；'.join(errors[:10])
            if len(errors) > 10:
                error_summary += f'（共 {len(errors)} 个错误，仅显示前 10 个）'

        return jsonify({
            'message': f'导入完成：成功 {imported} 条，跳过 {skipped} 条' +
                       (f'，{len(errors)} 条错误' if errors else ''),
            'imported_count': imported,
            'skipped_count': skipped,
            'errors': errors,
            'contracts': created_contracts,
        }), 201

    except Exception as e:
        db.session.rollback()
        # 不要把 Python 原始异常直接返回给用户
        error_msg = str(e)
        if 'tuple indices' in error_msg or 'TypeError' in error_msg:
            return jsonify({'message': '导入失败：Excel 表头字段识别失败，请检查模板字段是否正确'}), 400
        if 'NoneType' in error_msg:
            return jsonify({'message': '导入失败：Excel 数据格式不正确，请检查必填字段是否完整'}), 400
        return jsonify({'message': f'导入失败：{error_msg}'}), 400


@contract_bp.get('/contracts/import/template')
@require_permissions('contract:create')
def download_import_template():
    """下载导入模板"""
    from openpyxl import Workbook
    from io import BytesIO

    wb = Workbook()
    ws = wb.active
    ws.title = "台账明细"

    headers = [
        "项目名称", "合同号", "合同金额", "签订日期",
        "乙方单位", "甲方单位", "已收/已开", "已付款金", "验收金额", "备注"
    ]
    example_row = [
        "示例：XX管理系统开发项目", "HT-2026-001", "100000.00", "2026-01-15",
        "示例：乙方科技有限公司", "示例：甲方集团有限公司", "50000.00", "30000.00", "20000.00", "示例备注信息"
    ]

    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.font = cell.font.copy(bold=True)

    for col_idx, val in enumerate(example_row, start=1):
        ws.cell(row=2, column=col_idx, value=val)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name='合同导入模板.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# ==================== 审批流程 API ====================

def _add_approval_history(contract_id, action, operator_id, operator_name,
                          comment=None, from_status=None, to_status=None):
    record = ApprovalHistory(
        contract_id=contract_id,
        action=action,
        operator_id=operator_id,
        operator_name=operator_name,
        comment=comment,
        from_status=from_status,
        to_status=to_status,
    )
    db.session.add(record)


@contract_bp.post('/contracts/<int:contract_id>/approval/submit')
@require_permissions('contract:update')
def submit_approval(contract_id):
    """提交审批：草稿/已驳回 → 审批中"""
    contract, error = get_contract_or_404(contract_id)
    if error:
        return error

    if contract.approval_status not in ('draft', 'rejected'):
        return jsonify({'message': f'当前审批状态为「{contract.approval_status}」，无法提交审批'}), 400

    user = get_current_user()
    old_status = contract.approval_status
    contract.approval_status = 'pending_approval'
    contract.updated_by = user.id

    data = request.get_json(silent=True) or {}
    _add_approval_history(contract.id, 'submit', user.id, user.real_name or user.username,
                          comment=data.get('comment'), from_status=old_status, to_status='pending_approval')
    log_action(user.id, 'approval', 'submit', 'contract', contract.id,
               before_data={'approval_status': old_status},
               after_data={'approval_status': 'pending_approval'})
    db.session.commit()
    _broadcast_contract_update(contract_id, 'approval_submitted', user.real_name or user.username,
                               {'approval_status': 'pending_approval'})
    return jsonify({'message': '已提交审批', 'contract': contract.to_dict()})


@contract_bp.post('/contracts/<int:contract_id>/approval/approve')
@require_permissions('approval:approve')
def approve_contract(contract_id):
    """审批通过：审批中 → 已通过"""
    contract, error = get_contract_or_404(contract_id)
    if error:
        return error

    if contract.approval_status != 'pending_approval':
        return jsonify({'message': f'当前审批状态为「{contract.approval_status}」，无法审批'}), 400

    user = get_current_user()
    old_status = contract.approval_status
    contract.approval_status = 'approved'
    contract.updated_by = user.id

    data = request.get_json(silent=True) or {}
    _add_approval_history(contract.id, 'approve', user.id, user.real_name or user.username,
                          comment=data.get('comment'), from_status=old_status, to_status='approved')
    log_action(user.id, 'approval', 'approve', 'contract', contract.id,
               before_data={'approval_status': old_status},
               after_data={'approval_status': 'approved'})
    db.session.commit()
    _broadcast_contract_update(contract_id, 'approval_approved', user.real_name or user.username,
                               {'approval_status': 'approved'})
    return jsonify({'message': '审批通过', 'contract': contract.to_dict()})


@contract_bp.post('/contracts/<int:contract_id>/approval/reject')
@require_permissions('approval:approve')
def reject_contract(contract_id):
    """审批驳回：审批中 → 已驳回"""
    contract, error = get_contract_or_404(contract_id)
    if error:
        return error

    if contract.approval_status != 'pending_approval':
        return jsonify({'message': f'当前审批状态为「{contract.approval_status}」，无法驳回'}), 400

    user = get_current_user()
    old_status = contract.approval_status
    contract.approval_status = 'rejected'
    contract.updated_by = user.id

    data = request.get_json(silent=True) or {}
    if not data.get('comment'):
        return jsonify({'message': '驳回时必须填写审批意见'}), 400

    _add_approval_history(contract.id, 'reject', user.id, user.real_name or user.username,
                          comment=data.get('comment'), from_status=old_status, to_status='rejected')
    log_action(user.id, 'approval', 'reject', 'contract', contract.id,
               before_data={'approval_status': old_status},
               after_data={'approval_status': 'rejected'})
    db.session.commit()
    _broadcast_contract_update(contract_id, 'approval_rejected', user.real_name or user.username,
                               {'approval_status': 'rejected'})
    return jsonify({'message': '已驳回', 'contract': contract.to_dict()})


@contract_bp.post('/contracts/<int:contract_id>/approval/resubmit')
@require_permissions('contract:update')
def resubmit_approval(contract_id):
    """重新提交审批：已驳回 → 审批中"""
    contract, error = get_contract_or_404(contract_id)
    if error:
        return error

    if contract.approval_status != 'rejected':
        return jsonify({'message': f'当前审批状态为「{contract.approval_status}」，无法重新提交'}), 400

    user = get_current_user()
    old_status = contract.approval_status
    contract.approval_status = 'pending_approval'
    contract.updated_by = user.id

    data = request.get_json(silent=True) or {}
    _add_approval_history(contract.id, 'resubmit', user.id, user.real_name or user.username,
                          comment=data.get('comment'), from_status=old_status, to_status='pending_approval')
    log_action(user.id, 'approval', 'resubmit', 'contract', contract.id,
               before_data={'approval_status': old_status},
               after_data={'approval_status': 'pending_approval'})
    db.session.commit()
    _broadcast_contract_update(contract_id, 'approval_resubmitted', user.real_name or user.username,
                               {'approval_status': 'pending_approval'})
    return jsonify({'message': '已重新提交审批', 'contract': contract.to_dict()})


@contract_bp.get('/contracts/<int:contract_id>/approval/history')
@require_permissions('contract:view')
def get_approval_history(contract_id):
    """获取合同的审批历史"""
    contract, error = get_contract_or_404(contract_id)
    if error:
        return error
    history = ApprovalHistory.query.filter_by(contract_id=contract_id)\
        .order_by(ApprovalHistory.created_at.asc()).all()
    return jsonify({'items': [item.to_dict() for item in history]})
