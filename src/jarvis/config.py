"""Configuration globale de Jarvis."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Modele LLM utilise (Groq)
MODEL = "openai/gpt-oss-120b"

# Parametres de generation
TEMPERATURE = 0.7

# Cles API (lues depuis .env)
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")  # optionnelle (None si absente)

# Base de memoire persistante (historique de conversation entre les sessions)
MEMORY_DB_PATH = Path(os.environ.get("JARVIS_MEMORY_DB", str(Path.home() / ".jarvis" / "memory.db")))