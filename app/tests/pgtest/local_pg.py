"""Start/stop a throwaway local Postgres from binaries in tests/_pg (see scripts/pg_migrate/fetch_pg_binaries.py)."""
import os
import subprocess

PG_BIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_pg", "bin")


def _exe(name: str) -> str:
    return os.path.join(PG_BIN_DIR, name + ".exe")


def start(data_dir: str, port: int = 54329) -> str:
    if not os.path.exists(os.path.join(data_dir, "PG_VERSION")):
        subprocess.run([_exe("initdb"), "-D", data_dir, "-U", "postgres", "-A", "trust", "-E", "UTF8"],
                       check=True, capture_output=True)
    subprocess.run([_exe("pg_ctl"), "-D", data_dir, "-o", f"-p {port} -h 127.0.0.1",
                    "-l", os.path.join(data_dir, "server.log"), "-w", "start"],
                   check=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f"postgresql://postgres@127.0.0.1:{port}/postgres"


def stop(data_dir: str) -> None:
    subprocess.run([_exe("pg_ctl"), "-D", data_dir, "-m", "fast", "-w", "stop"],
                   check=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
