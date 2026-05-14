"""
J.A.R.V.I.S Android v1.0
"""

import os, json, datetime, threading, re
import urllib.request, urllib.parse
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
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, RoundedRectangle, Rectangle

try:
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    IS_ANDROID = True
except ImportError:
    IS_ANDROID = False

# ── Paths — safely set karo ───────────────────────────────────────
def get_base_dir():
    try:
        if IS_ANDROID:
            base = Path(primary_external_storage_path()) / "JARVIS"
        else:
            base = Path.home() / "JARVIS"
        return base
    except:
        return Path("/sdcard/JARVIS") if IS_ANDROID else Path.home() / "JARVIS"

def init_dirs():
    try:
        base = get_base_dir()
        for d in [base, base / "Reports", base / "Files"]:
            d.mkdir(parents=True, exist_ok=True)
        return base
    except Exception as e:
        # Internal storage fallback
        try:
            base = Path("/data/data/org.jarvis/files/JARVIS")
            for d in [base, base / "Reports", base / "Files"]:
                d.mkdir(parents=True, exist_ok=True)
            return base
        except:
            return Path("/sdcard/JARVIS")

# Global paths — app start pe set honge
BASE_DIR = None
REPORTS_DIR = None
FILES_DIR = None
CONFIG_FILE = None

# ── Colors ────────────────────────────────────────────────────────
C = {
    "bg":       "#080c1a",
    "bar":      "#0a0e20",
    "fg":       "#c8d8f8",
    "accent":   "#00e5ff",
    "btn":      "#0d47a1",
    "btn2":     "#1565c0",
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

# ── Config ────────────────────────────────────────────────────────
DEFAULTS = {
    "api_key": "", "name": "Sir", "gmail": "",
    "gmail_pass": "", "font_size": 14
}

def load_cfg():
    try:
        if CONFIG_FILE and CONFIG_FILE.exists():
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            for k, v in DEFAULTS.items():
                cfg.setdefault(k, v)
            return cfg
    except: pass
    return DEFAULTS.copy()

def save_cfg(cfg):
    try:
        if CONFIG_FILE:
            CONFIG_FILE.write_text(
                json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except: pass

CFG = DEFAULTS.copy()

# ── Claude API ────────────────────────────────────────────────────
def call_claude(messages, system_prompt, api_key):
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
        return json.loads(r.read().decode())["content"][0]["text"]

# ── Backend ───────────────────────────────────────────────────────
class Search:
    @staticmethod
    def raw(query):
        try:
            url = "https://api.duckduckgo.com/?q={}&format=json&no_html=1&skip_disambig=1".format(
                urllib.parse.quote(query))
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                d = json.loads(r.read().decode())
            out = []
            if d.get("Abstract"): out.append(d["Abstract"][:500])
            for t in d.get("RelatedTopics", [])[:3]:
                if isinstance(t, dict) and t.get("Text"):
                    out.append("• " + t["Text"][:200])
            return "\n".join(out) if out else "Result nahi mila."
        except Exception as e:
            return f"Search error: {e}"

class Weather:
    @staticmethod
    def get(city):
        try:
            url = f"https://wttr.in/{urllib.parse.quote(city or 'Udaipur')}?format=j1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                d = json.loads(r.read().decode())
            cc = d["current_condition"][0]
            area = d["nearest_area"][0]["areaName"][0]["value"]
            return (f"🌤 {area}\n🌡 {cc['temp_C']}°C\n"
                    f"☁ {cc['weatherDesc'][0]['value']}\n"
                    f"💧 {cc['humidity']}% | 🌬 {cc['windspeedKmph']} km/h")
        except Exception as e:
            return f"Weather error: {e}"

class Files:
    @staticmethod
    def list_files():
        try:
            items = [f"📄 {f.name}" for f in FILES_DIR.glob("*") if f.is_file()]
            return ("Files:\n" + "\n".join(items)) if items else "Koi file nahi."
        except: return "Files folder access nahi hua."

    @staticmethod
    def create(name, content):
        try:
            fp = FILES_DIR / (name if "." in name else name + ".txt")
            fp.write_text(f"JARVIS\n{'='*30}\n\n{content}", encoding="utf-8")
            return f"✅ File banayi: {fp.name}"
        except Exception as e:
            return f"File error: {e}"

class SysInfo:
    @staticmethod
    def get():
        info = [f"📱 JARVIS Android v1.0",
                f"📅 {datetime.datetime.now():%d %B %Y, %I:%M %p}"]
        if BASE_DIR:
            info.append(f"📁 {BASE_DIR}")
        return "\n".join(info)

def get_prompt():
    now = datetime.datetime.now().strftime("%d %B %Y, %I:%M %p")
    name = CFG.get('name', 'Sir')
    return f"""Tu JARVIS Android hai — {name} ka assistant. Aaj: {now}
Kaam:
ACTION:SEARCH:<query> — web search
ACTION:WEATHER:<city> — mausam  
ACTION:SYSTEM:info — device info
ACTION:FILE:list — files list
ACTION:FILE:create:<name>|<content> — file banao

Phir Hindi mein explain karo. Short raho."""

def do_actions(text, api_key, log_fn=None):
    results = []
    for line in text.split("\n"):
        l = line.strip()
        try:
            if l.startswith("ACTION:SEARCH:"):
                raw = Search.raw(l[14:])
                if api_key:
                    try:
                        r = call_claude(
                            [{"role":"user","content":f'Query: {l[14:]}\nResults: {raw}\nHindi mein short answer do.'}],
                            "Tu helpful assistant hai.", api_key)
                        results.append(r)
                    except: results.append(raw)
                else: results.append(raw)
            elif l.startswith("ACTION:WEATHER:"):
                results.append(Weather.get(l[15:]))
            elif l.startswith("ACTION:SYSTEM:"):
                results.append(SysInfo.get())
            elif l.startswith("ACTION:FILE:list"):
                results.append(Files.list_files())
            elif l.startswith("ACTION:FILE:create:"):
                p = l[19:].split("|", 1)
                results.append(Files.create(p[0].strip(),
                    p[1].strip() if len(p) > 1 else ""))
            elif l.startswith("ACTION:REMINDER:"):
                p = l[16:].split("|", 1)
                try: mins = int(p[0].strip())
                except: mins = 5
                txt = p[1].strip() if len(p) > 1 else "Reminder!"
                if log_fn:
                    Clock.schedule_once(
                        lambda dt, m=txt: log_fn("⏰ " + m), mins * 60)
                results.append(f"⏰ Reminder: {mins} min — {txt}")
        except Exception as e:
            results.append(f"Action error: {e}")
    return "\n\n".join(r for r in results if r)

# ── UI Widgets ────────────────────────────────────────────────────
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
        self._bg_c = bg
        self._rad = radius
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*get_color_from_hex(self._bg_c))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self._rad])


class JarvisInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = get_color_from_hex(C["input_bg"])
        self.foreground_color = c("fg")
        self.cursor_color = c("accent")
        self.hint_text_color = get_color_from_hex("#4a5a7a")
        self.font_size = sp(13)
        self.padding = [dp(12), dp(10)]


# ── Chat Screen ───────────────────────────────────────────────────
class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.history = []
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            Color(*c("bg"))
            r = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda w,v: setattr(r,'pos',v),
                  size=lambda w,v: setattr(r,'size',v))

        # Header
        hdr = BoxLayout(size_hint_y=None, height=dp(52),
                        padding=[dp(12),dp(6)], spacing=dp(8))
        with hdr.canvas.before:
            Color(*c("bar"))
            rh = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda w,v: setattr(rh,'pos',v),
                 size=lambda w,v: setattr(rh,'size',v))

        hdr.add_widget(Label(text="◈ J.A.R.V.I.S", font_size=sp(17),
                             bold=True, color=c("accent"), size_hint_x=0.7,
                             halign="left", valign="middle",
                             text_size=(None,None)))

        menu_btn = JarvisButton(text="☰", size_hint_x=None, width=dp(40),
                                height=dp(38), bg_color=C["sidebar"])
        menu_btn.bind(on_press=lambda *a: self.manager.app_ref.open_menu())

        cfg_btn = JarvisButton(text="⚙", size_hint_x=None, width=dp(40),
                               height=dp(38), bg_color=C["sidebar"])
        cfg_btn.bind(on_press=lambda *a:
            setattr(self.manager, "current", "settings"))

        hdr.add_widget(menu_btn)
        hdr.add_widget(cfg_btn)
        root.add_widget(hdr)

        # Chat area
        sv = ScrollView(size_hint=(1,1), do_scroll_x=False)
        self._chat = BoxLayout(orientation="vertical", size_hint_y=None,
                               spacing=dp(6), padding=[dp(8),dp(8)])
        self._chat.bind(minimum_height=self._chat.setter("height"))
        sv.add_widget(self._chat)
        self._sv = sv
        root.add_widget(sv)

        # Quick buttons
        qa = BoxLayout(size_hint_y=None, height=dp(44),
                       spacing=dp(4), padding=[dp(4),dp(4)])
        with qa.canvas.before:
            Color(*c("sidebar"))
            rq = Rectangle(pos=qa.pos, size=qa.size)
        qa.bind(pos=lambda w,v: setattr(rq,'pos',v),
                size=lambda w,v: setattr(rq,'size',v))

        for emoji, cmd in [("🌤","Udaipur ka mausam"), ("📰","India news aaj"),
                            ("💻","System info"), ("📁","Files list karo")]:
            b = JarvisButton(text=emoji, size_hint_x=None, width=dp(44),
                             height=dp(36), bg_color=C["bar"], radius=8,
                             font_size=sp(15))
            b.bind(on_press=lambda btn, c_=cmd: self._quick(c_))
            qa.add_widget(b)
        root.add_widget(qa)

        # Input
        inp_row = BoxLayout(size_hint_y=None, height=dp(54),
                            spacing=dp(6), padding=[dp(8),dp(6)])
        with inp_row.canvas.before:
            Color(*c("bar"))
            ri = Rectangle(pos=inp_row.pos, size=inp_row.size)
        inp_row.bind(pos=lambda w,v: setattr(ri,'pos',v),
                     size=lambda w,v: setattr(ri,'size',v))

        self._entry = JarvisInput(
            hint_text=f"Kuch poochho...",
            multiline=False, size_hint_x=1)
        self._entry.bind(on_text_validate=self._send)

        send = JarvisButton(text="▶", size_hint_x=None,
                            width=dp(48), bg_color=C["btn2"])
        send.bind(on_press=self._send)

        inp_row.add_widget(self._entry)
        inp_row.add_widget(send)
        root.add_widget(inp_row)
        self.add_widget(root)

        Clock.schedule_once(lambda dt: self._add(
            "◈ JARVIS",
            f"Namaste {CFG.get('name','Sir')}! JARVIS ready hai.\n"
            f"Settings mein API key daalo.", C["tag_j"]), 0.3)

    def _quick(self, cmd):
        self._entry.text = cmd
        self._send()

    def _add(self, sender, text, col=None):
        col = col or C["fg"]
        box = BoxLayout(orientation="vertical", size_hint_y=None,
                        padding=[dp(8),dp(5)], spacing=dp(2))
        sl = Label(text=f"{sender} [{datetime.datetime.now():%H:%M}]",
                   font_size=sp(10), bold=True,
                   color=get_color_from_hex(col),
                   size_hint_y=None, height=dp(16),
                   halign="left", valign="middle")
        sl.bind(size=sl.setter("text_size"))

        ml = Label(text=text, font_size=sp(13), color=c("fg"),
                   size_hint_y=None, halign="left", valign="top")
        ml.bind(width=lambda w,v: setattr(w,"text_size",(v,None)))
        ml.bind(texture_size=lambda w,s: setattr(w,"height",s[1]+dp(4)))

        box.add_widget(sl)
        box.add_widget(ml)

        with box.canvas.before:
            Color(*get_color_from_hex(C["card"]))
            rb = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(8)])
        box.bind(pos=lambda w,v: setattr(rb,'pos',v),
                 size=lambda w,v: setattr(rb,'size',v))
        box.bind(minimum_height=box.setter("height"))

        self._chat.add_widget(box)
        Clock.schedule_once(lambda dt: setattr(self._sv,"scroll_y",0), 0.1)

    def _send(self, *a):
        txt = self._entry.text.strip()
        if not txt: return
        self._entry.text = ""
        self._add(f"▶ {CFG.get('name','You')}", txt, C["tag_u"])
        self._add("◈ JARVIS", "🔄 Soch raha hoon...", C["tag_j"])
        threading.Thread(target=self._ai, args=(txt,), daemon=True).start()

    def _ai(self, msg):
        api_key = CFG.get("api_key", "")
        if not api_key:
            Clock.schedule_once(lambda dt: self._replace(
                "⚠ API key nahi! Settings mein daalo."), 0)
            return
        try:
            self.history.append({"role":"user","content":msg})
            if len(self.history) > 16:
                self.history = self.history[-16:]
            reply = call_claude(self.history, get_prompt(), api_key)
            self.history.append({"role":"assistant","content":reply})

            action_result = do_actions(reply, api_key,
                log_fn=lambda m: Clock.schedule_once(
                    lambda dt, x=m: self._add("⚡", x, C["tag_a"]), 0))

            display = "\n".join(l for l in reply.split("\n")
                                if not l.strip().startswith("ACTION:"))
            if action_result:
                display = display.strip() + f"\n\n⚡ {action_result}"

            Clock.schedule_once(lambda dt, d=display: self._replace(d), 0)
        except Exception as e:
            Clock.schedule_once(
                lambda dt: self._replace(f"❌ Error: {e}"), 0)

    def _replace(self, text):
        children = self._chat.children
        if children:
            last = children[0]
            for lbl in [w for w in last.children if isinstance(w, Label)]:
                if "🔄" in lbl.text or "Soch" in lbl.text:
                    lbl.text = text
                    return
        self._add("◈ JARVIS", text, C["tag_j"])


