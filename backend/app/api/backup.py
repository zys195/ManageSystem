import json
import shutil
import zipfile
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file
from sqlalchemy import Date, DateTime, Numeric, text

from app.extensions import db
from app.utils.permissions import get_current_user, require_permissions

backup_bp = Blueprint('backup', __name__, url_prefix='/api/system/backup')

BACKUP_FORMAT_VERSION = 1


def _json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _parse_value(column, value):
    if value is None:
        return None
    if isinstance(column.type, DateTime):
        return datetime.fromisoformat(value)
    if isinstance(column.type, Date):
        return date.fromisoformat(value)
    if isinstance(column.type, Numeric):
        return Decimal(str(value))
    return value


def _table_rows(table):
    rows = db.session.execute(table.select()).mappings().all()
    return [
        {column.name: _json_value(row[column.name]) for column in table.columns}
        for row in rows
    ]


def _backup_tables():
    return db.metadata.sorted_tables


def _uploads_dir():
    return Path(current_app.config['UPLOAD_DIR']).resolve()


def _write_uploads_to_zip(zip_file, upload_dir):
    if not upload_dir.exists():
        return 0

    count = 0
    for path in upload_dir.rglob('*'):
        if path.is_file():
            zip_file.write(path, f'uploads/{path.relative_to(upload_dir).as_posix()}')
            count += 1
    return count


def _restore_uploads_from_zip(zip_file, upload_dir):
    upload_members = [
        member for member in zip_file.infolist()
        if not member.is_dir() and member.filename.startswith('uploads/')
    ]

    temp_upload_dir = upload_dir.parent / f'.restore_uploads_{datetime.utcnow().strftime("%Y%m%d%H%M%S%f")}'
    if temp_upload_dir.exists():
        shutil.rmtree(temp_upload_dir)
    temp_upload_dir.mkdir(parents=True, exist_ok=True)

    try:
        for member in upload_members:
            relative = Path(member.filename).relative_to('uploads')
            target = (temp_upload_dir / relative).resolve()
            if temp_upload_dir not in target.parents and target != temp_upload_dir:
                raise ValueError('备份包中的附件路径不安全')
            target.parent.mkdir(parents=True, exist_ok=True)
            with zip_file.open(member) as source, target.open('wb') as dest:
                shutil.copyfileobj(source, dest)

        if upload_dir.exists():
            shutil.rmtree(upload_dir)
        temp_upload_dir.replace(upload_dir)
    except Exception:
        if temp_upload_dir.exists():
            shutil.rmtree(temp_upload_dir)
        raise

    return len(upload_members)


def _reset_sequences():
    dialect = db.session.bind.dialect.name
    for table in _backup_tables():
        pk_columns = list(table.primary_key.columns)
        if len(pk_columns) != 1:
            continue
        pk = pk_columns[0]
        if not getattr(pk, 'autoincrement', False):
            continue

        max_id = db.session.execute(
            text(f'SELECT COALESCE(MAX({pk.name}), 0) FROM {table.name}')
        ).scalar() or 0

        if dialect == 'postgresql':
            db.session.execute(
                text("SELECT setval(pg_get_serial_sequence(:table_name, :column_name), :next_value, false)"),
                {
                    'table_name': table.name,
                    'column_name': pk.name,
                    'next_value': int(max_id) + 1,
                },
            )
        elif dialect == 'sqlite':
            db.session.execute(
                text("UPDATE sqlite_sequence SET seq = :seq WHERE name = :table_name"),
                {'seq': int(max_id), 'table_name': table.name},
            )


@backup_bp.get('/info')
@require_permissions('backup:manage')
def backup_info():
    tables = _backup_tables()
    table_counts = {
        table.name: db.session.execute(text(f'SELECT COUNT(*) FROM {table.name}')).scalar()
        for table in tables
    }
    upload_dir = _uploads_dir()
    upload_files = list(upload_dir.rglob('*')) if upload_dir.exists() else []
    upload_size = sum(path.stat().st_size for path in upload_files if path.is_file())
    return jsonify({
        'database_uri': current_app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1],
        'table_count': len(tables),
        'row_count': sum(table_counts.values()),
        'table_counts': table_counts,
        'upload_file_count': sum(1 for path in upload_files if path.is_file()),
        'upload_size': upload_size,
        'format_version': BACKUP_FORMAT_VERSION,
    })


@backup_bp.get('/export')
@require_permissions('backup:manage')
def export_backup():
    user = get_current_user()
    now = datetime.utcnow()
    buffer = BytesIO()
    upload_dir = _uploads_dir()

    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
        tables = _backup_tables()
        manifest = {
            'format_version': BACKUP_FORMAT_VERSION,
            'created_at': now.isoformat(),
            'created_by': user.username if user else None,
            'database': current_app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1],
            'tables': [table.name for table in tables],
        }

        for table in tables:
            rows = _table_rows(table)
            zip_file.writestr(
                f'data/{table.name}.json',
                json.dumps(rows, ensure_ascii=False, indent=2),
            )

        upload_count = _write_uploads_to_zip(zip_file, upload_dir)
        manifest['upload_file_count'] = upload_count
        zip_file.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))

    buffer.seek(0)
    filename = f"system_backup_{now.strftime('%Y%m%d_%H%M%S')}.zip"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/zip')


@backup_bp.post('/restore')
@require_permissions('backup:manage')
def restore_backup():
    file_obj = request.files.get('file')
    if not file_obj:
        return jsonify({'message': '请选择备份 ZIP 文件'}), 400
    if not (file_obj.filename or '').lower().endswith('.zip'):
        return jsonify({'message': '仅支持本系统导出的 ZIP 备份包'}), 400

    try:
        backup_bytes = BytesIO(file_obj.read())
        with zipfile.ZipFile(backup_bytes, 'r') as zip_file:
            if 'manifest.json' not in zip_file.namelist():
                return jsonify({'message': '备份包缺少 manifest.json'}), 400
            manifest = json.loads(zip_file.read('manifest.json').decode('utf-8'))
            if manifest.get('format_version') != BACKUP_FORMAT_VERSION:
                return jsonify({'message': '备份包版本不兼容'}), 400

            tables = _backup_tables()
            table_map = {table.name: table for table in tables}
            missing_files = [table.name for table in tables if f'data/{table.name}.json' not in zip_file.namelist()]
            if missing_files:
                return jsonify({'message': f'备份包缺少数据表：{", ".join(missing_files)}'}), 400

            for table in reversed(tables):
                db.session.execute(table.delete())
            db.session.flush()

            restored_rows = 0
            for table in tables:
                raw_rows = json.loads(zip_file.read(f'data/{table.name}.json').decode('utf-8'))
                if not raw_rows:
                    continue
                parsed_rows = []
                for row in raw_rows:
                    parsed_rows.append({
                        column.name: _parse_value(column, row.get(column.name))
                        for column in table.columns
                    })
                db.session.execute(table.insert(), parsed_rows)
                restored_rows += len(parsed_rows)

            _reset_sequences()
            restored_files = _restore_uploads_from_zip(zip_file, _uploads_dir())
            db.session.commit()

        return jsonify({
            'message': '备份恢复完成',
            'restored_rows': restored_rows,
            'restored_files': restored_files,
            'created_at': manifest.get('created_at'),
        })
    except zipfile.BadZipFile:
        db.session.rollback()
        return jsonify({'message': '备份文件不是有效的 ZIP 包'}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({'message': f'恢复失败：{str(exc)}'}), 400
