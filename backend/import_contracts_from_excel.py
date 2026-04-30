"""从用户提供的合同 Excel 批量导入测试数据。

用法：
  1. 把本文件放到 backend 目录。
  2. 激活虚拟环境后执行：
     python import_contracts_from_excel.py --file ../合同软件测试数据.xlsx --sheet 台账明细

说明：
  - 数据库字段仍然使用 serial_no，但界面已统一显示为“项目号”。
  - 对于缺失的合同号，本脚本会自动生成占位合同号，避免导入失败。
  - 默认会创建缺失的甲乙方单位。
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from openpyxl import load_workbook

from app import create_app
from app.extensions import db
from app.models.contract import Contract, Company
from app.models.user import User


AUTO_CONTRACT_PREFIX = "AUTO-HT"
AUTO_PROJECT_PREFIX = "XM"


def parse_decimal(value) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value).strip())
    except Exception:
        return Decimal("0")


def parse_date(value) -> Optional[datetime.date]:
    if value in (None, ""):
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
    return None


def ensure_company(name: str) -> Optional[Company]:
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


def unique_contract_no(raw_contract_no: str, row_index: int) -> str:
    base = (raw_contract_no or "").strip()
    if not base:
        base = f"{AUTO_CONTRACT_PREFIX}-{row_index:04d}"
    candidate = base
    suffix = 1
    while Contract.query.filter_by(contract_no=candidate).first():
        suffix += 1
        candidate = f"{base}-{suffix}"
    return candidate


def unique_project_code(row_index: int) -> str:
    candidate = f"{AUTO_PROJECT_PREFIX}-{row_index:04d}"
    suffix = 1
    while Contract.query.filter_by(serial_no=candidate).first():
        suffix += 1
        candidate = f"{AUTO_PROJECT_PREFIX}-{row_index:04d}-{suffix}"
    return candidate


def import_sheet(file_path: Path, sheet_name: str):
    wb = load_workbook(file_path, data_only=True)
    ws = wb[sheet_name]

    headers = [str(c.value).strip() if c.value is not None else "" for c in ws[1]]
    header_map = {name: idx for idx, name in enumerate(headers)}

    created_by = User.query.filter_by(username="admin").first()
    created_by_id = created_by.id if created_by else None

    imported = 0
    skipped = 0

    for excel_row_no, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        project_name = (str(row[header_map.get("项目名称", 1)]).strip() if row[header_map.get("项目名称", 1)] is not None else "")
        if not project_name:
            skipped += 1
            continue

        party_b_name = str(row[header_map.get("乙方单位", 5)] or "").strip()
        party_a_name = str(row[header_map.get("甲方单位", 6)] or "").strip()
        party_a = ensure_company(party_a_name or "未命名甲方")
        party_b = ensure_company(party_b_name or "未命名乙方")

        contract_amount = parse_decimal(row[header_map.get("合同金额", 3)])
        received_amount = parse_decimal(row[header_map.get("已收/已开票金额", 7)])

        payment_key = "已收付款金额" if "已收付款金额" in header_map else "已付款金额"
        paid_amount = parse_decimal(row[header_map.get(payment_key, 10)])

        acceptance_amount = parse_decimal(row[header_map.get("验收金额", 13)])
        note_key = headers[-1] if headers and headers[-1] else None
        description = str(row[header_map[note_key]]) if note_key and row[header_map[note_key]] is not None else None

        project_code = unique_project_code(excel_row_no - 1)
        contract_no = unique_contract_no(str(row[header_map.get("合同号", 2)] or ""), excel_row_no - 1)

        # 避免同一项目名称 + 同一合同号重复导入
        if Contract.query.filter_by(project_name=project_name, contract_no=contract_no).first():
            skipped += 1
            continue

        unreceived_amount = contract_amount - received_amount
        unpaid_amount = contract_amount - paid_amount
        settlement_status = "settled" if unreceived_amount <= 0 and unpaid_amount <= 0 else (
            "partially_settled" if (received_amount > 0 or paid_amount > 0) else "pending"
        )
        processing_status = "completed" if settlement_status == "settled" else "executing"

        contract = Contract(
            serial_no=project_code,
            contract_no=contract_no,
            contract_name=project_name,
            project_name=project_name,
            contract_type="imported",
            sign_date=parse_date(row[header_map.get("签订日期", 4)]),
            party_a_company_id=party_a.id,
            party_b_company_id=party_b.id,
            currency="CNY",
            contract_amount=contract_amount,
            invoiced_amount=received_amount,
            received_amount=received_amount,
            paid_amount=paid_amount,
            unreceived_amount=unreceived_amount,
            unpaid_amount=unpaid_amount,
            processing_status=processing_status,
            settlement_status=settlement_status,
            approval_status="approved",
            archive_status="unarchived",
            description=description,
            created_by=created_by_id,
            updated_by=created_by_id,
        )
        db.session.add(contract)
        imported += 1

        # 每 100 条提交一次，避免大文件导入占内存太久
        if imported % 100 == 0:
            db.session.commit()
            print(f"已导入 {imported} 条...")

    db.session.commit()
    print(f"导入完成：成功 {imported} 条，跳过 {skipped} 条")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Excel 文件路径")
    parser.add_argument("--sheet", default="台账明细", help="工作表名称，默认 台账明细")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        import_sheet(Path(args.file), args.sheet)


if __name__ == "__main__":
    main()
