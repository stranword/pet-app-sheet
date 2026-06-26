import json
import os
import pytest
from unittest.mock import patch, MagicMock

os.environ.setdefault('SPREADSHEET_ID', 'test-spreadsheet-id')
os.environ.setdefault('SHEETS_API_KEY', 'test-api-key')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'test-client-id')

import app as flask_app

DEFAULT_CONFIG = {'active': ['Ратчин', 'ЧСА'], 'deleted': ['ДАА']}

ROWS_RESPONSE = {
    'values': [
        ['SHK001', '', 'ART001', '', '5', '3', '01.01.2024 10:00'],
        ['SHK002', '', 'ART002', '', '2', '1', '02.01.2024 11:00'],
    ]
}

SHEETS_META = {
    'sheets': [
        {'properties': {'title': 'Ратчин', 'sheetId': 42}},
        {'properties': {'title': 'ЧСА', 'sheetId': 43}},
    ]
}


@pytest.fixture
def config_path(tmp_path):
    path = tmp_path / 'sheets_config.json'
    path.write_text(json.dumps(DEFAULT_CONFIG), encoding='utf-8')
    return str(path)


@pytest.fixture(autouse=True)
def patch_config(config_path):
    with patch('app.CONFIG_FILE', config_path):
        yield


@pytest.fixture
def client():
    flask_app.app.config['TESTING'] = True
    with flask_app.app.test_client() as c:
        yield c


@pytest.fixture
def server_token():
    with patch('app.get_server_token', return_value='fake-server-token'):
        yield


def mock_get(json_data):
    m = MagicMock()
    m.json.return_value = json_data
    m.raise_for_status = MagicMock()
    m.ok = True
    return m


def mock_post(ok=True, text='', status_code=None):
    m = MagicMock()
    m.ok = ok
    m.text = text
    m.status_code = status_code if status_code is not None else (200 if ok else 400)
    return m


# ---- Page routes ----

