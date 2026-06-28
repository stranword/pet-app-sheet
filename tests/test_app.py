import os
import pytest
from unittest.mock import patch

os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost/test')

import app as flask_app

DEFAULT_CONFIG = {'active': ['Ратчин', 'ЧСА'], 'deleted': ['ДАА']}

SAMPLE_ROWS = [
    {'id': 1, 'shk': 'SHK001', 'kolichestvo': '5', 'nomer_koroba': '3', 'data': '01.01.2024 10:00'},
    {'id': 2, 'shk': 'SHK002', 'kolichestvo': '2', 'nomer_koroba': '1', 'data': '02.01.2024 11:00'},
]


@pytest.fixture(autouse=True)
def patch_config():
    config_data = {'active': ['Ратчин', 'ЧСА'], 'deleted': ['ДАА']}
    with patch('app.load_config', return_value=config_data):
        yield


@pytest.fixture
def client():
    flask_app.app.config['TESTING'] = True
    with flask_app.app.test_client() as c:
        yield c


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
    assert 'ДАА'.encode() in resp.data


# ---- GET /api/rows/<sheet> ----

def test_get_rows_success(client):
    with patch('app.db_execute', return_value=SAMPLE_ROWS):
        resp = client.get('/api/rows/Ратчин')
    assert resp.status_code == 200
    rows = resp.get_json()
    assert len(rows) == 2
    assert rows[0] == {
        'id': 1, 'shk': 'SHK001',
        'kolichestvo': '5', 'nomerKoroba': '3', 'data': '01.01.2024 10:00',
    }


def test_get_rows_unknown_sheet(client):
    resp = client.get('/api/rows/Неизвестный')
    assert resp.status_code == 400


def test_get_rows_empty_sheet(client):
    with patch('app.db_execute', return_value=[]):
        resp = client.get('/api/rows/Ратчин')
    assert resp.status_code == 200
    assert resp.get_json() == []


# ---- POST /api/rows/<sheet> ----

def test_add_row_success(client):
    with patch('app.db_execute', return_value=None):
        resp = client.post('/api/rows/Ратчин', json={
            'shk': 'SHK999', 'kolichestvo': 3, 'nomerKoroba': 2,
        })
    assert resp.status_code == 200
    assert resp.get_json()['ok'] is True


def test_add_row_unknown_sheet(client):
    resp = client.post('/api/rows/Неизвестный', json={'shk': 'X'})
    assert resp.status_code == 400


# ---- PUT /api/rows/<sheet>/<row_id> ----

def test_update_row_success(client):
    with patch('app.db_execute', return_value=None):
        resp = client.put('/api/rows/Ратчин/1', json={
            'shk': 'SHK001', 'kolichestvo': 10, 'nomerKoroba': 1, 'data': '01.01.2024 10:00',
        })
    assert resp.status_code == 200
    assert resp.get_json()['ok'] is True


def test_update_row_unknown_sheet(client):
    resp = client.put('/api/rows/Неизвестный/1', json={})
    assert resp.status_code == 400


# ---- DELETE /api/rows/<sheet>/<row_id> ----

def test_delete_row_success(client):
    with patch('app.db_execute', return_value=None):
        resp = client.delete('/api/rows/Ратчин/1')
    assert resp.status_code == 200
    assert resp.get_json()['ok'] is True


def test_delete_row_unknown_sheet(client):
    resp = client.delete('/api/rows/Неизвестный/1')
    assert resp.status_code == 400


# ---- GET /api/export/<sheet> ----

def test_export_sheet_success(client):
    with patch('app.db_execute', return_value=SAMPLE_ROWS):
        resp = client.get('/api/export/Ратчин')
    assert resp.status_code == 200
    assert 'spreadsheetml' in resp.content_type


def test_export_unknown_sheet(client):
    resp = client.get('/api/export/Неизвестный')
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
    with patch('app.db_execute', return_value=None):
        resp = client.post('/api/admin/sheets', json={'name': 'НовыйЛист'})
    assert resp.status_code == 200
    config = resp.get_json()['config']
    assert 'НовыйЛист' in config['active']


def test_admin_add_sheet_duplicate(client):
    resp = client.post('/api/admin/sheets', json={'name': 'Ратчин'})
    assert resp.status_code == 400


def test_admin_add_sheet_empty_name(client):
    resp = client.post('/api/admin/sheets', json={'name': '  '})
    assert resp.status_code == 400


def test_admin_add_deleted_sheet_rejected(client):
    resp = client.post('/api/admin/sheets', json={'name': 'ДАА'})
    assert resp.status_code == 400


# ---- POST /api/admin/sheets/delete ----

def test_admin_delete_sheet(client):
    with patch('app.db_execute', return_value=None):
        resp = client.post('/api/admin/sheets/delete', json={'name': 'Ратчин'})
    assert resp.status_code == 200
    config = resp.get_json()['config']
    assert 'Ратчин' not in config['active']
    assert 'Ратчин' in config['deleted']


def test_admin_delete_nonexistent_sheet(client):
    resp = client.post('/api/admin/sheets/delete', json={'name': 'Нет'})
    assert resp.status_code == 404


# ---- POST /api/admin/sheets/restore ----

def test_admin_restore_sheet(client):
    with patch('app.db_execute', return_value=None):
        resp = client.post('/api/admin/sheets/restore', json={'name': 'ДАА'})
    assert resp.status_code == 200
    config = resp.get_json()['config']
    assert 'ДАА' in config['active']
    assert 'ДАА' not in config['deleted']


def test_admin_restore_not_deleted(client):
    resp = client.post('/api/admin/sheets/restore', json={'name': 'Ратчин'})
    assert resp.status_code == 404


# ---- PUT /api/admin/sheets/rename ----

def test_admin_rename_sheet(client):
    with patch('app.db_transaction', return_value=None):
        resp = client.put('/api/admin/sheets/rename',
                          json={'old_name': 'Ратчин', 'new_name': 'РатчинV2'})
    assert resp.status_code == 200
    config = resp.get_json()['config']
    assert 'РатчинV2' in config['active']
    assert 'Ратчин' not in config['active']


def test_admin_rename_sheet_not_found(client):
    resp = client.put('/api/admin/sheets/rename',
                      json={'old_name': 'Нет', 'new_name': 'Новое'})
    assert resp.status_code == 404


def test_admin_rename_to_existing_name(client):
    resp = client.put('/api/admin/sheets/rename',
                      json={'old_name': 'Ратчин', 'new_name': 'ЧСА'})
    assert resp.status_code == 400


def test_admin_rename_empty_names(client):
    resp = client.put('/api/admin/sheets/rename',
                      json={'old_name': '', 'new_name': ''})
    assert resp.status_code == 400
