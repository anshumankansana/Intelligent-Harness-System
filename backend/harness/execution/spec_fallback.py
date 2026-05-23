"""When the LLM fails, build a real app from PROJECT_SPEC keywords (not a stub page)."""
from __future__ import annotations

import re
from pathlib import Path


def detect_app_kind(spec_text: str) -> str:
    t = spec_text.lower()
    if "calculator" in t or "arithmetic" in t or "calc" in t:
        return "calculator"
    if "todo" in t or "task list" in t:
        return "todo"
    if "weather" in t:
        return "weather"
    return "generic"


def apply_spec_fallback(project_dir: Path, spec_text: str, user_idea: str = "") -> str:
    """Write app files from spec. Returns description of what was built."""
    kind = detect_app_kind(spec_text + " " + user_idea)
    app_dir = project_dir / "app"
    app_dir.mkdir(parents=True, exist_ok=True)

    if kind == "calculator":
        (app_dir / "page.tsx").write_text(_CALCULATOR_PAGE, encoding="utf-8")
        (app_dir / "globals.css").write_text(_CALCULATOR_CSS, encoding="utf-8")
        layout = app_dir / "layout.tsx"
        if not layout.exists():
            layout.write_text(_LAYOUT_WITH_CSS, encoding="utf-8")
        return "calculator app (spec fallback template)"

    title = _extract_title(spec_text) or "Harness App"
    (app_dir / "page.tsx").write_text(_generic_page(title, user_idea), encoding="utf-8")
    if not (app_dir / "layout.tsx").exists():
        (app_dir / "layout.tsx").write_text(_LAYOUT_BASIC, encoding="utf-8")
    return f"generic app shell for “{title}”"


def _extract_title(spec_text: str) -> str:
    m = re.search(r"^#\s+(.+)$", spec_text, re.MULTILINE)
    return m.group(1).strip() if m else ""


_LAYOUT_BASIC = '''export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
'''

_LAYOUT_WITH_CSS = '''import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
'''

_CALCULATOR_CSS = """:root {
  --bg: #0f172a;
  --panel: rgba(30, 41, 59, 0.85);
  --accent: #22d3ee;
  --accent-dim: #0891b2;
  --text: #f1f5f9;
  --btn: rgba(51, 65, 85, 0.9);
  --btn-hover: rgba(71, 85, 105, 1);
  --op: #f59e0b;
}

* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  font-family: "Segoe UI", system-ui, sans-serif;
  background: radial-gradient(ellipse at top, #1e293b 0%, var(--bg) 55%);
  color: var(--text);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.calc-root { width: 100%; max-width: 380px; }
.calc-card {
  background: var(--panel);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(34, 211, 238, 0.25);
  border-radius: 24px;
  padding: 1.5rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}
.calc-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}
.calc-eyebrow {
  margin: 0;
  font-size: 0.65rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--accent);
}
.calc-card h1 { margin: 0.25rem 0 0; font-size: 1.5rem; font-weight: 700; }
.theme-toggle {
  background: var(--btn);
  border: none;
  border-radius: 12px;
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  font-size: 1.1rem;
}
.calc-display {
  text-align: right;
  font-size: 2.75rem;
  font-weight: 300;
  padding: 1rem 0.5rem;
  margin-bottom: 1rem;
  overflow: hidden;
  text-overflow: ellipsis;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
}
.calc-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.65rem;
}
.calc-btn {
  background: var(--btn);
  color: var(--text);
  border: none;
  border-radius: 14px;
  padding: 1rem;
  font-size: 1.25rem;
  font-weight: 500;
  cursor: pointer;
  transition: transform 0.1s, background 0.15s;
}
.calc-btn:hover { background: var(--btn-hover); transform: scale(1.03); }
.calc-btn:active { transform: scale(0.97); }
.calc-btn.op { background: rgba(245, 158, 11, 0.25); color: var(--op); }
.calc-btn.eq {
  background: linear-gradient(135deg, var(--accent), var(--accent-dim));
  color: #0f172a;
  font-weight: 700;
}
.calc-btn.wide { grid-column: span 2; }
body.light {
  --bg: #f1f5f9;
  --panel: rgba(255, 255, 255, 0.95);
  --text: #0f172a;
  --btn: #e2e8f0;
  --btn-hover: #cbd5e1;
}
"""

