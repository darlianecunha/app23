import os
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
import smtplib
from dateutil import parser as dtparser

SEARCH_DAYS = int(os.getenv("SEARCH_DAYS", "3"))
EMAIL_SUBJECT = os.getenv("EMAIL_SUBJECT", "📨 Editais – Brasil")
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASS = os.environ["GMAIL_APP_PASS"]
EMAIL_TO = os.environ["EMAIL_TO"]

# Palavras-chave que devem aparecer no título/descrição
KEYWORDS = [
    "edital", "chamada", "chamada pública", "seleção", "bolsa", "fomento",
    "pesquisa", "inovação", "propostas", "resultado", "convocação"
]

# Fontes via Google News RSS (filtra por site:)
RSS_SOURCES = {
    "CAPES": "https://news.google.com/rss/search?q=site:capes.gov.br+edital+OR+\"chamada+p%C3%BAblica\"",
    "CNPq": "https://news.google.com/rss/search?q=site:cnpq.br+edital+OR+\"chamada+p%C3%BAblica\"",
    "FINEP": "https://news.google.com/rss/search?q=site:finep.gov.br+edital+OR+\"chamada+p%C3%BAblica\"",
    "MCTI": "https://news.google.com/rss/search?q=site:mcti.gov.br+edital+OR+\"chamada+p%C3%BAblica\"",
    "FAPEMA": "https://news.google.com/rss/search?q=site:fapema.br+edital+OR+\"chamada\"",
    # Você pode incluir FAPESP, FAPESB, FAPERJ etc.
    "FAPESP": "https://news.google.com/rss/search?q=site:fapesp.br+edital+OR+\"chamada\"",
}

def within_days(published, days=3):
    if not published:
        return False
    try:
        dt = dtparser.parse(published)
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        return False
    return (datetime.now(timezone.utc) - dt) <= timedelta(days=days)

def passes_keywords(title, summary):
    text = f"{title or ''} {summary or ''}".lower()
    return any(k in text for k in KEYWORDS)

def fetch_feed(url):
    return feedparser.parse(url)

def collect_items():
    items = []
    for name, url in RSS_SOURCES.items():
        feed = fetch_feed(url)
        for e in feed.entries:
            pub = getattr(e, "published", None) or getattr(e, "updated", None)
            if within_days(pub, SEARCH_DAYS) and passes_keywords(e.get("title"), e.get("summary")):
                items.append({
                    "fonte": name,
                    "titulo": e.get("title", "").strip(),
                    "link": e.get("link", "").strip(),
                    "published": pub
                })
    return items

def format_email(items):
    if not items:
        return "Nenhum edital encontrado no período configurado."
    lines = []
    items.sort(key=lambda x: x.get("published") or "", reverse=True)
    for it in items:
        lines.append(f"• [{it['fonte']}] {it['titulo']}\n  {it['link']}")
    return "\n\n".join(lines)

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
    body = format_email(items)
    send_email(body)
    print(f"OK: {len(items)} itens enviados para {EMAIL_TO}")

if __name__ == "__main__":
    main()
