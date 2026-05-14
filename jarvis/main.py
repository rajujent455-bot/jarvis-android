"""
J.A.R.V.I.S Android v1.0
Kivy-based Android App — Full Featured
Fixes: urllib API call, FileChooser path, menu bug
"""

import os, json, datetime, threading, re, time
import urllib.request, urllib.parse, html
from pathlib import Path

os.environ['KIVY_NO_ENV_CONFIG'] = '1'

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, BooleanProperty

try:
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    IS_ANDROID = True
except ImportError:
    IS_ANDROID = False

# ── Paths ─────────────────────────────────────────────────────────────────────
if IS_ANDROID:
    BASE_DIR = Path(primary_external_storage_path()) / "JARVIS"
else:
    BASE_DIR = Path.home() / "JARVIS"

REPORTS_DIR = BASE_DIR / "Reports"
FILES_DIR   = BASE_DIR / "Files"
CONFIG_FILE = BASE_DIR / "config.json"

for d in [BASE_DIR, REPORTS_DIR, FILES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Colors ────────────────────────────────────────────────────────────────────
C = {
    "bg":       "#080c1a",
    "bar":      "#0a0e20",
    "fg":       "#c8d8f8",
    "accent":   "#00e5ff",
    "accent2":  "#7c4dff",
    "btn":      "#0d47a1",
    "btn2":     "#1565c0",
    "success":  "#00e676",
    "warn":     "#ff5252",
    "card":     "#0e1428",
    "border":   "#1a2a5a",
    "tag_j":    "#00e5ff",
    "tag_u":    "#82b1ff",
    "tag_a":    "#69f0ae",
    "tag_e":    "#ff5252",
    "sidebar":  "#0d1226",
    "input_bg": "#101428",
}

def c(key): return get_color_from_hex(C.get(key, "#ffffff"))

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULTS = {
    "api_key": "", "name": "Sir", "gmail": "",
    "gmail_pass": "", "theme": "dark", "font_size": 14
}

def load_cfg():
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            for k, v in DEFAULTS.items():
                cfg.setdefault(k, v)
            return cfg
        except: pass
    return DEFAULTS.copy()

def save_cfg(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

CFG = load_cfg()

# ══════════════════════════════════════════════════════════════════
# CLAUDE API — Direct urllib (no SDK, works on Android)
# ══════════════════════════════════════════════════════════════════

def call_claude(messages, system_prompt, api_key):
    """Anthropic API ko seedha urllib se call karo — SDK nahi chahiye."""
    data = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "system": system_prompt,
        "messages": messages
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read().decode())
        return result["content"][0]["text"]


# ══════════════════════════════════════════════════════════════════
# BACKEND CLASSES
# ══════════════════════════════════════════════════════════════════

class Search:
    @staticmethod
    def raw(query: str) -> str:
        try:
            url = "https://api.duckduckgo.com/?q={}&format=json&no_html=1&skip_disambig=1".format(
                urllib.parse.quote(query))
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                d = json.loads(r.read().decode())
            out = []
            if d.get("Abstract"): out.append("Summary: " + d["Abstract"][:500])
            for t in d.get("RelatedTopics", [])[:4]:
                if isinstance(t, dict) and t.get("Text"):
                    out.append("• " + t["Text"][:200])
            if out: return "\n".join(out)
        except: pass
        return "Search result nahi mila."

    @staticmethod
    def smart(query: str, api_key: str) -> str:
        raw = Search.raw(query)
        if not api_key: return raw
        try:
            reply = call_claude(
                messages=[{"role": "user", "content":
                    f'Problem: "{query}"\n\nResults:\n{raw}\n\nHindi mein best solution do. Step-by-step.'}],
                system_prompt="Tu ek helpful assistant hai. Hindi mein jawab do.",
                api_key=api_key
            )
            return reply
        except Exception as e:
            return raw


class Weather:
    @staticmethod
    def get(city: str) -> str:
        try:
            city_enc = urllib.parse.quote(city or "Udaipur")
            url = f"https://wttr.in/{city_enc}?format=j1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                d = json.loads(r.read().decode())
            cc = d["current_condition"][0]
            area = d["nearest_area"][0]["areaName"][0]["value"]
            return (f"🌤 {area}\n"
                    f"🌡 {cc['temp_C']}°C (Feels {cc['FeelsLikeC']}°C)\n"
                    f"☁ {cc['weatherDesc'][0]['value']}\n"
                    f"💧 Humidity: {cc['humidity']}%\n"
                    f"🌬 Wind: {cc['windspeedKmph']} km/h")
        except Exception as e:
            return f"Weather error: {e}"


class News:
    @staticmethod
    def get(topic: str) -> str:
        try:
            q = urllib.parse.quote(topic or "India today")
            url = f"https://api.duckduckgo.com/?q={q}+news&format=json&no_html=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                d = json.loads(r.read().decode())
            items = []
            if d.get("Abstract"): items.append("📰 " + d["Abstract"][:400])
            for t in d.get("RelatedTopics", [])[:5]:
                if isinstance(t, dict) and t.get("Text"):
                    items.append("• " + t["Text"][:200])
            return "\n".join(items) if items else "Koi news nahi mili."
        except Exception as e:
            return f"News error: {e}"


class Files:
    @staticmethod
    def run(inst: str) -> str:
        low = inst.lower()
        if any(w in low for w in ["list", "dikhao", "sab"]):
            return Files._list()
        if any(w in low for w in ["delete", "hatao"]):
            return Files._del(inst)
        if any(w in low for w in ["read", "padho"]):
            return Files._read(inst)
        return Files._create(inst)

    @staticmethod
    def _create(inst):
        m = re.search(r'["\'](.*?)["\']|(\w[\w\-]*\.(?:txt|py|csv|md|json))', inst, re.I)
        fname = (m.group(1) or m.group(2)) if m else \
                f"note_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt"
        if "." not in fname: fname += ".txt"
        fp = FILES_DIR / fname
        cm = re.search(r'(?:content|likho|write)[:\s]+(.+)', inst, re.I | re.S)
        body = cm.group(1).strip() if cm else inst
        fp.write_text(f"JARVIS\n{'='*40}\n\n{body}", encoding="utf-8")
        return f"✅ File banayi: {fname}"

    @staticmethod
    def _read(inst):
        m = re.search(r'["\'](.*?)["\']|(\w[\w\-]*\.(?:txt|py|csv|md|json))', inst, re.I)
        if m:
            fp = FILES_DIR / (m.group(1) or m.group(2))
            if fp.exists():
                return fp.read_text(encoding="utf-8")[:2000]
        return Files._list()

    @staticmethod
    def _del(inst):
        m = re.search(r'["\'](.*?)["\']|(\w[\w\-]*\.(?:txt|py|csv|md|json))', inst, re.I)
        if m:
            fp = FILES_DIR / (m.group(1) or m.group(2))
            if fp.exists():
                fp.unlink()
                return f"🗑 Deleted: {fp.name}"
        return "Kaun si file? Naam batao."

    @staticmethod
    def _list():
        items = [f"📄 {f.name}" for f in FILES_DIR.glob("*") if f.is_file()]
        return ("Files:\n" + "\n".join(items)) if items else "Koi file nahi."


class Report:
    @staticmethod
    def save(content: str) -> str:
        now = datetime.datetime.now()
        fp  = REPORTS_DIR / now.strftime("Report_%Y-%m-%d.txt")
        hdr = f"{'='*40}\n  JARVIS REPORT\n  {now:%d %B %Y}\n{'='*40}\n\n"
        if fp.exists():
            fp.write_text(fp.read_text(encoding="utf-8") +
                f"\n\n--- {now:%H:%M} ---\n{content}", encoding="utf-8")
        else:
            fp.write_text(hdr + content, encoding="utf-8")
        return f"📊 Report save ki: {fp.name}"


class SysInfo:
    @staticmethod
    def get() -> str:
        info = [f"📱 JARVIS Android v1.0",
                f"📅 {datetime.datetime.now():%d %B %Y, %I:%M %p}",
                f"📁 Base: {BASE_DIR}"]
        try:
            import psutil
            info.append(f"💻 CPU: {psutil.cpu_percent()}%")
            m = psutil.virtual_memory()
            info.append(f"🧠 RAM: {m.used//1024**2}MB/{m.total//1024**2}MB")
        except: pass
        return "\n".join(info)


class PDFTools:
    @staticmethod
    def info(path: str) -> str:
        try:
            from pypdf import PdfReader
            r = PdfReader(path)
            meta = r.metadata or {}
            lines = [
                f"📄 File: {Path(path).name}",
                f"📃 Pages: {len(r.pages)}",
                f"🔒 Encrypted: {'Yes' if r.is_encrypted else 'No'}",
            ]
            for k, v in meta.items():
                if v: lines.append(f"  {str(k).replace('/','')}: {str(v)[:60]}")
            root = r.trailer.get("/Root", {})
            if "/AcroForm" in root:
                acro = root["/AcroForm"]
                if "/Fields" in acro:
                    lines.append("🔐 Digital Signature: Found")
            return "\n".join(lines)
        except Exception as e:
            return f"PDF info error: {e}"

    @staticmethod
    def extract_text(path: str) -> str:
        try:
            from pypdf import PdfReader
            r = PdfReader(path)
            text = ""
            for i, page in enumerate(r.pages):
                text += f"\n\n--- Page {i+1} ---\n"
                text += page.extract_text() or "(no text)"
            out = FILES_DIR / (Path(path).stem + "_text.txt")
            out.write_text(text, encoding="utf-8")
            return f"✅ Text extract hua!\nSaved: {out.name}\n\nPreview:\n{text[:500]}..."
        except Exception as e:
            return f"Extract error: {e}"

    @staticmethod
    def merge(paths: list) -> str:
        try:
            from pypdf import PdfWriter, PdfReader
            writer = PdfWriter()
            for p in paths:
                for page in PdfReader(p).pages:
                    writer.add_page(page)
            out = FILES_DIR / f"Merged_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf"
            with open(out, "wb") as f:
                writer.write(f)
            return f"✅ {len(paths)} PDFs merge huyi!\nSaved: {out.name}"
        except Exception as e:
            return f"Merge error: {e}"


def get_prompt():
    now = datetime.datetime.now().strftime("%A, %d %B %Y, %I:%M %p")
    return f"""Tu J.A.R.V.I.S Android v1.0 hai — {CFG['name']} ka personal AI assistant.
Aaj: {now}

Tu ye kaam karta hai:
1. FILES: Create, read, delete files
2. REPORTS: Reports save karo
3. WEB SEARCH: Internet search
4. SYSTEM: Phone/device info
5. WEATHER: Mausam batao
6. NEWS: Latest news
7. REMINDER: Reminder set karo
8. PDF: PDF info, text extract

Action format:
  ACTION:FILE:<instruction>
  ACTION:REPORT:<content>
  ACTION:SYSTEM:info
  ACTION:SEARCH:<query>
  ACTION:WEATHER:<city>
  ACTION:NEWS:<topic>
  ACTION:REMINDER:<minutes>|<text>

Phir Hindi/Hinglish mein explain karo.
Hamesha "{CFG['name']}" bolo. Short aur helpful raho."""


def do_actions(text: str, api_key: str, log_fn=None) -> str:
    results = []
    for line in text.split("\n"):
        l = line.strip()
        if l.startswith("ACTION:FILE:"):
            results.append(Files.run(l[12:]))
        elif l.startswith("ACTION:REPORT:"):
            results.append(Report.save(l[14:]))
        elif l.startswith("ACTION:SYSTEM:"):
            results.append(SysInfo.get())
        elif l.startswith("ACTION:SEARCH:"):
            results.append(Search.smart(l[14:], api_key))
        elif l.startswith("ACTION:WEATHER:"):
            results.append(Weather.get(l[15:]))
        elif l.startswith("ACTION:NEWS:"):
            results.append(News.get(l[12:]))
        elif l.startswith("ACTION:REMINDER:"):
            p = l[16:].split("|", 1)
            try: mins = int(p[0].strip())
            except: mins = 5
            txt = p[1].strip() if len(p) > 1 else "Reminder!"
            if log_fn:
                Clock.schedule_once(lambda dt, m=txt: log_fn("⏰ " + m), mins * 60)
            results.append(f"⏰ Reminder set: {mins} min baad — {txt}")
    return "\n\n".join(r for r in results if r)


# ══════════════════════════════════════════════════════════════════
# UI WIDGETS
# ══════════════════════════════════════════════════════════════════

class JarvisButton(Button):
    def __init__(self, **kwargs):
        bg = kwargs.pop("bg_color", C["btn"])
        radius = kwargs.pop("radius", 10)
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.color = c("accent")
        self.font_size = sp(13)
        self.bold = True
        self.size_hint_y = None
        self.height = dp(44)
        self._bg_color = bg
        self._radius = radius
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*get_color_from_hex(self._bg_color))
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[self._radius])


class JarvisInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = get_color_from_hex(C["input_bg"])
        self.foreground_color = c("fg")
        self.cursor_color     = c("accent")
        self.hint_text_color  = get_color_from_hex("#4a5a7a")
        self.font_size        = sp(13)
        self.padding          = [dp(12), dp(10)]


# ══════════════════════════════════════════════════════════════════
# SCREENS
# ══════════════════════════════════════════════════════════════════

class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.history = []
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical", spacing=0, padding=0)
        with root.canvas.before:
            Color(*c("bg"))
            self._bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda w, v: setattr(self._bg_rect, 'pos', v),
                  size=lambda w, v: setattr(self._bg_rect, 'size', v))

        # Header
        hdr = BoxLayout(size_hint_y=None, height=dp(56),
                        padding=[dp(14), dp(8)], spacing=dp(10))
        with hdr.canvas.before:
            Color(*c("bar"))
            hdr_rect = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda w, v: setattr(hdr_rect, 'pos', v),
                 size=lambda w, v: setattr(hdr_rect, 'size', v))

        title = Label(text="◈ J.A.R.V.I.S", font_size=sp(18), bold=True,
                      color=c("accent"), size_hint_x=0.6,
                      halign="left", valign="middle")
        title.bind(size=title.setter("text_size"))

        menu_btn = JarvisButton(text="☰", size_hint_x=None, width=dp(42),
                                height=dp(40), bg_color=C["sidebar"])
        menu_btn.bind(on_press=lambda *a: self.manager.app_ref.open_menu())

        settings_btn = JarvisButton(text="⚙", size_hint_x=None, width=dp(42),
                                    height=dp(40), bg_color=C["sidebar"])
        settings_btn.bind(on_press=lambda *a:
            setattr(self.manager, "current", "settings"))

        hdr.add_widget(title)
        hdr.add_widget(menu_btn)
        hdr.add_widget(settings_btn)
        root.add_widget(hdr)

        # Chat scroll area
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self._chat_layout = BoxLayout(orientation="vertical",
                                      size_hint_y=None, spacing=dp(8),
                                      padding=[dp(10), dp(10)])
        self._chat_layout.bind(minimum_height=self._chat_layout.setter("height"))
        scroll.add_widget(self._chat_layout)
        self._scroll = scroll
        root.add_widget(scroll)

        # Quick actions bar
        qa = BoxLayout(size_hint_y=None, height=dp(46),
                       spacing=dp(4), padding=[dp(6), dp(4)])
        with qa.canvas.before:
            Color(*c("sidebar"))
            qa_rect = Rectangle(pos=qa.pos, size=qa.size)
        qa.bind(pos=lambda w, v: setattr(qa_rect, 'pos', v),
                size=lambda w, v: setattr(qa_rect, 'size', v))

        for lbl, cmd in [("🌤", "Udaipur ka mausam batao"),
                          ("📰", "Aaj ki India news do"),
                          ("💻", "System info do"),
                          ("📊", "Aaj ka report banao"),
                          ("📄", "PDF tools batao"),
                          ("🔍", "Web search karo")]:
            b = JarvisButton(text=lbl, size_hint_x=None, width=dp(46),
                             height=dp(36), bg_color=C["bar"],
                             radius=8, font_size=sp(16))
            b.bind(on_press=lambda btn, c_=cmd: self._quick_send(c_))
            qa.add_widget(b)
        root.add_widget(qa)

        # Input row
        inp_row = BoxLayout(size_hint_y=None, height=dp(56),
                            spacing=dp(6), padding=[dp(8), dp(6)])
        with inp_row.canvas.before:
            Color(*c("bar"))
            inp_rect = Rectangle(pos=inp_row.pos, size=inp_row.size)
        inp_row.bind(pos=lambda w, v: setattr(inp_rect, 'pos', v),
                     size=lambda w, v: setattr(inp_rect, 'size', v))

        self._entry = JarvisInput(
            hint_text=f"Kuch poochho {CFG.get('name','Sir')}...",
            multiline=False, size_hint_x=1)
        self._entry.bind(on_text_validate=self._send)

        send_btn = JarvisButton(text="▶", size_hint_x=None,
                                width=dp(50), bg_color=C["btn2"])
        send_btn.bind(on_press=self._send)

        voice_btn = JarvisButton(text="🎤", size_hint_x=None,
                                 width=dp(50), bg_color=C["sidebar"])
        voice_btn.bind(on_press=self._voice)

        inp_row.add_widget(self._entry)
        inp_row.add_widget(voice_btn)
        inp_row.add_widget(send_btn)
        root.add_widget(inp_row)

        self.add_widget(root)

        Clock.schedule_once(lambda dt: self._add_msg(
            "◈ JARVIS",
            f"Namaste {CFG.get('name','Sir')}! Main J.A.R.V.I.S hoon.\n"
            f"API key settings mein daalna na bhoolen! 🚀",
            C["tag_j"]), 0.5)

    def _quick_send(self, cmd):
        self._entry.text = cmd
        self._send()

    def _add_msg(self, sender, text, color_hex=None):
        color = color_hex or C["fg"]
        box = BoxLayout(orientation="vertical", size_hint_y=None,
                        padding=[dp(10), dp(6)], spacing=dp(2))

        s_lbl = Label(
            text=f"{sender}  [{datetime.datetime.now():%H:%M}]",
            font_size=sp(10), bold=True,
            color=get_color_from_hex(color),
            size_hint_y=None, height=dp(18),
            halign="left", valign="middle")
        s_lbl.bind(size=s_lbl.setter("text_size"))

        m_lbl = Label(text=text, font_size=sp(13), color=c("fg"),
                      size_hint_y=None, halign="left", valign="top")
        m_lbl.bind(width=lambda w, val: setattr(w, "text_size", (val, None)))
        m_lbl.bind(texture_size=lambda w, s: setattr(w, "height", s[1] + dp(4)))

        box.add_widget(s_lbl)
        box.add_widget(m_lbl)

        with box.canvas.before:
            Color(*get_color_from_hex(C["card"]))
            box_rect = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(8)])
        box.bind(pos=lambda w, v: setattr(box_rect, 'pos', v),
                 size=lambda w, v: setattr(box_rect, 'size', v))
        box.bind(minimum_height=box.setter("height"))

        self._chat_layout.add_widget(box)
        Clock.schedule_once(lambda dt: setattr(self._scroll, "scroll_y", 0), 0.1)

    def _send(self, *a):
        txt = self._entry.text.strip()
        if not txt: return
        self._entry.text = ""
        self._add_msg(f"▶ {CFG.get('name','You')}", txt, C["tag_u"])
        self._add_msg("◈ JARVIS", "🔄 Soch raha hoon...", C["tag_j"])
        threading.Thread(target=self._ai_call, args=(txt,), daemon=True).start()

    def _ai_call(self, user_msg):
        api_key = CFG.get("api_key", "")
        if not api_key:
            Clock.schedule_once(lambda dt: self._replace_last(
                "⚠ API key nahi hai! Settings mein daalo."), 0)
            return
        try:
            self.history.append({"role": "user", "content": user_msg})
            if len(self.history) > 20:
                self.history = self.history[-20:]

            reply = call_claude(
                messages=self.history,
                system_prompt=get_prompt(),
                api_key=api_key
            )

            self.history.append({"role": "assistant", "content": reply})

            action_result = do_actions(
                reply, api_key,
                log_fn=lambda m: Clock.schedule_once(
                    lambda dt, msg=m: self._add_msg("⚡", msg, C["tag_a"]), 0))

            display = "\n".join(l for l in reply.split("\n")
                                if not l.strip().startswith("ACTION:"))
            if action_result:
                display = display.strip() + f"\n\n⚡ {action_result}"

            Clock.schedule_once(lambda dt, d=display: self._replace_last(d), 0)

        except Exception as e:
            Clock.schedule_once(
                lambda dt: self._replace_last(f"❌ Error: {e}"), 0)

    def _replace_last(self, text):
        children = self._chat_layout.children
        if children:
            last = children[0]
            labels = [w for w in last.children if isinstance(w, Label)]
            for lbl in labels:
                if "Soch" in lbl.text or "🔄" in lbl.text:
                    lbl.text = text
                    return
        self._add_msg("◈ JARVIS", text, C["tag_j"])

    def _voice(self, *a):
        self._add_msg("⚡", "🎤 Voice feature coming soon!", C["tag_a"])


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            Color(*c("bg"))
            bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda w, v: setattr(bg_rect, 'pos', v),
                  size=lambda w, v: setattr(bg_rect, 'size', v))

        hdr = BoxLayout(size_hint_y=None, height=dp(56),
                        padding=[dp(14), dp(8)])
        with hdr.canvas.before:
            Color(*c("bar"))
            hdr_rect = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda w, v: setattr(hdr_rect, 'pos', v),
                 size=lambda w, v: setattr(hdr_rect, 'size', v))

        back = JarvisButton(text="← Back", size_hint_x=None,
                            width=dp(80), bg_color=C["sidebar"])
        back.bind(on_press=lambda *a: setattr(self.manager, "current", "chat"))
        hdr.add_widget(back)
        hdr.add_widget(Label(text="⚙  Settings", font_size=sp(16),
                             bold=True, color=c("accent")))
        root.add_widget(hdr)

        sv = ScrollView()
        sl = BoxLayout(orientation="vertical", size_hint_y=None,
                       padding=dp(14), spacing=dp(12))
        sl.bind(minimum_height=sl.setter("height"))

        def field(label, key, pw=False):
            sl.add_widget(Label(text=label, font_size=sp(11),
                                color=c("accent"), size_hint_y=None,
                                height=dp(22), halign="left",
                                text_size=(Window.width - dp(28), None)))
            inp = JarvisInput(text=str(CFG.get(key, "")),
                              password=pw, multiline=False,
                              size_hint_y=None, height=dp(42))
            sl.add_widget(inp)
            return inp

        self._api   = field("🔑 Anthropic API Key", "api_key", pw=True)
        self._name  = field("👤 Aapka Naam", "name")
        self._gmail = field("📧 Gmail ID", "gmail")
        self._gpass = field("🔒 Gmail App Password", "gmail_pass", pw=True)

        save_btn = JarvisButton(text="💾  SAVE SETTINGS",
                                bg_color=C["btn2"],
                                size_hint_y=None, height=dp(50))
        save_btn.bind(on_press=self._save)
        sl.add_widget(Label(size_hint_y=None, height=dp(10)))
        sl.add_widget(save_btn)

        about = Label(
            text="J.A.R.V.I.S Android v1.0\nPowered by Claude AI\nBuilt with Kivy + Python",
            font_size=sp(10), color=c("border"),
            size_hint_y=None, height=dp(60), halign="center")
        sl.add_widget(about)

        sv.add_widget(sl)
        root.add_widget(sv)
        self.add_widget(root)

    def _save(self, *a):
        CFG["api_key"]    = self._api.text.strip()
        CFG["name"]       = self._name.text.strip() or "Sir"
        CFG["gmail"]      = self._gmail.text.strip()
        CFG["gmail_pass"] = self._gpass.text.strip()
        save_cfg(CFG)
        popup = Popup(
            title="✅ Saved!",
            content=Label(text="Settings save ho gayi!\nJARVIS restart karo.",
                          color=c("fg")),
            size_hint=(0.7, 0.3))
        popup.open()


class PDFScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            Color(*c("bg"))
            bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda w, v: setattr(bg_rect, 'pos', v),
                  size=lambda w, v: setattr(bg_rect, 'size', v))

        hdr = BoxLayout(size_hint_y=None, height=dp(56),
                        padding=[dp(14), dp(8)])
        with hdr.canvas.before:
            Color(*c("bar"))
            hdr_rect = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda w, v: setattr(hdr_rect, 'pos', v),
                 size=lambda w, v: setattr(hdr_rect, 'size', v))

        back = JarvisButton(text="← Back", size_hint_x=None,
                            width=dp(80), bg_color=C["sidebar"])
        back.bind(on_press=lambda *a: setattr(self.manager, "current", "chat"))
        hdr.add_widget(back)
        hdr.add_widget(Label(text="📄  PDF Manager", font_size=sp(16),
                             bold=True, color=c("accent")))
        root.add_widget(hdr)

        # FIX: Android pe sahi path
        if IS_ANDROID:
            from android.storage import primary_external_storage_path
            start_path = primary_external_storage_path()
        else:
            start_path = str(Path.home())

        self._fc = FileChooserListView(path=start_path,
                                       filters=["*.pdf"],
                                       size_hint_y=0.45)
        root.add_widget(self._fc)

        sv = ScrollView(size_hint_y=0.3)
        self._result = Label(
            text="PDF select karo upar se, phir action choose karo.",
            font_size=sp(12), color=c("fg"),
            size_hint_y=None, halign="left", valign="top",
            padding=(dp(10), dp(6)))
        self._result.bind(
            width=lambda w, v: setattr(w, "text_size", (v, None)))
        self._result.bind(
            texture_size=lambda w, s: setattr(w, "height", s[1] + dp(10)))
        sv.add_widget(self._result)
        root.add_widget(sv)

        btn_row = GridLayout(cols=2, size_hint_y=None, height=dp(110),
                             spacing=dp(6), padding=[dp(8), dp(4)])
        for lbl, fn, col in [
            ("📋 Info",         self._info,         C["btn"]),
            ("📝 Extract Text", self._extract,       C["btn2"]),
            ("🔗 Merge PDFs",   self._merge,         "#1b5e20"),
            ("🔍 Search PDF",   self._search_in_pdf, "#4a148c"),
        ]:
            b = JarvisButton(text=lbl, bg_color=col,
                             size_hint_y=None, height=dp(46))
            b.bind(on_press=lambda btn, f=fn: f())
            btn_row.add_widget(b)
        root.add_widget(btn_row)
        self.add_widget(root)

    def _get_selected(self):
        sel = self._fc.selection
        if not sel:
            self._result.text = "⚠ Pehle PDF file select karo!"
            return None
        return sel[0]

    def _info(self):
        path = self._get_selected()
        if path:
            threading.Thread(target=lambda: Clock.schedule_once(
                lambda dt: setattr(self._result, "text",
                                   PDFTools.info(path)), 0), daemon=True).start()

    def _extract(self):
        path = self._get_selected()
        if path:
            self._result.text = "⏳ Text extract ho raha hai..."
            threading.Thread(target=lambda: Clock.schedule_once(
                lambda dt: setattr(self._result, "text",
                                   PDFTools.extract_text(path)), 0), daemon=True).start()

    def _merge(self):
        sel = self._fc.selection
        if len(sel) < 2:
            self._result.text = "⚠ Kam se kam 2 PDFs select karo!"
            return
        self._result.text = "⏳ Merge ho raha hai..."
        threading.Thread(target=lambda: Clock.schedule_once(
            lambda dt: setattr(self._result, "text",
                               PDFTools.merge(sel)), 0), daemon=True).start()

    def _search_in_pdf(self):
        path = self._get_selected()
        if not path: return
        content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        inp = JarvisInput(hint_text="Search karna kya hai?",
                          size_hint_y=None, height=dp(44))
        popup = Popup(title="🔍 PDF Search", content=content,
                      size_hint=(0.85, 0.3))

        def do_search(*a):
            keyword = inp.text.strip()
            if not keyword: return
            popup.dismiss()
            self._result.text = f"🔍 '{keyword}' dhoondh raha hoon..."
            threading.Thread(target=self._run_search,
                             args=(path, keyword), daemon=True).start()

        btn = JarvisButton(text="Search", bg_color=C["btn2"])
        btn.bind(on_press=do_search)
        content.add_widget(inp)
        content.add_widget(btn)
        popup.open()

    def _run_search(self, path, keyword):
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            found = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if keyword.lower() in text.lower():
                    idx = text.lower().find(keyword.lower())
                    snippet = text[max(0, idx-50):idx+100].strip()
                    found.append(f"Page {i+1}: ...{snippet}...")
            if found:
                result = f"✅ '{keyword}' mila {len(found)} pages pe:\n\n" + "\n\n".join(found)
            else:
                result = f"❌ '{keyword}' nahi mila is PDF mein."
            Clock.schedule_once(lambda dt: setattr(self._result, "text", result), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(
                self._result, "text", f"Search error: {e}"), 0)


class FilesScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            Color(*c("bg"))
            bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda w, v: setattr(bg_rect, 'pos', v),
                  size=lambda w, v: setattr(bg_rect, 'size', v))

        hdr = BoxLayout(size_hint_y=None, height=dp(56),
                        padding=[dp(14), dp(8)])
        with hdr.canvas.before:
            Color(*c("bar"))
            hdr_rect = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda w, v: setattr(hdr_rect, 'pos', v),
                 size=lambda w, v: setattr(hdr_rect, 'size', v))

        back = JarvisButton(text="← Back", size_hint_x=None,
                            width=dp(80), bg_color=C["sidebar"])
        back.bind(on_press=lambda *a: setattr(self.manager, "current", "chat"))
        hdr.add_widget(back)
        hdr.add_widget(Label(text="📁  JARVIS Files", font_size=sp(16),
                             bold=True, color=c("accent")))
        root.add_widget(hdr)

        self._fc = FileChooserListView(path=str(FILES_DIR), size_hint_y=0.65)
        root.add_widget(self._fc)

        btn_row = GridLayout(cols=2, size_hint_y=None, height=dp(56),
                             spacing=dp(6), padding=[dp(8), dp(4)])
        read_btn = JarvisButton(text="📖 Read File", bg_color=C["btn"])
        read_btn.bind(on_press=self._read_file)
        del_btn = JarvisButton(text="🗑 Delete", bg_color="#b71c1c")
        del_btn.bind(on_press=self._del_file)
        btn_row.add_widget(read_btn)
        btn_row.add_widget(del_btn)
        root.add_widget(btn_row)

        sv = ScrollView(size_hint_y=0.25)
        self._result = Label(text="File select karo.", font_size=sp(12),
                             color=c("fg"), size_hint_y=None,
                             halign="left", valign="top")
        self._result.bind(
            width=lambda w, v: setattr(w, "text_size", (v, None)))
        self._result.bind(
            texture_size=lambda w, s: setattr(w, "height", s[1] + dp(10)))
        sv.add_widget(self._result)
        root.add_widget(sv)
        self.add_widget(root)

    def _read_file(self, *a):
        sel = self._fc.selection
        if not sel:
            self._result.text = "⚠ File select karo!"
            return
        try:
            self._result.text = Path(sel[0]).read_text(encoding="utf-8")[:1000]
        except Exception as e:
            self._result.text = f"Read error: {e}"

    def _del_file(self, *a):
        sel = self._fc.selection
        if not sel:
            self._result.text = "⚠ File select karo!"
            return
        try:
            Path(sel[0]).unlink()
            self._result.text = f"✅ Deleted: {Path(sel[0]).name}"
            self._fc._update_files()
        except Exception as e:
            self._result.text = f"Delete error: {e}"


