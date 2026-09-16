import os
import pytest
from pathlib import Path
from modules.backup.service import (
    list_directory,
    create_directory,
    delete_item,
    secure_path
)

@pytest.fixture
def backup_root(tmp_path, monkeypatch):
    root = tmp_path / "Backup"
    root.mkdir()
    # Mock the root path in the service
    monkeypatch.setattr("modules.backup.service.BACKUP_ROOT", str(root))
    return root

def test_secure_path_valid(backup_root):
    path = secure_path("subfolder")
    assert str(path) == str(backup_root / "subfolder")

def test_secure_path_invalid(backup_root):
    with pytest.raises(ValueError, match="Access denied"):
        secure_path("../outside")
    
    with pytest.raises(ValueError, match="Access denied"):
        secure_path("subfolder/../../outside")

def test_list_directory(backup_root):
    # Create some files and folders
    (backup_root / "folder1").mkdir()
    (backup_root / "file1.txt").write_text("hello")
    
    items = list_directory("")
    assert len(items) == 2
    
    # Sort for deterministic assertions
    items.sort(key=lambda x: x["name"])
    
    assert items[0]["name"] == "file1.txt"
    assert items[0]["is_dir"] is False
    assert items[0]["size"] == 5
    
    assert items[1]["name"] == "folder1"
    assert items[1]["is_dir"] is True
    assert items[1]["size"] == 0

def test_create_directory(backup_root):
    create_directory("new_folder")
    assert (backup_root / "new_folder").is_dir()
    
    with pytest.raises(ValueError):
        create_directory("../invalid_folder")

def test_delete_item(backup_root):
    file_path = backup_root / "todelete.txt"
    file_path.write_text("delete me")
    
    dir_path = backup_root / "todelete_dir"
    dir_path.mkdir()
    
    delete_item("todelete.txt")
    assert not file_path.exists()
    
    delete_item("todelete_dir")
    assert not dir_path.exists()
    
    with pytest.raises(ValueError):
        delete_item("../todelete_dir")
