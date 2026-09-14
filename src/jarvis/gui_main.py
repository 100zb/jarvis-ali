"""Point d'entree de l'interface graphique de Jarvis."""
import sys
import tkinter.messagebox as messagebox


def main():
    try:
        from jarvis.config import GROQ_API_KEY, MODEL, TEMPERATURE
    except KeyError:
        messagebox.showerror(
            "JARVIS - Configuration manquante",
            "La cle GROQ_API_KEY est introuvable.\n\n"
            "Cree un fichier .env a la racine du projet avec :\n"
            "GROQ_API_KEY=ta_cle_ici\n\n"
            "(voir .env.example)",
        )
        sys.exit(1)

    from groq import Groq
    from jarvis.gui import JarvisGUI

    client = Groq(api_key=GROQ_API_KEY)
    app = JarvisGUI(client, MODEL, TEMPERATURE)
    app.mainloop()


if __name__ == "__main__":
    main()