# ══════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════

class JarvisApp(App):
    def build(self):
        Window.clearcolor = get_color_from_hex(C["bg"])

        if IS_ANDROID:
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.INTERNET,
                Permission.RECORD_AUDIO,
            ])

        self.sm = ScreenManager(transition=SlideTransition())
        self.sm.app_ref = self

        self.sm.add_widget(ChatScreen(name="chat"))
        self.sm.add_widget(SettingsScreen(name="settings"))
        self.sm.add_widget(PDFScreen(name="pdf"))
        self.sm.add_widget(FilesScreen(name="files"))

        return self.sm

    def open_menu(self):
        content = BoxLayout(orientation="vertical",
                            spacing=dp(8), padding=dp(12))
        popup = Popup(title="◈ JARVIS Menu", content=content,
                      size_hint=(0.75, 0.55),
                      background_color=get_color_from_hex(C["bar"]),
                      title_color=get_color_from_hex(C["accent"]))

        for lbl, screen in [
            ("💬  Chat",        "chat"),
            ("📄  PDF Manager", "pdf"),
            ("📁  Files",       "files"),
            ("⚙   Settings",   "settings"),
        ]:
            b = JarvisButton(text=lbl, bg_color=C["card"],
                             size_hint_y=None, height=dp(48))
            b.color = get_color_from_hex(C["accent"])
            b.bind(on_press=lambda btn, s=screen, p=popup:
                   (p.dismiss(), setattr(self.sm, "current", s)))
            content.add_widget(b)

        popup.open()

    def get_application_name(self):
        return "JARVIS"


if __name__ == "__main__":
    JarvisApp().run()
