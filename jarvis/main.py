"""
JARVIS Android App — main.py
Fixes applied:
  1. API key ab Android-safe user_data_dir mein save hoti hai
  2. NotoEmoji font se emojis sahi render hote hain
"""

import os
import json
import urllib.request
import urllib.error

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.core.text import LabelBase
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import platform

# ── FIX 2: Emoji font register ────────────────────────────────────────────────
# NotoEmoji.ttf assets/fonts/ folder mein hona chahiye (buildozer.spec mein add karo)
_EMOJI_FONT_PATH = os.path.join(
    os.path.dirname(__file__), "assets", "fonts", "NotoEmoji.ttf"
)
if os.path.exists(_EMOJI_FONT_PATH):
    LabelBase.register(name="NotoEmoji", fn_regular=_EMOJI_FONT_PATH)
    _EMOJI_FONT = "NotoEmoji"
else:
    # Fallback — font nahi mila, default use karo (boxes aayenge sirf tab)
    _EMOJI_FONT = "Roboto"

# ── API key persistence helpers ───────────────────────────────────────────────

def _config_path():
    """
    FIX 1: Android pe writable path.
    user_data_dir  →  /data/data/<package>/files/
    Desktop pe     →  ~/.jarvis/
    """
    app = App.get_running_app()
    if app:
        data_dir = app.user_data_dir          # Kivy guaranteed-writable path
    else:
        data_dir = os.path.expanduser("~/.jarvis")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "config.json")


def load_api_key() -> str:
    try:
        with open(_config_path(), "r", encoding="utf-8") as f:
            return json.load(f).get("api_key", "")
    except Exception:
        return ""


def save_api_key(key: str):
    try:
        path = _config_path()
        existing = {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
        existing["api_key"] = key.strip()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[JARVIS] API key save error: {e}")
        return False


# ── Claude API call ───────────────────────────────────────────────────────────

def call_claude(api_key: str, user_message: str) -> str:
    if not api_key:
        return "❌ API key set nahi hai. Settings mein jao aur save karo."

    url = "https://api.anthropic.com/v1/messages"
    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": user_message}]
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        try:
            msg = json.loads(body).get("error", {}).get("message", body)
        except Exception:
            msg = body
        return f"❌ API Error {e.code}: {msg}"
    except Exception as e:
        return f"❌ Network error: {e}"


# ── Screens ───────────────────────────────────────────────────────────────────

class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._api_key = ""
        self._build_ui()

    def on_enter(self):
        # Screen par aate hi fresh key load karo
        self._api_key = load_api_key()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))

        # Title bar
        title_bar = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        title = Label(
            text="🤖 JARVIS",
            font_name=_EMOJI_FONT,
            font_size=dp(22),
            bold=True,
            size_hint_x=0.7,
        )
        settings_btn = Button(
            text="⚙️",
            font_name=_EMOJI_FONT,
            font_size=dp(22),
            size_hint_x=0.3,
        )
        settings_btn.bind(on_release=self._open_settings)
        title_bar.add_widget(title)
        title_bar.add_widget(settings_btn)
        root.add_widget(title_bar)

        # Chat history
        scroll = ScrollView(size_hint_y=0.75)
        self.chat_label = Label(
            text="Namaste! Main JARVIS hoon. Kuch poochho... 😊\n",
            font_name=_EMOJI_FONT,
            font_size=dp(15),
            size_hint_y=None,
            text_size=(None, None),
            halign="left",
            valign="top",
            markup=True,
            padding=(dp(6), dp(6)),
        )
        self.chat_label.bind(
            texture_size=lambda inst, val: setattr(inst, "size", val)
        )
        scroll.add_widget(self.chat_label)
        root.add_widget(scroll)

        # Input row
        input_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6))
        self.user_input = TextInput(
            hint_text="Message likho...",
            multiline=False,
            size_hint_x=0.8,
            font_size=dp(15),
        )
        self.user_input.bind(on_text_validate=self._send)
        send_btn = Button(
            text="➤",
            font_name=_EMOJI_FONT,
            font_size=dp(22),
            size_hint_x=0.2,
        )
        send_btn.bind(on_release=self._send)
        input_row.add_widget(self.user_input)
        input_row.add_widget(send_btn)
        root.add_widget(input_row)

        self.add_widget(root)

    def _open_settings(self, *_):
        self.manager.current = "settings"

    def _send(self, *_):
        msg = self.user_input.text.strip()
        if not msg:
            return
        self.user_input.text = ""
        self._append(f"[b]🧑 Aap:[/b] {msg}\n")
        self._append("⏳ Soch raha hoon...\n")
        Clock.schedule_once(lambda dt: self._do_api_call(msg), 0.1)

    def _do_api_call(self, msg):
        response = call_claude(self._api_key, msg)
        # Remove the "thinking" line and add response
        lines = self.chat_label.text.split("\n")
        lines = [l for l in lines if "⏳" not in l]
        self.chat_label.text = "\n".join(lines)
        self._append(f"[b]🤖 JARVIS:[/b] {response}\n\n")

    def _append(self, text):
        self.chat_label.text += text


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build_ui()

    def on_enter(self):
        # Settings khulte hi saved key dikhao
        self.key_input.text = load_api_key()
        self.status_label.text = ""

    def _build_ui(self):
        layout = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(14))

        layout.add_widget(Label(
            text="⚙️ Settings",
            font_name=_EMOJI_FONT,
            font_size=dp(24),
            bold=True,
            size_hint_y=None,
            height=dp(50),
        ))

        layout.add_widget(Label(
            text="Claude API Key:",
            font_size=dp(15),
            size_hint_y=None,
            height=dp(30),
            halign="left",
        ))

        self.key_input = TextInput(
            hint_text="sk-ant-...",
            password=False,
            multiline=False,
            font_size=dp(14),
            size_hint_y=None,
            height=dp(48),
        )
        layout.add_widget(self.key_input)

        save_btn = Button(
            text="💾 Save API Key",
            font_name=_EMOJI_FONT,
            font_size=dp(18),
            size_hint_y=None,
            height=dp(52),
            background_color=(0.2, 0.6, 1, 1),
        )
        save_btn.bind(on_release=self._save)
        layout.add_widget(save_btn)

        self.status_label = Label(
            text="",
            font_name=_EMOJI_FONT,
            font_size=dp(15),
            size_hint_y=None,
            height=dp(36),
        )
        layout.add_widget(self.status_label)

        back_btn = Button(
            text="← Wapas Chat Pe",
            font_size=dp(16),
            size_hint_y=None,
            height=dp(48),
            background_color=(0.3, 0.3, 0.3, 1),
        )
        back_btn.bind(on_release=self._go_back)
        layout.add_widget(back_btn)

        layout.add_widget(Label())  # spacer
        self.add_widget(layout)

    def _save(self, *_):
        key = self.key_input.text.strip()
        if not key:
            self.status_label.text = "❌ Key khali hai!"
            return
        if not key.startswith("sk-ant-"):
            self.status_label.text = "⚠️ Key 'sk-ant-' se shuru honi chahiye"
            return
        if save_api_key(key):
            self.status_label.text = "✅ API Key save ho gayi!"
        else:
            self.status_label.text = "❌ Save nahi hui — storage error"

    def _go_back(self, *_):
        self.manager.current = "chat"


# ── App entry point ───────────────────────────────────────────────────────────

class JarvisApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(ChatScreen(name="chat"))
        sm.add_widget(SettingsScreen(name="settings"))
        return sm


if __name__ == "__main__":
    JarvisApp().run()
