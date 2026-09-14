"""Lanceur de l'interface graphique de Jarvis (double-clic, sans console)."""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from jarvis.gui_main import main  # noqa: E402

if __name__ == "__main__":
    main()
