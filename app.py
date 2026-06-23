import os
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)

SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
API_KEY = os.getenv('SHEETS_API_KEY')
SHEETS = ['Ратчин', 'ЧСА', 'ЕОГ', 'ДАА']

COLUMNS = ['ШК', 'Товар', 'Арт ВБ', 'Размер', 'Количество', 'Номер короба', 'Дата']


def sheets_url(sheet, range_='A:G'):
    name = requests.utils.quote(sheet)
    return f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{name}!{range_}?key={API_KEY}'


GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')

@app.route('/')
def index():
    return render_template('index.html', sheets=SHEETS, google_client_id=GOOGLE_CLIENT_ID)


@app.route('/api/rows/<sheet>')
def get_rows(sheet):
    if sheet not in SHEETS:
        return jsonify({'error': 'Unknown sheet'}), 400
    try:
        resp = requests.get(sheets_url(sheet))
        resp.raise_for_status()
        values = resp.json().get('values', [])
        rows = []
        for i, row in enumerate(values):
            while len(row) < 7:
                row.append('')
            rows.append({
                'rowNumber': i + 1,
                'shk': row[0],
                'tovar': row[1],
                'artVB': row[2],
                'razmer': row[3],
                'kolichestvo': row[4],
                'nomerKoroba': row[5],
                'data': row[6],
            })
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rows/<sheet>', methods=['POST'])
def add_row(sheet):
    if sheet not in SHEETS:
        return jsonify({'error': 'Unknown sheet'}), 400
    data = request.json
    values = [[
        data.get('shk', ''),
        data.get('tovar', ''),
        data.get('artVB', ''),
        data.get('razmer', ''),
        data.get('kolichestvo', ''),
        data.get('nomerKoroba', ''),
        data.get('data', datetime.today().strftime('%d.%m.%Y')),
    ]]
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    name = requests.utils.quote(sheet)
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{name}!A:G:append?valueInputOption=USER_ENTERED'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    resp = requests.post(url, json={'values': values}, headers=headers)
    if not resp.ok:
        return jsonify({'error': resp.text}), resp.status_code
    return jsonify({'ok': True})


@app.route('/api/rows/<sheet>/<int:row_number>', methods=['PUT'])
def update_row(sheet, row_number):
    if sheet not in SHEETS:
        return jsonify({'error': 'Unknown sheet'}), 400
    data = request.json
    values = [[
        data.get('shk', ''),
        data.get('tovar', ''),
        data.get('artVB', ''),
        data.get('razmer', ''),
        data.get('kolichestvo', ''),
        data.get('nomerKoroba', ''),
        data.get('data', ''),
    ]]
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    name = requests.utils.quote(sheet)
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{name}!A{row_number}:G{row_number}?valueInputOption=USER_ENTERED'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    resp = requests.put(url, json={'values': values}, headers=headers)
    if not resp.ok:
        return jsonify({'error': resp.text}), resp.status_code
    return jsonify({'ok': True})


@app.route('/api/rows/<sheet>/<int:row_number>', methods=['DELETE'])
def delete_row(sheet, row_number):
    if sheet not in SHEETS:
        return jsonify({'error': 'Unknown sheet'}), 400
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    # Get sheet id
    meta_url = f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?key={API_KEY}'
    meta = requests.get(meta_url).json()
    sheet_id = None
    for s in meta.get('sheets', []):
        if s['properties']['title'] == sheet:
            sheet_id = s['properties']['sheetId']
            break
    if sheet_id is None:
        return jsonify({'error': 'Sheet not found'}), 404

    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    body = {'requests': [{'deleteDimension': {'range': {
        'sheetId': sheet_id,
        'dimension': 'ROWS',
        'startIndex': row_number - 1,
        'endIndex': row_number,
    }}}]}
    resp = requests.post(url, json=body, headers=headers)
    if not resp.ok:
        return jsonify({'error': resp.text}), resp.status_code
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
