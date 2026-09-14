# Jarvis

Assistant IA personnel avec tool calling (Groq), memoire de conversation, et interface
graphique de bureau (theme sombre cyan).

## Installation

```bash
uv sync
```

Cree un fichier `.env` a la racine (voir `.env.example`) :

```
GROQ_API_KEY=ta_cle_ici
TAVILY_API_KEY=ta_cle_ici
```

- `GROQ_API_KEY` (obligatoire) : cle depuis [console.groq.com](https://console.groq.com/keys)
- `TAVILY_API_KEY` (optionnelle) : necessaire pour l'outil `web_search`, depuis [tavily.com](https://tavily.com)

## Lancer Jarvis

**Interface graphique** (recommande) :

```bash
uv run jarvis-gui
```

Ou double-clique sur le raccourci **Jarvis** sur le Bureau.

**Terminal (CLI)** :

```bash
uv run jarvis
```

Commandes CLI : `exit` | `/reset` | `/compact` | `/stats` | `/tools`

## Outils disponibles

- `get_current_time` - heure et date actuelles
- `open_app` / `list_known_apps` - lancer des applications Windows
- `calculate` - calculs mathematiques precis
- `web_search` - recherche web (necessite `TAVILY_API_KEY`)
- `show_map` / `show_globe` - cartes et globe 3D interactifs

## Structure

```
src/jarvis/
  main.py          CLI (terminal)
  gui.py           Interface graphique (customtkinter)
  gui_main.py      Point d'entree de la GUI
  conversation.py  Memoire, compaction, boucle de tool calling
  personality.py   System prompt / personnalite de Jarvis
  config.py        Config globale (modele, cles API)
  tools/           Outils (decorateur @tool auto-enregistre)
```

## Regenerer l'icone

```bash
uv run python scripts/make_icon.py
```
