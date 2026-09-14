"""Gestion de la conversation avec memoire, compaction et tool calling."""
import json
from groq import Groq

from jarvis.tools.registry import get_schemas, execute_tool


class Conversation:
    """Gere une conversation continue avec memoire, compaction et tool calling."""

    COMPACT_THRESHOLD = 12
    KEEP_RECENT = 4
    MAX_TOOL_ITERATIONS = 5  # securite anti-boucle infinie

    def __init__(self, client: Groq, system_prompt: str, model: str, temperature: float = 0.7, store=None):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.store = store
        self.compaction_count = 0

        persisted = self.store.load_messages() if self.store else []
        self.messages = [{"role": "system", "content": system_prompt}, *persisted]

    def _persist(self) -> None:
        if self.store:
            self.store.replace_all(self.messages[1:])

    def send(self, user_message: str, console=None) -> str:
        """Envoie un message, gere les tool calls en boucle, retourne la reponse finale."""
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
                    self._persist()
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

                    result = execute_tool(tool_name, args)

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

            self._persist()
            return "Trop d'iterations sur les outils, j'arrete la."

        except Exception:
            # Rollback : on retire tout ce qu'on a ajoute pendant cet appel rate
            self.messages = self.messages[:messages_before]
            raise

    def reset(self):
        """Reset la conversation, garde juste le system prompt."""
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.compaction_count = 0
        self._persist()

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
        self._persist()
        return True

    def send_stream(self, user_message: str):
        """Comme send(), mais en generateur : yield des evenements au fur et a mesure.

        Evenements possibles :
        - {"type": "delta", "content": str}            -> fragment de texte de la reponse
        - {"type": "tool_call", "name": str, "args": dict}
        - {"type": "tool_result", "name": str, "result": str}
        - {"type": "done", "content": str}              -> reponse finale complete
        - {"type": "error", "message": str}
        """
        messages_before = len(self.messages)
        self.messages.append({"role": "user", "content": user_message})

        try:
            for _ in range(self.MAX_TOOL_ITERATIONS):
                tools = get_schemas()
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    temperature=self.temperature,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                    stream=True,
                )

                content = ""
                tool_calls_acc: dict[int, dict] = {}

                for chunk in stream:
                    delta = chunk.choices[0].delta

                    if delta.content:
                        content += delta.content
                        yield {"type": "delta", "content": delta.content}

                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            acc = tool_calls_acc.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                            if tc.id:
                                acc["id"] = tc.id
                            if tc.function and tc.function.name:
                                acc["name"] += tc.function.name
                            if tc.function and tc.function.arguments:
                                acc["arguments"] += tc.function.arguments

                if not tool_calls_acc:
                    self.messages.append({"role": "assistant", "content": content})
                    self._persist()
                    yield {"type": "done", "content": content}
                    return

                ordered_tool_calls = [tool_calls_acc[i] for i in sorted(tool_calls_acc)]

                self.messages.append({
                    "role": "assistant",
                    "content": content or "",
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": tc["arguments"]},
                        } for tc in ordered_tool_calls
                    ]
                })

                for tc in ordered_tool_calls:
                    tool_name = tc["name"]
                    raw_args = tc["arguments"] or "{}"

                    try:
                        args = json.loads(raw_args) or {}
                    except json.JSONDecodeError:
                        args = {}

                    yield {"type": "tool_call", "name": tool_name, "args": args}

                    result = execute_tool(tool_name, args)

                    yield {"type": "tool_result", "name": tool_name, "result": result}

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })

            self._persist()
            yield {"type": "done", "content": "Trop d'iterations sur les outils, j'arrete la."}

        except Exception:
            self.messages = self.messages[:messages_before]
            raise

    @property
    def turn_count(self) -> int:
        non_system = [m for m in self.messages[1:] if m.get('role') in ('user', 'assistant')]
        return len(non_system) // 2

    @property
    def message_count(self) -> int:
        return len(self.messages) - 1