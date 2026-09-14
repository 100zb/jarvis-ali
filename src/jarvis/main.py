"""Jarvis - point d'entree de l'application."""
from groq import Groq
from rich.console import Console
from rich.markdown import Markdown

from jarvis.config import GROQ_API_KEY, MEMORY_DB_PATH, MODEL, TEMPERATURE
from jarvis.conversation import Conversation
from jarvis.personality import SYSTEM_PROMPT
from jarvis.store import MemoryStore
from jarvis.tools import registry  # noqa: F401 - declenche le chargement des outils
import jarvis.tools  # noqa: F401 - charge tous les modules d'outils

console = Console()


def main():
    client = Groq(api_key=GROQ_API_KEY)
    store = MemoryStore(MEMORY_DB_PATH)
    conversation = Conversation(client, SYSTEM_PROMPT, MODEL, TEMPERATURE, store=store)

    available_tools = registry.list_tools()
    console.print("[bold cyan]Jarvis v0.2.0[/bold cyan] - Phase 2: tool calling actif")
    console.print(f"[dim]Outils charges ({len(available_tools)}): {', '.join(available_tools)}[/dim]")
    console.print("[dim]Commandes: 'exit' | '/reset' | '/compact' | '/stats' | '/tools'[/dim]")
    if conversation.message_count > 0:
        console.print(f"[dim]Memoire rechargee ({conversation.message_count} messages).[/dim]\n")
    else:
        console.print()

    while True:
        try:
            user_input = console.input("[bold green]Toi:[/bold green] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]A plus, BOSS.[/dim]")
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in ("exit", "quit", "q"):
            console.print("[dim]A plus, BOSS.[/dim]")
            break

        if cmd == "/reset":
            conversation.reset()
            console.print("[yellow]Memoire effacee.[/yellow]\n")
            continue

        if cmd == "/compact":
            if conversation.compact():
                console.print("[yellow]Historique compacte.[/yellow]\n")
            else:
                console.print("[dim]Pas assez de messages.[/dim]\n")
            continue

        if cmd == "/stats":
            console.print(
                f"[dim]Messages: {conversation.message_count} | "
                f"Tours: {conversation.turn_count} | "
                f"Compactions: {conversation.compaction_count}[/dim]\n"
            )
            continue

        if cmd == "/tools":
            console.print(f"[dim]Outils disponibles: {', '.join(registry.list_tools())}[/dim]\n")
            continue

        try:
            reply = conversation.send(user_input, console=console)
        except Exception as e:
            console.print(f"[red]Erreur: {e}[/red]\n")
            continue

        if conversation.should_compact():
            console.print("[dim italic]Compaction auto...[/dim italic]")
            conversation.compact()

        console.print(
            f"\n[bold magenta]Jarvis:[/bold magenta] "
            f"[dim](tour {conversation.turn_count})[/dim]"
        )
        console.print(Markdown(reply))
        console.print()


if __name__ == "__main__":
    main()