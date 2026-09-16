import os
import shutil
from pathlib import Path
from datetime import datetime

BACKUP_ROOT = "D:\\\\"

def secure_path(rel_path: str) -> Path:
    """
    Resolve the given relative path against BACKUP_ROOT and ensure it stays within BACKUP_ROOT.
    """
    root = Path(BACKUP_ROOT).resolve()
    
    # Remove leading slashes so it's treated as relative
    rel_path = rel_path.lstrip("/\\")
    
    target = (root / rel_path).resolve()
    
    if not str(target).startswith(str(root)):
        raise ValueError("Access denied: Path is outside the backup directory.")
        
    return target

def list_directory(rel_path: str = "") -> list:
    """
    List contents of the directory at rel_path.
    Returns a list of dicts with name, is_dir, size, and modified time.
    """
    target = secure_path(rel_path)
    
    if not target.exists() or not target.is_dir():
        return []
        
    items = []
    for entry in target.iterdir():
        stat = entry.stat()
        items.append({
            "name": entry.name,
            "is_dir": entry.is_dir(),
            "size": stat.st_size if not entry.is_dir() else 0,
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        })
        
    # Sort: directories first, then alphabetically
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return items

def create_directory(rel_path: str):
    """
    Create a new directory at rel_path.
    """
    target = secure_path(rel_path)
    target.mkdir(parents=True, exist_ok=True)

def delete_item(rel_path: str):
    """
    Delete file or directory at rel_path.
    """
    target = secure_path(rel_path)
    
    if not target.exists():
        return
        
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