def test_index_renders(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert 'Ратчин'.encode() in resp.data
    assert 'ЧСА'.encode() in resp.data


def test_admin_renders(client):
    resp = client.get('/admin')
    assert resp.status_code == 200
    assert 'Ратчин'.encode() in resp.data
    assert 'ДАА'.encode() in resp.data  # deleted sheet is shown


# ---- GET /api/rows/<sheet> ----

def test_get_rows_success(client, server_token):
    with patch('app.requests.get', return_value=mock_get(ROWS_RESPONSE)):
        resp = client.get('/api/rows/Ратчин')
    assert resp.status_code == 200
    rows = resp.get_json()
    assert len(rows) == 2
    assert rows[0] == {
        'rowNumber': 1, 'shk': 'SHK001', 'artVB': 'ART001',
        'kolichestvo': '5', 'nomerKoroba': '3', 'data': '01.01.2024 10:00',
    }


def test_get_rows_pads_short_rows(client, server_token):
    short = {'values': [['SHK001']]}  # only 1 column
    with patch('app.requests.get', return_value=mock_get(short)):
        resp = client.get('/api/rows/Ратчин')
    assert resp.status_code == 200
    row = resp.get_json()[0]
    assert row['artVB'] == ''
    assert row['kolichestvo'] == ''


def test_get_rows_unknown_sheet(client):
    resp = client.get('/api/rows/Неизвестный')
    assert resp.status_code == 400


def test_get_rows_no_service_account(client):
    with patch('app.get_server_token', return_value=None):
        resp = client.get('/api/rows/Ратчин')
    assert resp.status_code == 503


def test_get_rows_empty_sheet(client, server_token):
    with patch('app.requests.get', return_value=mock_get({'values': []})):
        resp = client.get('/api/rows/Ратчин')
    assert resp.status_code == 200
    assert resp.get_json() == []


# ---- POST /api/rows/<sheet> ----

def test_add_row_success(client, server_token):
    with patch('app.requests.post', return_value=mock_post(ok=True)):
        resp = client.post('/api/rows/Ратчин', json={
            'shk': 'SHK999', 'artVB': 'ART999', 'kolichestvo': 3, 'nomerKoroba': 2,
        })
    assert resp.status_code == 200
    assert resp.get_json()['ok'] is True


def test_add_row_no_service_account(client):
    with patch('app.get_server_token', return_value=None):
        resp = client.post('/api/rows/Ратчин', json={'shk': 'X'})
    assert resp.status_code == 503


def test_add_row_unknown_sheet(client, server_token):
    resp = client.post('/api/rows/Неизвестный', json={'shk': 'X'})
    assert resp.status_code == 400


def test_add_row_sheets_api_error(client, server_token):
    with patch('app.requests.post', return_value=mock_post(ok=False, text='API error')):
        resp = client.post('/api/rows/Ратчин', json={'shk': 'X'})
    assert not resp.get_json().get('ok')


# ---- PUT /api/rows/<sheet>/<row_number> ----

def test_update_row_success(client, server_token):
    with patch('app.requests.put', return_value=mock_post(ok=True)):
        resp = client.put('/api/rows/Ратчин/1', json={
            'shk': 'SHK001', 'artVB': 'ART001',
            'kolichestvo': 10, 'nomerKoroba': 1, 'data': '01.01.2024 10:00',
        })
    assert resp.status_code == 200
    assert resp.get_json()['ok'] is True


def test_update_row_unknown_sheet(client, server_token):
    resp = client.put('/api/rows/Неизвестный/1', json={})
    assert resp.status_code == 400


# ---- DELETE /api/rows/<sheet>/<row_number> ----

def test_delete_row_success(client, server_token):
    with patch('app.requests.get', return_value=mock_get(SHEETS_META)), \
         patch('app.requests.post', return_value=mock_post(ok=True)):
        resp = client.delete('/api/rows/Ратчин/1')
    assert resp.status_code == 200
    assert resp.get_json()['ok'] is True


def test_delete_row_sheet_not_in_meta(client, server_token):
    with patch('app.requests.get', return_value=mock_get({'sheets': []})):
        resp = client.delete('/api/rows/Ратчин/1')
    assert resp.status_code == 404


def test_delete_row_unknown_sheet(client, server_token):
    resp = client.delete('/api/rows/Неизвестный/1')
    assert resp.status_code == 400


# ---- GET /api/admin/sheets ----

def test_admin_get_sheets(client):
    resp = client.get('/api/admin/sheets')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['active'] == ['Ратчин', 'ЧСА']
    assert data['deleted'] == ['ДАА']


# ---- POST /api/admin/sheets ----

def test_admin_add_sheet(client):
    with patch('app.requests.post', return_value=mock_post(ok=True)):
        resp = client.post('/api/admin/sheets',
                           json={'name': 'НовыйЛист'},
                           headers={'Authorization': 'Bearer user-token'})
    assert resp.status_code == 200
    config = resp.get_json()['config']
    assert 'НовыйЛист' in config['active']


def test_admin_add_sheet_duplicate(client):
    resp = client.post('/api/admin/sheets',
                       json={'name': 'Ратчин'},
                       headers={'Authorization': 'Bearer user-token'})
    assert resp.status_code == 400


def test_admin_add_sheet_empty_name(client):
    resp = client.post('/api/admin/sheets',
                       json={'name': '  '},
                       headers={'Authorization': 'Bearer user-token'})
    assert resp.status_code == 400


def test_admin_add_deleted_sheet_rejected(client):
    resp = client.post('/api/admin/sheets',
                       json={'name': 'ДАА'},
                       headers={'Authorization': 'Bearer user-token'})
    assert resp.status_code == 400


# ---- POST /api/admin/sheets/delete ----

def test_admin_delete_sheet(client):
    resp = client.post('/api/admin/sheets/delete',
                       json={'name': 'Ратчин'},
                       headers={'Authorization': 'Bearer user-token'})
    assert resp.status_code == 200
    config = resp.get_json()['config']
    assert 'Ратчин' not in config['active']
    assert 'Ратчин' in config['deleted']


def test_admin_delete_nonexistent_sheet(client):
    resp = client.post('/api/admin/sheets/delete',
                       json={'name': 'Нет'},
                       headers={'Authorization': 'Bearer user-token'})
    assert resp.status_code == 404


# ---- POST /api/admin/sheets/restore ----

def test_admin_restore_sheet(client):
    resp = client.post('/api/admin/sheets/restore',
                       json={'name': 'ДАА'},
                       headers={'Authorization': 'Bearer user-token'})
    assert resp.status_code == 200
    config = resp.get_json()['config']
    assert 'ДАА' in config['active']
    assert 'ДАА' not in config['deleted']


def test_admin_restore_not_deleted(client):
    resp = client.post('/api/admin/sheets/restore',
                       json={'name': 'Ратчин'},
                       headers={'Authorization': 'Bearer user-token'})
    assert resp.status_code == 404


# ---- PUT /api/admin/sheets/rename ----

def test_admin_rename_sheet(client):
    with patch('app.requests.get', return_value=mock_get(SHEETS_META)), \
         patch('app.requests.post', return_value=mock_post(ok=True)):
        resp = client.put('/api/admin/sheets/rename',
                          json={'old_name': 'Ратчин', 'new_name': 'РатчинV2'},
                          headers={'Authorization': 'Bearer user-token'})
    assert resp.status_code == 200
    config = resp.get_json()['config']
    assert 'РатчинV2' in config['active']
    assert 'Ратчин' not in config['active']


def test_admin_rename_sheet_not_found(client):
    resp = client.put('/api/admin/sheets/rename',
                      json={'old_name': 'Нет', 'new_name': 'Новое'},
                      headers={'Authorization': 'Bearer user-token'})
    assert resp.status_code == 404


def test_admin_rename_to_existing_name(client):
    resp = client.put('/api/admin/sheets/rename',
                      json={'old_name': 'Ратчин', 'new_name': 'ЧСА'},
                      headers={'Authorization': 'Bearer user-token'})
    assert resp.status_code == 400


def test_admin_rename_empty_names(client):
    resp = client.put('/api/admin/sheets/rename',
                      json={'old_name': '', 'new_name': ''},
                      headers={'Authorization': 'Bearer user-token'})
    assert resp.status_code == 400
