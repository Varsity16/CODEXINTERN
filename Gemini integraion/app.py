"""
Gemini Chat with Memory + Google Search (Python)
================================================

▶️ Run
    python app.py
    
to activate environment    
  python -m venv venv
  venv\Scripts\activate

Type your messages. Examples:
- btc price
- weather in mumbai
- what’s new in python 3.12?
- /new   (starts a fresh session)
- /history  (shows last 20 turns)
- /help


 API keys should be stored in .env file

"""
from __future__ import annotations

import os
import re
import json
import time
import sqlite3
import datetime as dt
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

import google.generativeai as genai

console = Console()


load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GOOGLE_CSE_API_KEY = os.getenv("GOOGLE_CSE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")  # or gemini-1.5-flash
DB_PATH = os.getenv("CHAT_DB", "chat_memory.sqlite3")
SESSION_ID = os.getenv("SESSION_ID", dt.datetime.now().strftime("sess-%Y%m%d-%H%M%S"))
MAX_TOKENS_IN_CONTEXT = int(os.getenv("MAX_TOKENS_IN_CONTEXT", 4000))  # soft cap

if not GEMINI_API_KEY:
    console.print("[bold red]Missing GEMINI_API_KEY in .env[/bold red]")
    raise SystemExit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_session_created ON messages(session_id, created_at);
"""

class ConversationStore:
    def __init__(self, path: str):
        self.path = path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.path) as conn:
            conn.executescript(SCHEMA_SQL)

    def add(self, role: str, content: str, session_id: str = SESSION_ID):
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO messages(session_id, role, content) VALUES(?,?,?)",
                (session_id, role, content),
            )
            conn.commit()

    def fetch(self, session_id: str = SESSION_ID, limit: int = 50) -> List[Tuple[str,str,str]]:
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute(
                "SELECT role, content, created_at FROM messages WHERE session_id=? ORDER BY created_at ASC, id ASC LIMIT ?",
                (session_id, limit),
            )
            return cur.fetchall()

    def clear(self, session_id: str = SESSION_ID):
        with sqlite3.connect(self.path) as conn:
            conn.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
            conn.commit()

store = ConversationStore(DB_PATH)


@dataclass
class SearchResult:
    answer: Optional[str]
    snippets: List[str]
    links: List[Tuple[str, str]]  

class SearchClient:
    def __init__(self, serper_key: Optional[str]=None, g_api_key: Optional[str]=None, g_cx: Optional[str]=None):
        self.serper_key = serper_key
        self.g_api_key = g_api_key
        self.g_cx = g_cx

    def available(self) -> bool:
        return bool(self.serper_key or (self.g_api_key and self.g_cx))

    def search(self, query: str, gl: str = "in", hl: str = "en") -> SearchResult:
        if self.serper_key:
            return self._search_serper(query, gl=gl, hl=hl)
        elif self.g_api_key and self.g_cx:
            return self._search_cse(query)
        else:
            return SearchResult(answer=None, snippets=[], links=[])

    # Serper.dev — Google Search API wrapper (recommended)
    def _search_serper(self, query: str, gl: str = "in", hl: str = "en") -> SearchResult:
        try:
            resp = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": self.serper_key, "Content-Type": "application/json"},
                json={"q": query, "gl": gl, "hl": hl},
                timeout=12,
            )
            data = resp.json()
            answer = data.get("answerBox", {}).get("answer") or data.get("knowledgeGraph", {}).get("title")
            snippets = []
            links: List[Tuple[str,str]] = []
            for item in data.get("organic", [])[:5]:
                title = item.get("title") or "(no title)"
                url = item.get("link") or ""
                snippet = item.get("snippet") or ""
                snippets.append(snippet)
                links.append((title, url))
            return SearchResult(answer=answer, snippets=snippets, links=links)
        except Exception as e:
            return SearchResult(answer=None, snippets=[f"Serper error: {e}"], links=[])

    # Google Custom Search JSON API (official)
    def _search_cse(self, query: str) -> SearchResult:
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            resp = requests.get(url, params={"key": self.g_api_key, "cx": self.g_cx, "q": query}, timeout=12)
            data = resp.json()
            items = data.get("items", [])
            snippets = [it.get("snippet", "") for it in items[:5]]
            links = [(it.get("title", "(no title)"), it.get("link", "")) for it in items[:5]]
            # CSE rarely has a direct answer; try to pick first snippet as pseudo-answer
            answer = items[0].get("snippet") if items else None
            return SearchResult(answer=answer, snippets=snippets, links=links)
        except Exception as e:
            return SearchResult(answer=None, snippets=[f"CSE error: {e}"], links=[])

search_client = SearchClient(SERPER_API_KEY, GOOGLE_CSE_API_KEY, GOOGLE_CSE_ID)

BTC_PAT = re.compile(r"\b(btc|bitcoin)\b.*\b(price|rate|value)\b|\b(price|rate|value)\b.*\b(btc|bitcoin)\b", re.I)
WEATHER_PAT = re.compile(r"\bweather\b.*\b(in|at)\b\s+([a-zA-Z .,'-]+)", re.I)
NOW_PAT = re.compile(r"\b(now|today|current|live|right now)\b", re.I)


def fetch_live_context(user_msg: str) -> Optional[str]:
    """Return a string with fresh data if we detect a live info request."""
    if not search_client.available():
        return None

    # BTC price
    if BTC_PAT.search(user_msg) or ("btc" in user_msg.lower() and NOW_PAT.search(user_msg)):
        sr = search_client.search("current Bitcoin price in USD and INR")
        prize = extract_number(sr.answer or "")
        # Try from snippets too
        if prize is None:
            for sn in sr.snippets:
                prize = extract_number(sn)
                if prize is not None:
                    break
        parts = ["[Live Search] Bitcoin price (from Google Search):"]
        if sr.answer:
            parts.append(f"AnswerBox: {sr.answer}")
        if prize is not None:
            parts.append(f"Parsed price-ish number: {prize}")
        if sr.links:
            parts.append("Top sources:\n" + "\n".join(f"- {t}: {u}" for t,u in sr.links))
        return "\n".join(parts)

    # Weather
    m = WEATHER_PAT.search(user_msg)
    if m:
        city = m.group(2).strip()
        sr = search_client.search(f"weather in {city} now")
        temp = extract_temperature(sr.answer or "")
        if temp is None:
            for sn in sr.snippets:
                temp = extract_temperature(sn)
                if temp is not None:
                    break
        parts = [f"[Live Search] Weather for {city}:"]
        if sr.answer:
            parts.append(f"AnswerBox: {sr.answer}")
        if temp:
            parts.append(f"Parsed temperature-ish value: {temp}")
        if sr.links:
            parts.append("Top sources:\n" + "\n".join(f"- {t}: {u}" for t,u in sr.links))
        return "\n".join(parts)

    if NOW_PAT.search(user_msg):
        sr = search_client.search(user_msg)
        parts = ["[Live Search] Top results:"]
        if sr.answer:
            parts.append(f"AnswerBox: {sr.answer}")
        if sr.links:
            parts.append("Sources:\n" + "\n".join(f"- {t}: {u}" for t,u in sr.links))
        return "\n".join(parts)

    return None


def extract_number(text: str) -> Optional[str]:
    m = re.search(r"(?:USD|US\$|\$|INR|₹)\s*([0-9][0-9,]*(?:\.[0-9]+)?)", text)
    if m:
        return m.group(0)
    m2 = re.search(r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:USD|US\$|\$|INR|₹)", text)
    return m2.group(0) if m2 else None


def extract_temperature(text: str) -> Optional[str]:
    m = re.search(r"(-?\d{1,3})\s*(?:°\s*[CF]|deg\s*[CF]|C|F)\b", text, re.I)
    return m.group(0) if m else None

SYSTEM_PRIMER = (
    "You are a helpful Python assistant. If a '[Live Search]' context is provided, "
    "use it to answer time-sensitive questions and cite the listed sources in plain text."
)


def build_history_text(rows: List[Tuple[str,str,str]], max_chars: int = 12000) -> str:
    chunks = [f"system: {SYSTEM_PRIMER}"]
    for role, content, created_at in rows:
        chunks.append(f"{role} ({created_at}): {content}")
    text = "\n".join(chunks)
    if len(text) > max_chars:
        # Keep the tail if too long
        text = text[-max_chars:]
    return text


def chat_once(user_msg: str) -> str:
    # 1) Memory fetch
    rows = store.fetch(limit=100)
    hist_text = build_history_text(rows)

    # 2) Live data if needed
    live = fetch_live_context(user_msg)

    # 3) Compose prompt
    prompt_parts = [
        SYSTEM_PRIMER,
        "\nConversation so far:\n" + hist_text,
        "\nUser:\n" + user_msg,
    ]
    if live:
        prompt_parts.append("\n" + live)
        prompt_parts.append("\nPlease ground your answer in the [Live Search] data when relevant, and include short plain-text citations to the listed sources (just the URLs).")

    final_prompt = "\n\n".join(prompt_parts)

    # 4) Call Gemini
    try:
        resp = model.generate_content(final_prompt)
        text = resp.text or "(no response)"
    except Exception as e:
        text = f"Error from Gemini: {e}"

    # 5) Persist
    store.add("user", user_msg)
    store.add("assistant", text)
    return text

HELP = """
Commands:
  /help           Show this help
  /new            Start a new session (clears memory for this SESSION_ID)
  /history        Show last 20 turns
  /whoami         Show config / which search backend will be used
