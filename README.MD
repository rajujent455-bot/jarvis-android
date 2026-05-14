# JARVIS Android — Bug Fixes

## Fix 1 — API Key save nahi ho rahi

**Root cause:** Android pe `open("config.json", "w")` fail hota hai kyunki
app ka current directory (`/`) writable nahi hota.

**Solution:** Kivy ka `App.user_data_dir` use karo —
yeh automatically `/data/data/<package>/files/` point karta hai jo
always writable hota hai.

```python
# ❌ Pehle (kaam nahi karta Android pe)
with open("config.json", "w") as f:
    json.dump({"api_key": key}, f)

# ✅ Ab (sahi tarika)
data_dir = App.get_running_app().user_data_dir   # guaranteed writable
path = os.path.join(data_dir, "config.json")
with open(path, "w") as f:
    json.dump({"api_key": key}, f)
```

---

## Fix 2 — Emojis boxes ban rahe hain

**Root cause:** Kivy ka default font `Roboto` mein emoji glyphs nahi hote.

**Solution:** `NotoEmoji.ttf` font ko APK mein bundle karo aur register karo.

### Step 1 — Font register karo `main.py` mein:
```python
from kivy.core.text import LabelBase

LabelBase.register(
    name="NotoEmoji",
    fn_regular="assets/fonts/NotoEmoji.ttf"
)
```

### Step 2 — Har Label/Button pe font set karo jahan emoji ho:
```python
Label(text="🤖 JARVIS", font_name="NotoEmoji", ...)
Button(text="⚙️",      font_name="NotoEmoji", ...)
```

### Step 3 — `buildozer.spec` mein font include karo:
```ini
source.include_patterns = assets/fonts/*.ttf
```

### Step 4 — GitHub Actions mein font download karo (build se pehle):
```yaml
- name: Download NotoEmoji font
  run: |
    mkdir -p assets/fonts
    curl -L "https://github.com/googlefonts/noto-emoji/raw/main/fonts/NotoColorEmoji.ttf" \
         -o assets/fonts/NotoEmoji.ttf
```

---

## Files jo replace/update karni hain

| File | Action |
|------|--------|
| `main.py` | Poora replace karo |
| `buildozer.spec` | `source.include_patterns` line add karo |
| `.github/workflows/build.yml` | Font download step add karo |

## Test kaise karo

1. Settings screen kholo
2. API key daalo (`sk-ant-...`)
3. "Save" dabao — `✅ API Key save ho gayi!` dikhna chahiye
4. App band karo, dobara kholo
5. Settings mein key wahi honi chahiye (persist confirm)
6. Chat mein emoji wale buttons/labels sahi dikhne chahiye
