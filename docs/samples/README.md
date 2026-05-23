# Sample test briefs for IHS

## Manager test — Word file

| File | Use |
|------|-----|
| **IHS-Test-Brief-Simple-Web-App.docx** | Upload on **New Project** to test `.docx` → harness pipeline |

**Project described:** a simple **Focus Timer** (Pomodoro-style) built with **HTML, CSS, and JavaScript only** — no React, no npm.

### Quick test steps

1. Open [IHS live demo](https://intelligent-harness-system-12345.vercel.app/) → **New Project**.
2. Upload `IHS-Test-Brief-Simple-Web-App.docx`.
3. Optional text: `Static HTML/CSS/JS Pomodoro timer`.
4. Start run → watch **Logs** / **Debate** → **Approval** → build.
5. Verify: timer starts/pauses/resets, 25 min and 5 min presets, “Time’s up!” at zero.

### Regenerate the .docx

```bash
cd backend
.venv\Scripts\activate
python ..\docs\samples\generate_test_brief.py
```

Requires `python-docx` (already in `backend/requirements.txt`).