# ── Settings Screen ───────────────────────────────────────────────
class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            Color(*c("bg"))
            r = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda w,v: setattr(r,'pos',v),
                  size=lambda w,v: setattr(r,'size',v))

        hdr = BoxLayout(size_hint_y=None, height=dp(52),
                        padding=[dp(12),dp(6)])
        with hdr.canvas.before:
            Color(*c("bar"))
            rh = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda w,v: setattr(rh,'pos',v),
                 size=lambda w,v: setattr(rh,'size',v))

        back = JarvisButton(text="← Back", size_hint_x=None,
                            width=dp(80), bg_color=C["sidebar"])
        back.bind(on_press=lambda *a:
            setattr(self.manager, "current", "chat"))
        hdr.add_widget(back)
        hdr.add_widget(Label(text="⚙ Settings", font_size=sp(16),
                             bold=True, color=c("accent")))
        root.add_widget(hdr)

        sv = ScrollView()
        sl = BoxLayout(orientation="vertical", size_hint_y=None,
                       padding=dp(14), spacing=dp(10))
        sl.bind(minimum_height=sl.setter("height"))

        def field(label, key, pw=False):
            sl.add_widget(Label(text=label, font_size=sp(11),
                                color=c("accent"), size_hint_y=None,
                                height=dp(20), halign="left",
                                text_size=(Window.width-dp(28), None)))
            inp = JarvisInput(text=str(CFG.get(key,"")),
                              password=pw, multiline=False,
                              size_hint_y=None, height=dp(42))
            sl.add_widget(inp)
            return inp

        self._api  = field("🔑 Anthropic API Key", "api_key", pw=True)
        self._name = field("👤 Aapka Naam", "name")

        save_btn = JarvisButton(text="💾 SAVE", bg_color=C["btn2"],
                                size_hint_y=None, height=dp(48))
        save_btn.bind(on_press=self._save)
        sl.add_widget(Label(size_hint_y=None, height=dp(8)))
        sl.add_widget(save_btn)

        sl.add_widget(Label(
            text=f"Base dir: {BASE_DIR or 'Loading...'}",
            font_size=sp(9), color=c("border"),
            size_hint_y=None, height=dp(30), halign="center"))

        sv.add_widget(sl)
        root.add_widget(sv)
        self.add_widget(root)

    def _save(self, *a):
        CFG["api_key"] = self._api.text.strip()
        CFG["name"]    = self._name.text.strip() or "Sir"
        save_cfg(CFG)
        popup = Popup(title="✅ Saved!",
                      content=Label(text="Settings save ho gayi!", color=c("fg")),
                      size_hint=(0.7, 0.25))
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 1.5)


