import os
import io
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
from datetime import datetime
import psycopg2
import psycopg2.extras
from openpyxl import Workbook

load_dotenv()

app = Flask(__name__)

DEFAULT_SHEETS = ['Ратчин', 'ЧСА', 'ЕОГ', 'ДАА']


def get_db():
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise RuntimeError('DATABASE_URL is not set')
    return psycopg2.connect(url)


def db_execute(sql, params=(), fetch=None):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch == 'all':
                result = [dict(r) for r in cur.fetchall()]
            elif fetch == 'one':
                row = cur.fetchone()
                result = dict(row) if row else None
            else:
                result = None
        conn.commit()
        return result
    finally:
        conn.close()


def db_transaction(queries):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            for sql, params in queries:
                cur.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def init_db():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS sheets (
                    name TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'active'
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS rows (
                    id SERIAL PRIMARY KEY,
                    sheet_name TEXT NOT NULL,
                    shk TEXT,
                    kolichestvo TEXT,
                    nomer_koroba TEXT,
                    data TEXT
                )
            ''')
            for name in DEFAULT_SHEETS:
                cur.execute(
                    'INSERT INTO sheets (name, status) VALUES (%s, %s) ON CONFLICT DO NOTHING',
                    (name, 'active')
                )
        conn.commit()
    finally:
        conn.close()


def load_config():
    rows = db_execute('SELECT name, status FROM sheets ORDER BY name', fetch='all')
    active = [r['name'] for r in rows if r['status'] == 'active']
    deleted = [r['name'] for r in rows if r['status'] == 'deleted']
    return {'active': active, 'deleted': deleted}


# ---- Pages ----

@app.route('/')
def index():
    sheets = load_config()['active']
    return render_template('index.html', sheets=sheets)


@app.route('/admin')
def admin():
    config = load_config()
    return render_template('admin.html', config=config)


# ---- Rows API ----

@app.route('/api/rows/<sheet>')
def get_rows(sheet):
    if sheet not in load_config()['active']:
        return jsonify({'error': 'Unknown sheet'}), 400
    rows = db_execute(
        'SELECT id, shk, kolichestvo, nomer_koroba, data FROM rows WHERE sheet_name=%s ORDER BY id',
        (sheet,), fetch='all'
    )
    result = [{
        'id': r['id'],
        'shk': r['shk'] or '',
        'kolichestvo': r['kolichestvo'] or '',
        'nomerKoroba': r['nomer_koroba'] or '',
        'data': r['data'] or '',
    } for r in rows]
    return jsonify(result)


@app.route('/api/rows/<sheet>', methods=['POST'])
def add_row(sheet):
    if sheet not in load_config()['active']:
        return jsonify({'error': 'Unknown sheet'}), 400
    data = request.json
    db_execute(
        'INSERT INTO rows (sheet_name, shk, kolichestvo, nomer_koroba, data) VALUES (%s, %s, %s, %s, %s)',
        (sheet, data.get('shk', ''), str(data.get('kolichestvo', '')),
         str(data.get('nomerKoroba', '')),
         data.get('data', datetime.today().strftime('%d.%m.%Y %H:%M')))
    )
    return jsonify({'ok': True})


@app.route('/api/rows/<sheet>/<int:row_id>', methods=['PUT'])
def update_row(sheet, row_id):
    if sheet not in load_config()['active']:
        return jsonify({'error': 'Unknown sheet'}), 400
    data = request.json
    db_execute(
        'UPDATE rows SET shk=%s, kolichestvo=%s, nomer_koroba=%s, data=%s WHERE id=%s AND sheet_name=%s',
        (data.get('shk', ''), str(data.get('kolichestvo', '')),
         str(data.get('nomerKoroba', '')),
         data.get('data', datetime.today().strftime('%d.%m.%Y %H:%M')),
         row_id, sheet)
    )
    return jsonify({'ok': True})


@app.route('/api/rows/<sheet>/<int:row_id>', methods=['DELETE'])
def delete_row(sheet, row_id):
    if sheet not in load_config()['active']:
        return jsonify({'error': 'Unknown sheet'}), 400
    db_execute('DELETE FROM rows WHERE id=%s AND sheet_name=%s', (row_id, sheet))
    return jsonify({'ok': True})


# ---- Export ----

@app.route('/api/export/<sheet>')
def export_sheet(sheet):
    if sheet not in load_config()['active']:
        return jsonify({'error': 'Unknown sheet'}), 400
    rows = db_execute(
        'SELECT shk, kolichestvo, nomer_koroba, data FROM rows WHERE sheet_name=%s ORDER BY id',
        (sheet,), fetch='all'
    )
    wb = Workbook()
    ws = wb.active
    ws.title = sheet[:31]  # Excel tab name limit
    ws.append(['ШК', 'Количество', 'Номер короба', 'Дата'])
    for r in rows:
        ws.append([r['shk'], r['kolichestvo'], r['nomer_koroba'], r['data']])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'{sheet}.xlsx'
    )


# ---- Admin: Sheet management ----

@app.route('/api/admin/sheets', methods=['GET'])
def admin_get_sheets():
    return jsonify(load_config())


@app.route('/api/admin/sheets', methods=['POST'])
def admin_add_sheet():
    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Имя не указано'}), 400
    config = load_config()
    if name in config['active']:
        return jsonify({'error': 'Лист уже существует'}), 400
    if name in config['deleted']:
        return jsonify({'error': 'Лист удалён — используйте восстановление'}), 400
    db_execute('INSERT INTO sheets (name, status) VALUES (%s, %s)', (name, 'active'))
    config['active'].append(name)
    return jsonify({'ok': True, 'config': config})


@app.route('/api/admin/sheets/rename', methods=['PUT'])
def admin_rename_sheet():
    data = request.json
    old_name = data.get('old_name', '').strip()
    new_name = data.get('new_name', '').strip()
    if not old_name or not new_name:
        return jsonify({'error': 'Имя не указано'}), 400
    config = load_config()
    if old_name not in config['active']:
        return jsonify({'error': 'Лист не найден'}), 404
    if new_name in config['active']:
        return jsonify({'error': 'Имя уже занято'}), 400
    db_transaction([
        ('UPDATE sheets SET name=%s WHERE name=%s', (new_name, old_name)),
        ('UPDATE rows SET sheet_name=%s WHERE sheet_name=%s', (new_name, old_name)),
    ])
    idx = config['active'].index(old_name)
    config['active'][idx] = new_name
    return jsonify({'ok': True, 'config': config})


@app.route('/api/admin/sheets/delete', methods=['POST'])
def admin_delete_sheet():
    name = request.json.get('name', '').strip()
    config = load_config()
    if name not in config['active']:
        return jsonify({'error': 'Лист не найден'}), 404
    db_execute('UPDATE sheets SET status=%s WHERE name=%s', ('deleted', name))
    config['active'].remove(name)
    config['deleted'].append(name)
    return jsonify({'ok': True, 'config': config})


@app.route('/api/admin/sheets/restore', methods=['POST'])
def admin_restore_sheet():
    name = request.json.get('name', '').strip()
    config = load_config()
    if name not in config['deleted']:
        return jsonify({'error': 'Лист не найден в удалённых'}), 404
    db_execute('UPDATE sheets SET status=%s WHERE name=%s', ('active', name))
    config['deleted'].remove(name)
    config['active'].append(name)
    return jsonify({'ok': True, 'config': config})


try:
    with app.app_context():
        init_db()
except Exception as e:
    print(f'DB init failed: {e}')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
