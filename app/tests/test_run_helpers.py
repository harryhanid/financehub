import socket
import importlib, sys, types


def _load_get_lan_ip():
    """Import get_lan_ip dari run_production tanpa menjalankan main block."""
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location(
        "run_production",
        pathlib.Path(__file__).parent.parent / "run_production.py"
    )
    mod = importlib.util.module_from_spec(spec)
    # Stub agar import side-effect (init_db, create_app, waitress) tidak jalan
    for name in ("app", "database", "waitress"):
        if name not in sys.modules:
            mock_mod = types.ModuleType(name)
            if name == "app":
                mock_mod.create_app = lambda: None
            elif name == "database":
                mock_mod.init_db = lambda: None
            elif name == "waitress":
                mock_mod.serve = lambda *args, **kwargs: None
            sys.modules[name] = mock_mod
    spec.loader.exec_module(mod)
    return mod.get_lan_ip


def test_get_lan_ip_returns_non_loopback():
    get_lan_ip = _load_get_lan_ip()
    ip = get_lan_ip()
    assert isinstance(ip, str)
    assert ip != "127.0.0.1", f"get_lan_ip() returned loopback: {ip}"
    parts = ip.split(".")
    assert len(parts) == 4, f"Bukan IPv4: {ip}"
    assert all(p.isdigit() for p in parts), f"Format salah: {ip}"
