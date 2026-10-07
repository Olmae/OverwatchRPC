"""Build a portable directory; preserves fast startup without one-file extraction."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    if sys.platform != "win32":
        raise SystemExit("Build this artifact on Windows; PyInstaller cannot cross-compile Windows binaries.")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
                    "--name", "OverwatchRPC", "--icon", str(ROOT / "assets" / "app.ico"),
                    "--add-data", str(ROOT / "assets") + os.pathsep + "assets",
                    "--hidden-import", "pystray._win32", "--hidden-import", "PIL.ImageTk",
                    "--hidden-import", "pytesseract", str(ROOT / "owrpc.py")], cwd=ROOT, check=True)
    print("Built dist/OverwatchRPC/OverwatchRPC.exe — keep the whole folder together.")


if __name__ == "__main__":
    main()