# ── Files Screen ──────────────────────────────────────────────────
class FilesScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            Color(*c("bg"))
            r = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda w,v: setattr(r,'pos',v),
                  size=lambda w,v: setattr(r,'size',v))

        hdr = BoxLayout(size_hint_y=None, height=dp(52),
                        padding=[dp(12),dp(6)])
        with hdr.canvas.before:
            Color(*c("bar"))
            rh = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda w,v: setattr(rh,'pos',v),
                 size=lambda w,v: setattr(rh,'size',v))

        back = JarvisButton(text="← Back", size_hint_x=None,
                            width=dp(80), bg_color=C["sidebar"])
        back.bind(on_press=lambda *a:
            setattr(self.manager, "current", "chat"))
        hdr.add_widget(back)
        hdr.add_widget(Label(text="📁 JARVIS Files", font_size=sp(16),
                             bold=True, color=c("accent")))
        root.add_widget(hdr)

        start_path = str(FILES_DIR) if FILES_DIR and FILES_DIR.exists() else "/sdcard"
        self._fc = FileChooserListView(path=start_path, size_hint_y=0.7)
        root.add_widget(self._fc)

        btn_row = GridLayout(cols=2, size_hint_y=None, height=dp(54),
                             spacing=dp(6), padding=[dp(8),dp(4)])
        read = JarvisButton(text="📖 Read", bg_color=C["btn"])
        read.bind(on_press=self._read)
        delete = JarvisButton(text="🗑 Delete", bg_color="#b71c1c")
        delete.bind(on_press=self._delete)
        btn_row.add_widget(read)
        btn_row.add_widget(delete)
        root.add_widget(btn_row)

        sv = ScrollView(size_hint_y=0.25)
        self._res = Label(text="File select karo.", font_size=sp(12),
                          color=c("fg"), size_hint_y=None,
                          halign="left", valign="top")
        self._res.bind(width=lambda w,v: setattr(w,"text_size",(v,None)))
        self._res.bind(texture_size=lambda w,s: setattr(w,"height",s[1]+dp(8)))
        sv.add_widget(self._res)
        root.add_widget(sv)
        self.add_widget(root)

    def _read(self, *a):
        sel = self._fc.selection
        if not sel: self._res.text = "⚠ File select karo!"; return
        try:
            self._res.text = Path(sel[0]).read_text(encoding="utf-8")[:800]
        except Exception as e:
            self._res.text = f"Error: {e}"

    def _delete(self, *a):
        sel = self._fc.selection
        if not sel: self._res.text = "⚠ File select karo!"; return
        try:
            Path(sel[0]).unlink()
            self._res.text = f"✅ Deleted: {Path(sel[0]).name}"
            self._fc._update_files()
        except Exception as e:
            self._res.text = f"Error: {e}"


