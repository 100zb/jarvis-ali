"""Configuration globale de Jarvis."""
import os
from pathlib import Path

from dotenv import load_dotenv

# .env a la racine du projet (utilise en dev, via `uv run`)
load_dotenv()

# Repli stable sur ~/.jarvis/.env : c'est la que doit vivre la cle pour l'app
# desktop installee, dont le dossier d'installation n'embarque jamais de .env
# (on ne met pas de secret dans un installeur distribue). load_dotenv() ne
# remplace jamais une variable deja definie (override=False par defaut), donc
# le .env du projet reste prioritaire en dev.
load_dotenv(Path.home() / ".jarvis" / ".env")

# Modele LLM utilise (Groq)
MODEL = "openai/gpt-oss-120b"

# Parametres de generation
TEMPERATURE = 0.7

# Cles API (lues depuis .env)
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")  # optionnelle (None si absente)

# Base de memoire persistante (historique de conversation entre les sessions)
MEMORY_DB_PATH = Path(os.environ.get("JARVIS_MEMORY_DB", str(Path.home() / ".jarvis" / "memory.db")))