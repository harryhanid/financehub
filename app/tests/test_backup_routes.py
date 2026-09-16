import pytest
from tests.test_beasiswa_routes import login

def test_backup_index_unauthorized(client):
    resp = client.get("/backup/")
    assert resp.status_code == 302 # Redirects to login

def test_backup_index_authorized(client, monkeypatch):
    login(client)
    # Mock list_directory so it doesn't crash if D:\Backup doesn't exist on CI
    monkeypatch.setattr("modules.backup.routes.list_directory", lambda path: [])
    resp = client.get("/backup/")
    assert resp.status_code == 200
    assert b"Backup Data Y" in resp.data or b"Backup" in resp.data

def test_backup_create_directory(client, monkeypatch):
    login(client)
    called = []
    monkeypatch.setattr("modules.backup.routes.create_directory", lambda path: called.append(path))
    resp = client.post("/backup/create_folder", data={"path": "", "folder_name": "test_folder"})
    assert resp.status_code == 302 # Redirects back to index
    assert "test_folder" in called

def test_backup_delete_item(client, monkeypatch):
    login(client)
    called = []
    monkeypatch.setattr("modules.backup.routes.delete_item", lambda path: called.append(path))
    resp = client.post("/backup/delete", data={"path": "test_folder"})
    assert resp.status_code == 302
    assert "test_folder" in called