# ── Main App ──────────────────────────────────────────────────────
class JarvisApp(App):
    def build(self):
        global BASE_DIR, REPORTS_DIR, FILES_DIR, CONFIG_FILE, CFG

        Window.clearcolor = get_color_from_hex(C["bg"])

        # Permissions request
        if IS_ANDROID:
            try:
                request_permissions([
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                    Permission.INTERNET,
                    Permission.RECORD_AUDIO,
                ])
            except: pass

        # Dirs init — safely
        BASE_DIR    = init_dirs()
        REPORTS_DIR = BASE_DIR / "Reports"
        FILES_DIR   = BASE_DIR / "Files"
        CONFIG_FILE = BASE_DIR / "config.json"

        # Ensure dirs exist
        for d in [BASE_DIR, REPORTS_DIR, FILES_DIR]:
            try: d.mkdir(parents=True, exist_ok=True)
            except: pass

        # Load config
        CFG = load_cfg()

        self.sm = ScreenManager(transition=SlideTransition())
        self.sm.app_ref = self
        self.sm.add_widget(ChatScreen(name="chat"))
        self.sm.add_widget(SettingsScreen(name="settings"))
        self.sm.add_widget(FilesScreen(name="files"))
        return self.sm

    def open_menu(self):
        content = BoxLayout(orientation="vertical",
                            spacing=dp(8), padding=dp(12))
        popup = Popup(title="◈ JARVIS Menu", content=content,
                      size_hint=(0.75, 0.5),
                      background_color=get_color_from_hex(C["bar"]),
                      title_color=get_color_from_hex(C["accent"]))
        for lbl, screen in [("💬 Chat","chat"),
                             ("📁 Files","files"),
                             ("⚙ Settings","settings")]:
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
