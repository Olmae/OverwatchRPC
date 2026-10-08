"""Build a portable directory; preserves fast startup without one-file extraction."""
import os
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--onefile', action='store_true', help='Build a standalone EXE in dist/standalone')
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Build this artifact on Windows; PyInstaller cannot cross-compile Windows binaries.")
    layout = (['--onefile','--distpath',str(ROOT/'dist'/'standalone'),
               '--workpath',str(ROOT/'build'/'standalone'), '--specpath',str(ROOT/'build'/'standalone')]
              if args.onefile else ['--onedir'])
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", *layout, "--windowed",
                    "--name", "OverwatchRPC", "--icon", str(ROOT / "assets" / "app.ico"),
                    "--add-data", str(ROOT / "assets") + os.pathsep + "assets",
                    "--add-data", str(ROOT / "LICENSE") + os.pathsep + ".",
                    "--hidden-import", "pystray._win32", "--hidden-import", "PIL.ImageTk",
                    "--hidden-import", "pytesseract", str(ROOT / "owrpc.py")], cwd=ROOT, check=True)
    print("Built dist/standalone/OverwatchRPC.exe" if args.onefile else
          "Built dist/OverwatchRPC/OverwatchRPC.exe — keep the whole folder together.")


if __name__ == "__main__":
    main()
