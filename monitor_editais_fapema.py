import os
import feedparser
from datetime import datetime, timedelta, timezone
from email.mime_text import MIMEText
import smtplib
from dateutil import parser as dtparser

# === Config ===
SEARCH_DAYS = int(os.getenv("SEARCH_DAYS", "14"))
EMAIL_SUBJECT = os.getenv("EMAIL_SUBJECT", "📨 Editais – FAPEMA (últimos 14 dias)")
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASS = os.environ["GMAIL_APP_PASS"]
EMAIL_TO = os.environ["EMAIL_TO"]

# === Fontes (somente FAPEMA) ===
RSS_SOURCES = {
    "FAPEMA (site oficial RSS)": "https://www.fapema.br/portal/feed/",
    "FAPEMA (Google News)": "https://news.google.com/rss/search?q=site:fapema.br+(edital+OR+chamada+OR+bolsa+OR+fomento)",
}

KEYWORDS = [
    "edital", "chamada", "chamadas", "chamada pública", "seleção", "convocação",
    "submissão", "fomento", "bolsa", "bolsas", "pesquisa", "propostas",
    "resultado", "retificação", "prorrog"
]

def within_days(published, days=14):
    if not published:
        return False
    try:
        dt = dtparser.parse(published)
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        return False
    return (datetime.now(timezone.utc) - dt) <= timedelta(days=days)

def matches_keywords(title, summary):
    text = f"{title or ''} {summary or ''}".lower()
    return any(k in text for k in KEYWORDS)

def collect_items():
    items = []
    for name, url in RSS_SOURCES.items():
        feed = feedparser.parse(url)
        for e in feed.entries:
            pub = getattr(e, "published", None) or getattr(e, "updated", None)
            title = e.get("title") or ""
            summary = e.get("summary") or ""
            link = (e.get("link") or "").strip()
            if within_days(pub, SEARCH_DAYS) and matches_keywords(title, summary) and link:
                items.append({
                    "fonte": name,
                    "titulo": title.strip(),
                    "link": link,
                    "published": pub
                })
    return items

def format_email(items):
    if not items:
        return f"Nenhum edital da FAPEMA encontrado nos últimos {SEARCH_DAYS} dias."
    items.sort(key=lambda x: x.get("published") or "", reverse=True)
    header = f"Janela: últimos {SEARCH_DAYS} dias\nFontes: FAPEMA\n"
    body = "\n".join([f"• {it['titulo']}\n  {it['link']}" for it in items])
    return f"{header}\n{body}"

def send_email(body):
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = EMAIL_SUBJECT
    msg["From"] = GMAIL_USER
    msg["To"] = EMAIL_TO
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=45) as s:
        s.starttls()
        s.login(GMAIL_USER, GMAIL_APP_PASS)
        s.send_message(msg)

def main():
    items = collect_items()
    send_email(format_email(items))
    print(f"FAPEMA: {len(items)} itens enviados.")

if __name__ == "__main__":
    main()