"""

def show_history(n: int = 20):
    rows = store.fetch(limit=1000)
    rows = rows[-(n*2):]  # approx user+assistant per turn
    table = Table(title=f"Last {n} turns (session: {SESSION_ID})")
    table.add_column("When")
    table.add_column("Role")
    table.add_column("Content", overflow="fold")
    for role, content, created_at in rows:
        table.add_row(created_at, role, content)
    console.print(table)


def whoami():
    meta = Table(title="Runtime Config")
    meta.add_column("Key")
    meta.add_column("Value")
    meta.add_row("Model", MODEL_NAME)
    meta.add_row("DB", DB_PATH)
    meta.add_row("Session", SESSION_ID)
    backend = "Serper" if SERPER_API_KEY else ("Google CSE" if (GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID) else "None")
    meta.add_row("Search Backend", backend)
    console.print(meta)


def main():
    console.print(Panel.fit("Gemini Chat with Memory + Google Search", style="bold green"))
    console.print("Type /help for commands. Start chatting!\n")

    while True:
        try:
            user_msg = console.input("[bold cyan]You> [/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            console.print("\nBye!")
            break
        user_msg = user_msg.strip()
        if not user_msg:
            continue

        if user_msg.lower() == "/help":
            console.print(Markdown(HELP))
            continue
        if user_msg.lower() == "/new":
            store.clear()
            console.print("[yellow]New session started. Memory cleared.[/yellow]")
            continue
        if user_msg.lower() == "/history":
            show_history()
            continue
        if user_msg.lower() == "/whoami":
            whoami()
            continue

        answer = chat_once(user_msg)
        console.print(Panel.fit(Markdown(answer), title="Gemini", style="bold magenta"))


if __name__ == "__main__":
    main()
