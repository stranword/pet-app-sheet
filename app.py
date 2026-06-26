import os
import json
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)

SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
API_KEY = os.getenv('SHEETS_API_KEY')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'sheets_config.json')
DEFAULT_SHEETS = ['Ратчин', 'ЧСА', 'ЕОГ', 'ДАА']

# ---- Service account (for anonymous row CRUD) ----
try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as GoogleRequest
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False

_sa_creds = None

def get_server_token():
    global _sa_creds
    if not HAS_GOOGLE_AUTH:
        return None
    sa_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    if not sa_json:
        return None
    try:
        sa_info = json.loads(sa_json)
        if _sa_creds is None:
            _sa_creds = service_account.Credentials.from_service_account_info(
                sa_info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        if not _sa_creds.valid:
            _sa_creds.refresh(GoogleRequest())
        return _sa_creds.token
    except Exception as e:
        print(f'Service account error: {e}')
        _sa_creds = None
        return None

def server_headers():
    token = get_server_token()
    if not token:
        return None
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

def user_headers(req):
    token = req.headers.get('Authorization', '').replace('Bearer ', '')
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# ---- Config ----

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'active': list(DEFAULT_SHEETS), 'deleted': []}

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# ---- Helpers ----

def _google_error(resp):
    try:
        return resp.json()['error']['message']
    except Exception:
        return resp.text

def sheets_url(sheet, range_='A:G'):
    name = requests.utils.quote(sheet)
    return f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{name}!{range_}?key={API_KEY}'

def get_sheet_id(sheet_name, hdrs):
    meta_url = f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}'
    meta = requests.get(meta_url, headers=hdrs).json()
    for s in meta.get('sheets', []):
        if s['properties']['title'] == sheet_name:
            return s['properties']['sheetId']
    return None

# ---- Pages ----

@app.route('/')
def index():
    sheets = load_config()['active']
    return render_template('index.html', sheets=sheets)

@app.route('/admin')
def admin():
    config = load_config()
    return render_template('admin.html', config=config, google_client_id=GOOGLE_CLIENT_ID)

# ---- Rows API (uses service account — no user auth needed) ----

@app.route('/api/rows/<sheet>')
def get_rows(sheet):
    if sheet not in load_config()['active']:
        return jsonify({'error': 'Unknown sheet'}), 400
    hdrs = server_headers()
    if not hdrs:
        return jsonify({'error': 'Не настроен GOOGLE_SERVICE_ACCOUNT_JSON'}), 503
    try:
        name = requests.utils.quote(sheet)
        url = f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{name}!A:G'
        resp = requests.get(url, headers=hdrs)
        if not resp.ok:
            return jsonify({'error': _google_error(resp)}), resp.status_code
        values = resp.json().get('values', [])
        rows = []
        for i, row in enumerate(values):
            while len(row) < 7:
                row.append('')
            rows.append({
                'rowNumber': i + 1,
                'shk': row[0],
                'artVB': row[2],
                'kolichestvo': row[4],
                'nomerKoroba': row[5],
                'data': row[6],
            })
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rows/<sheet>', methods=['POST'])
def add_row(sheet):
    if sheet not in load_config()['active']:
        return jsonify({'error': 'Unknown sheet'}), 400
    hdrs = server_headers()
    if not hdrs:
        return jsonify({'error': 'Не настроен GOOGLE_SERVICE_ACCOUNT_JSON'}), 503
    data = request.json
    values = [[
        data.get('shk', ''),
        '',
        data.get('artVB', ''),
        '',
        data.get('kolichestvo', ''),
        data.get('nomerKoroba', ''),
        data.get('data', datetime.today().strftime('%d.%m.%Y %H:%M')),
    ]]
    name = requests.utils.quote(sheet)
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{name}!A:G:append?valueInputOption=USER_ENTERED'
    resp = requests.post(url, json={'values': values}, headers=hdrs)
    if not resp.ok:
        return jsonify({'error': _google_error(resp)}), resp.status_code
    return jsonify({'ok': True})