_CALCULATOR_PAGE = r'''"use client";

import { useCallback, useState } from "react";

type Op = "+" | "-" | "*" | "/" | null;

export default function CalculatorPage() {
  const [display, setDisplay] = useState("0");
  const [stored, setStored] = useState<number | null>(null);
  const [op, setOp] = useState<Op>(null);
  const [fresh, setFresh] = useState(true);
  const [light, setLight] = useState(false);

  const inputDigit = (d: string) => {
    setDisplay((prev) => {
      if (fresh) return d === "." ? "0." : d;
      if (d === "." && prev.includes(".")) return prev;
      return prev === "0" && d !== "." ? d : prev + d;
    });
    setFresh(false);
  };

  const clearAll = () => {
    setDisplay("0");
    setStored(null);
    setOp(null);
    setFresh(true);
  };

  const applyOp = useCallback(
    (next: Op) => {
      const val = parseFloat(display);
      if (stored === null || op === null) {
        setStored(val);
      } else {
        const result = compute(stored, val, op);
        setStored(result);
        setDisplay(String(result));
      }
      setOp(next);
      setFresh(true);
    },
    [display, stored, op]
  );

  const equals = () => {
    if (stored === null || op === null) return;
    const val = parseFloat(display);
    const result = compute(stored, val, op);
    setDisplay(String(result));
    setStored(null);
    setOp(null);
    setFresh(true);
  };

  const pct = () => setDisplay(String(parseFloat(display) / 100));

  const buttons: { label: string; action: () => void; className?: string }[] = [
    { label: "C", action: clearAll, className: "wide" },
    { label: "%", action: pct },
    { label: "÷", action: () => applyOp("/"), className: "op" },
    { label: "7", action: () => inputDigit("7") },
    { label: "8", action: () => inputDigit("8") },
    { label: "9", action: () => inputDigit("9") },
    { label: "×", action: () => applyOp("*"), className: "op" },
    { label: "4", action: () => inputDigit("4") },
    { label: "5", action: () => inputDigit("5") },
    { label: "6", action: () => inputDigit("6") },
    { label: "−", action: () => applyOp("-"), className: "op" },
    { label: "1", action: () => inputDigit("1") },
    { label: "2", action: () => inputDigit("2") },
    { label: "3", action: () => inputDigit("3") },
    { label: "+", action: () => applyOp("+"), className: "op" },
    { label: "0", action: () => inputDigit("0"), className: "wide" },
    { label: ".", action: () => inputDigit(".") },
    { label: "=", action: equals, className: "eq" },
  ];

  return (
    <main className="calc-root">
      <div className="calc-card">
        <header className="calc-header">
          <div>
            <p className="calc-eyebrow">IHS Build</p>
            <h1>Calculator</h1>
          </div>
          <button
            type="button"
            className="theme-toggle"
            onClick={() => {
              setLight((v) => !v);
              document.body.classList.toggle("light", !light);
            }}
            aria-label="Toggle theme"
          >
            {light ? "🌙" : "☀️"}
          </button>
        </header>
        <div className="calc-display" aria-live="polite">
          {display}
        </div>
        <div className="calc-grid">
          {buttons.map((b) => (
            <button
              key={b.label}
              type="button"
              className={`calc-btn ${b.className || ""}`}
              onClick={b.action}
            >
              {b.label}
            </button>
          ))}
        </div>
      </div>
    </main>
  );
}

function compute(a: number, b: number, op: Op): number {
  switch (op) {
    case "+":
      return a + b;
    case "-":
      return a - b;
    case "*":
      return a * b;
    case "/":
      return b === 0 ? NaN : a / b;
    default:
      return b;
  }
}
'''


def _generic_page(title: str, idea: str) -> str:
    safe_title = title.replace('"', "'")[:80]
    safe_idea = (idea or "Built by Intelligent Harness System")[:200].replace('"', "'")
    return f'''export default function Home() {{
  return (
    <main style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "linear-gradient(160deg, #0f172a, #1e3a5f)",
      color: "#f8fafc",
      fontFamily: "system-ui, sans-serif",
      padding: "2rem",
    }}>
      <div style={{
        maxWidth: 480,
        textAlign: "center",
        background: "rgba(255,255,255,0.06)",
        borderRadius: 20,
        padding: "2.5rem",
        border: "1px solid rgba(34,211,238,0.3)",
      }}>
        <h1 style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>{safe_title}</h1>
        <p style={{ opacity: 0.85, lineHeight: 1.6 }}>{safe_idea}</p>
      </div>
    </main>
  );
}}
'''
