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
sur `http://127.0.0.1:8756`. L'historique de conversation est sauvegarde dans
`~/.jarvis/memory.db` (SQLite) et rechargee a chaque ouverture.

### Installeur Windows (.exe)

Pour obtenir une vraie appli installable (icone Bureau/menu Demarrer, plus besoin de terminal),
lance la commande suivante **sur Windows** (electron-builder doit tourner sur l'OS cible) :

```powershell
cd desktop
npm install
npm run dist
```

L'installeur `Jarvis Setup <version>.exe` est genere dans `desktop/dist/`. Il installe l'app
dans le profil utilisateur (pas besoin des droits admin) et cree les raccourcis. `uv` doit
etre installe sur la machine (l'app l'utilise pour lancer le backend Python embarque).