@app.route('/api/rows/<sheet>/<int:row_number>', methods=['PUT'])
def update_row(sheet, row_number):
    if sheet not in load_config()['active']:
        return jsonify({'error': 'Unknown sheet'}), 400
    hdrs = server_headers()
    if not hdrs:
        return jsonify({'error': 'Не настроен GOOGLE_SERVICE_ACCOUNT_JSON'}), 503
    data = request.json
    values = [[
        data.get('shk', ''),
        '',
        data.get('artVB', ''),
        '',
        data.get('kolichestvo', ''),
        data.get('nomerKoroba', ''),
        data.get('data', ''),
    ]]
    name = requests.utils.quote(sheet)
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{name}!A{row_number}:G{row_number}?valueInputOption=USER_ENTERED'
    resp = requests.put(url, json={'values': values}, headers=hdrs)
    if not resp.ok:
        return jsonify({'error': _google_error(resp)}), resp.status_code
    return jsonify({'ok': True})


@app.route('/api/rows/<sheet>/<int:row_number>', methods=['DELETE'])
def delete_row(sheet, row_number):
    if sheet not in load_config()['active']:
        return jsonify({'error': 'Unknown sheet'}), 400
    hdrs = server_headers()
    if not hdrs:
        return jsonify({'error': 'Не настроен GOOGLE_SERVICE_ACCOUNT_JSON'}), 503
    sheet_id = get_sheet_id(sheet, hdrs)
    if sheet_id is None:
        return jsonify({'error': 'Sheet not found'}), 404
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate'
    body = {'requests': [{'deleteDimension': {'range': {
        'sheetId': sheet_id,
        'dimension': 'ROWS',
        'startIndex': row_number - 1,
        'endIndex': row_number,
    }}}]}
    resp = requests.post(url, json=body, headers=hdrs)
    if not resp.ok:
        return jsonify({'error': _google_error(resp)}), resp.status_code
    return jsonify({'ok': True})


# ---- Admin: Sheet management (uses user OAuth token) ----

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
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate'
    body = {'requests': [{'addSheet': {'properties': {'title': name}}}]}
    resp = requests.post(url, json=body, headers=user_headers(request))
    if not resp.ok:
        return jsonify({'error': _google_error(resp)}), resp.status_code
    config['active'].append(name)
    save_config(config)
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
    sheet_id = get_sheet_id(old_name, user_headers(request))
    if sheet_id is None:
        return jsonify({'error': 'Лист не найден в Google Sheets'}), 404
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate'
    body = {'requests': [{'updateSheetProperties': {
        'properties': {'sheetId': sheet_id, 'title': new_name},
        'fields': 'title'
    }}]}
    resp = requests.post(url, json=body, headers=user_headers(request))
    if not resp.ok:
        return jsonify({'error': _google_error(resp)}), resp.status_code
    idx = config['active'].index(old_name)
    config['active'][idx] = new_name
    save_config(config)
    return jsonify({'ok': True, 'config': config})


@app.route('/api/admin/sheets/delete', methods=['POST'])
def admin_delete_sheet():
    name = request.json.get('name', '').strip()
    config = load_config()
    if name not in config['active']:
        return jsonify({'error': 'Лист не найден'}), 404
    config['active'].remove(name)
    config['deleted'].append(name)
    save_config(config)
    return jsonify({'ok': True, 'config': config})


@app.route('/api/admin/sheets/restore', methods=['POST'])
def admin_restore_sheet():
    name = request.json.get('name', '').strip()
    config = load_config()
    if name not in config['deleted']:
        return jsonify({'error': 'Лист не найден в удалённых'}), 404
    config['deleted'].remove(name)
    config['active'].append(name)
    save_config(config)
    return jsonify({'ok': True, 'config': config})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
