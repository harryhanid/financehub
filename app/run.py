"""
Finance Hub — Production entry point
Jalankan: python run.py
Akses LAN: http://<IP-laptop>:8080
"""
import socket
from waitress import serve
from app import create_app
from database import init_db

if __name__ == "__main__":
    init_db()
    application = create_app()
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "127.0.0.1"
    print("=" * 50)
    print("  Finance Hub — Production Server")
    print(f"  Local : http://localhost:8080")
    print(f"  LAN   : http://{local_ip}:8080")
    print("  Tekan Ctrl+C untuk berhenti")
    print("=" * 50)
    serve(application, host="0.0.0.0", port=8080, threads=4)
