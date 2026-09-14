"""Gestion de la conversation avec memoire, compaction et tool calling."""
import json
from groq import Groq

from jarvis.tools.registry import get_schemas, execute_tool


class Conversation:
    """Gere une conversation continue avec memoire, compaction et tool calling."""

    COMPACT_THRESHOLD = 12
    KEEP_RECENT = 4
    MAX_TOOL_ITERATIONS = 5  # securite anti-boucle infinie

    def __init__(self, client: Groq, system_prompt: str, model: str, temperature: float = 0.7):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.messages = [{"role": "system", "content": system_prompt}]
        self.compaction_count = 0

    def send(self, user_message: str, console=None, on_tool_call=None) -> str:
        """Envoie un message, gere les tool calls en boucle, retourne la reponse finale.

        on_tool_call: callback optionnel appele avec (tool_name, args_dict) avant
        chaque execution d'outil, pour permettre a une UI externe (ex: GUI) de
        l'afficher sans dependre de rich.Console.
        """
        messages_before = len(self.messages)
        self.messages.append({"role": "user", "content": user_message})

        try:
            for _ in range(self.MAX_TOOL_ITERATIONS):
                tools = get_schemas()
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    temperature=self.temperature,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                )

                message = response.choices[0].message

                if not message.tool_calls:
                    self.messages.append({"role": "assistant", "content": message.content})
                    return message.content

                self.messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        } for tc in message.tool_calls
                    ]
                })

                for tc in message.tool_calls:
                    tool_name = tc.function.name
                    raw_args = tc.function.arguments or "{}"

                    try:
                        args = json.loads(raw_args) or {}
                    except json.JSONDecodeError:
                        args = {}

                    if console:
                        args_display = ", ".join(f"{k}={v!r}" for k, v in args.items())
                        console.print(f"[dim italic]>>> {tool_name}({args_display})[/dim italic]")

                    if on_tool_call:
                        on_tool_call(tool_name, args)

                    result = execute_tool(tool_name, args)

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

            return "Trop d'iterations sur les outils, j'arrete la."

        except Exception:
            # Rollback : on retire tout ce qu'on a ajoute pendant cet appel rate
            self.messages = self.messages[:messages_before]
            raise
        
    def reset(self):
        """Reset la conversation, garde juste le system prompt."""
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.compaction_count = 0

    def should_compact(self) -> bool:
        return len(self.messages) - 1 > self.COMPACT_THRESHOLD

    def compact(self) -> bool:
        non_system = self.messages[1:]
        if len(non_system) <= self.KEEP_RECENT:
            return False

        to_summarize = non_system[:-self.KEEP_RECENT]
        to_keep = non_system[-self.KEEP_RECENT:]

        conversation_text = "\n".join(
            f"{'Ali' if msg.get('role') == 'user' else 'Jarvis'}: {msg.get('content', '')}"
            for msg in to_summarize
            if msg.get('role') in ('user', 'assistant') and msg.get('content')
        )

        summary_response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Tu resumes des conversations de maniere concise et factuelle."},
                {"role": "user", "content": (
                    "Resume cette conversation entre Ali et son assistant Jarvis. "
                    "Garde les faits importants. Sois concis (max 200 mots).\n\n"
                    f"Conversation:\n{conversation_text}"
                )}
            ],
            temperature=0.3,
        )
        summary = summary_response.choices[0].message.content

        self.messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": "Resume de notre conversation jusqu'a present :"},
            {"role": "assistant", "content": summary},
            *to_keep
        ]
        self.compaction_count += 1
        return True

    @property
    def turn_count(self) -> int:
        non_system = [m for m in self.messages[1:] if m.get('role') in ('user', 'assistant')]
        return len(non_system) // 2

    @property
    def message_count(self) -> int:
        return len(self.messages) - 1