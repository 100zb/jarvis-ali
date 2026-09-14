# Jarvis

Assistant personnel avec tool calling (Groq), utilisable en terminal ou via une app desktop.

## Setup

```bash
uv sync
cp .env.example .env   # renseigner GROQ_API_KEY (et TAVILY_API_KEY en option)
```

## Terminal

```bash
uv run jarvis
```

Commandes : `exit` | `/reset` | `/compact` | `/stats` | `/tools`

## App desktop

Interface graphique (Electron) qui pilote le meme moteur Jarvis via un backend FastAPI local
(streaming des reponses, appels d'outils affiches en temps reel).

```bash
cd desktop
npm install
npm start
```

Le backend FastAPI (`uv run jarvis-server`) est lance automatiquement par l'app au demarrage,
sur `http://127.0.0.1:8756`.
