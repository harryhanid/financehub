import os
import socket
from waitress import serve
from app import create_app
from database import init_db

if __name__ == "__main__":
    if not os.environ.get("FH_JWT_SECRET"):
        print("⚠  WARNING: FH_JWT_SECRET env var tidak di-set.")
        print("   JWT secret akan di-generate ulang setiap restart — semua sesi akan invalid.")
        print("   Set: set FH_JWT_SECRET=<random-64-char-hex>  sebelum menjalankan server.")
        print()

    init_db()
    app = create_app()
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 8080))
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "127.0.0.1"
    print("=" * 55)
    print("  Finance Hub — Production Server")
    print("=" * 55)
    print(f"  Local :  http://localhost:{port}")
    print(f"  LAN   :  http://{local_ip}:{port}")
    print("=" * 55)
    print("  Tekan Ctrl+C untuk menghentikan server")
    print()
    serve(app, host=host, port=port, threads=8)
