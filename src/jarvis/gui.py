"""Interface graphique de bureau pour Jarvis (theme sombre cyan, style Iron Man)."""
import queue
import threading
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from jarvis.conversation import Conversation
from jarvis.personality import SYSTEM_PROMPT
from jarvis.tools import registry
import jarvis.tools  # noqa: F401 - charge tous les modules d'outils

ASSETS_DIR = Path(__file__).parent / "assets"

BG = "#05080d"
PANEL = "#0a1018"
INPUT_BG = "#0d1620"
USER_BUBBLE = "#12384a"
ASSISTANT_BUBBLE = "#0a1c22"
TOOL_BUBBLE = "#0a1018"
ERROR_BUBBLE = "#3a1218"
ACCENT = "#00e5ff"
ACCENT_DIM = "#0891a8"
TEXT = "#d8f4ff"
DIM_TEXT = "#5a7a8a"
ERROR_TEXT = "#ff7a85"

FONT_FAMILY = "Consolas"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class JarvisGUI(ctk.CTk):
    def __init__(self, client, model: str, temperature: float):
        super().__init__()

        self.conversation = Conversation(client, SYSTEM_PROMPT, model, temperature)
        self._queue: queue.Queue = queue.Queue()
        self._message_labels: list[tk.Widget] = []
        self._thinking_frame: ctk.CTkFrame | None = None
        self._busy = False

        self.title("JARVIS")
        self.geometry("920x720")
        self.minsize(560, 420)
        self.configure(fg_color=BG)

        icon_path = ASSETS_DIR / "jarvis.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        self._build_top_bar()
        self._build_chat_area()
        self._build_input_bar()

        self.bind("<Configure>", self._on_resize)

        self._add_system_notice(
            f"JARVIS en ligne. Outils charges ({len(registry.list_tools())}): "
            f"{', '.join(registry.list_tools())}"
        )

        self._poll_queue()

    # ---------- UI construction ----------

    def _build_top_bar(self):
        bar = ctk.CTkFrame(self, fg_color=PANEL, height=64, corner_radius=0)
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)

        title_box = ctk.CTkFrame(bar, fg_color="transparent")
        title_box.pack(side="left", padx=20)
        ctk.CTkLabel(
            title_box, text="JARVIS", text_color=ACCENT,
            font=(FONT_FAMILY, 20, "bold"),
        ).pack(anchor="w", pady=(10, 0))
        self.subtitle_label = ctk.CTkLabel(
            title_box, text="Assistant d'Ali · pret",
            text_color=DIM_TEXT, font=(FONT_FAMILY, 11),
        )
        self.subtitle_label.pack(anchor="w")

        btn_box = ctk.CTkFrame(bar, fg_color="transparent")
        btn_box.pack(side="right", padx=16)

        self._make_bar_button(btn_box, "Outils", self._show_tools).pack(side="left", padx=4)
        self._make_bar_button(btn_box, "Stats", self._show_stats).pack(side="left", padx=4)
        self._make_bar_button(btn_box, "Reset", self._reset_conversation).pack(side="left", padx=4)

    def _make_bar_button(self, parent, text, command):
        return ctk.CTkButton(
            parent, text=text, command=command,
            width=80, height=30, corner_radius=6,
            fg_color=INPUT_BG, hover_color="#132433",
            text_color=ACCENT, border_width=1, border_color=ACCENT_DIM,
            font=(FONT_FAMILY, 12),
        )

    def _build_chat_area(self):
        self.chat_frame = ctk.CTkScrollableFrame(
            self, fg_color=BG, scrollbar_button_color=ACCENT_DIM,
            scrollbar_button_hover_color=ACCENT,
        )
        self.chat_frame.pack(side="top", fill="both", expand=True, padx=10, pady=(10, 0))
        self.chat_frame.grid_columnconfigure(0, weight=1)

    def _build_input_bar(self):
        bar = ctk.CTkFrame(self, fg_color=PANEL, height=76, corner_radius=0)
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=14)

        self.entry = ctk.CTkTextbox(
            inner, height=48, fg_color=INPUT_BG, text_color=TEXT,
            border_width=1, border_color=ACCENT_DIM, corner_radius=8,
            font=(FONT_FAMILY, 13), wrap="word",
        )
        self.entry.pack(side="left", fill="both", expand=True)
        self.entry.bind("<Return>", self._on_enter_pressed)
        self.entry.bind("<Shift-Return>", lambda e: None)
        self.entry.focus_set()

        self.send_button = ctk.CTkButton(
            inner, text="Envoyer", width=100, height=48, corner_radius=8,
            fg_color=ACCENT_DIM, hover_color=ACCENT, text_color="#00131a",
            font=(FONT_FAMILY, 13, "bold"), command=self._send_message,
        )
        self.send_button.pack(side="right", padx=(10, 0))

    # ---------- message rendering ----------

    def _add_bubble(self, role: str, text: str):
        row = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        row.grid(row=len(self._message_labels), column=0, sticky="ew", pady=4)
        row.grid_columnconfigure(0, weight=1)

        if role == "user":
            bubble_color, text_color, anchor, prefix = USER_BUBBLE, TEXT, "e", "Toi"
        elif role == "assistant":
            bubble_color, text_color, anchor, prefix = ASSISTANT_BUBBLE, TEXT, "w", "Jarvis"
        elif role == "tool":
            bubble_color, text_color, anchor, prefix = TOOL_BUBBLE, DIM_TEXT, "w", None
        elif role == "error":
            bubble_color, text_color, anchor, prefix = ERROR_BUBBLE, ERROR_TEXT, "w", "Erreur"
        else:
            bubble_color, text_color, anchor, prefix = PANEL, DIM_TEXT, "center", None

        bubble = ctk.CTkFrame(row, fg_color=bubble_color, corner_radius=10)
        bubble.grid(row=0, column=0, sticky=("e" if anchor == "e" else "w"))

        if prefix:
            ctk.CTkLabel(
                bubble, text=prefix, text_color=ACCENT if role != "error" else ERROR_TEXT,
                font=(FONT_FAMILY, 11, "bold"), anchor="w",
            ).pack(anchor="w", padx=12, pady=(8, 0))

        label = ctk.CTkLabel(
            bubble, text=text, text_color=text_color, font=(FONT_FAMILY, 13),
            justify="left", anchor="w", wraplength=self._wrap_width(),
        )
        label.pack(anchor="w", padx=12, pady=(0 if prefix else 8, 8))

        self._message_labels.append(label)
        self._scroll_to_bottom()
        return bubble

    def _add_system_notice(self, text: str):
        self._add_bubble("system", text)

    def _add_tool_notice(self, tool_name: str, args: dict):
        args_display = ", ".join(f"{k}={v!r}" for k, v in args.items())
        self._add_bubble("tool", f">>> {tool_name}({args_display})")

    def _wrap_width(self) -> int:
        return max(300, self.winfo_width() - 140)

    def _on_resize(self, event):
        if event.widget is not self:
            return
        width = self._wrap_width()
        for label in self._message_labels:
            label.configure(wraplength=width)

    def _scroll_to_bottom(self):
        self.after(30, lambda: self.chat_frame._parent_canvas.yview_moveto(1.0))

    # ---------- thinking indicator ----------

    def _show_thinking(self):
        self._thinking_frame = self._add_bubble("assistant", "reflechit...")

    def _hide_thinking(self):
        if self._thinking_frame is not None:
            self._thinking_frame.master.destroy()
            self._thinking_frame = None
            if self._message_labels:
                self._message_labels.pop()

    # ---------- sending ----------

    def _on_enter_pressed(self, event):
        self._send_message()
        return "break"

    def _send_message(self):
        if self._busy:
            return
        text = self.entry.get("1.0", "end").strip()
        if not text:
            return

        self.entry.delete("1.0", "end")
        self._add_bubble("user", text)

        self._busy = True
        self.send_button.configure(state="disabled", text="...")
        self.subtitle_label.configure(text="Assistant d'Ali · reflechit...")
        self._show_thinking()

        thread = threading.Thread(target=self._worker_send, args=(text,), daemon=True)
        thread.start()

    def _worker_send(self, text: str):
        def on_tool_call(name, args):
            self._queue.put(("tool", (name, args)))

        try:
            reply = self.conversation.send(text, on_tool_call=on_tool_call)
            self._queue.put(("reply", reply))
        except Exception as e:
            self._queue.put(("error", str(e)))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "tool":
                    name, args = payload
                    self._hide_thinking()
                    self._add_tool_notice(name, args)
                    self._show_thinking()
                elif kind == "reply":
                    self._hide_thinking()
                    self._add_bubble("assistant", payload)
                    self._finish_turn()
                elif kind == "error":
                    self._hide_thinking()
                    self._add_bubble("error", payload)
                    self._finish_turn()
        except queue.Empty:
            pass
        self.after(50, self._poll_queue)

    def _finish_turn(self):
        self._busy = False
        self.send_button.configure(state="normal", text="Envoyer")
        self.subtitle_label.configure(text="Assistant d'Ali · pret")
        if self.conversation.should_compact():
            self.conversation.compact()
            self._add_system_notice("Historique compacte automatiquement.")

    # ---------- top bar actions ----------

    def _show_tools(self):
        self._add_system_notice("Outils disponibles : " + ", ".join(registry.list_tools()))

    def _show_stats(self):
        c = self.conversation
        self._add_system_notice(
            f"Messages: {c.message_count} | Tours: {c.turn_count} | Compactions: {c.compaction_count}"
        )

    def _reset_conversation(self):
        self.conversation.reset()
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
        self._message_labels.clear()
        self._add_system_notice("Memoire effacee. Nouvelle conversation.")
