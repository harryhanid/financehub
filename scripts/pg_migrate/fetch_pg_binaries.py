"""Extract Postgres binaries from the pgserver wheel into app/tests/_pg (wheel is not installed)."""
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "app" / "tests" / "_pg"
PREFIX = "pgserver/pginstall/"


def main() -> int:
    if (DEST / "bin" / "postgres.exe").exists():
        print("already present:", DEST)
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [sys.executable, "-m", "pip", "download", "pgserver==0.1.4", "--no-deps",
             "--only-binary=:all:", "--python-version", "3.12", "--platform", "win_amd64",
             "-d", tmp],
            check=True,
        )
        wheel = next(Path(tmp).glob("pgserver-*.whl"))
        with zipfile.ZipFile(wheel) as z:
            for name in z.namelist():
                if not name.startswith(PREFIX) or name.endswith("/"):
                    continue
                target = DEST / name[len(PREFIX):]
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(name) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
    print("extracted to", DEST)
    return 0


if __name__ == "__main__":
    sys.exit(main())
