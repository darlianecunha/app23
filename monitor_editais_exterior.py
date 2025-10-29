import os
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
import smtplib
from dateutil import parser as dtparser

SEARCH_DAYS = int(os.getenv("SEARCH_DAYS", "3"))
EMAIL_SUBJECT = os.getenv("EMAIL_SUBJECT", "📨 Editais – NL/DE/EU")
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASS = os.environ["GMAIL_APP_PASS"]
EMAIL_TO = os.environ["EMAIL_TO"]

KEYWORDS = [
    "call", "call for proposals", "grant", "funding", "fellowship",
    "research", "programme", "deadline", "opening", "competition", "Consolidator", "ERC"
]

# Google News RSS para fontes principais (NL, DE, EU) + ERC Consolidator
RSS_SOURCES = {
    # Holanda
    "NWO (NL)": "https://news.google.com/rss/search?q=site:nwo.nl+call+OR+grant+OR+fellowship",
    # Alemanha
    "DFG (DE)": "https://news.google.com/rss/search?q=site:dfg.de+call+OR+funding+OR+programme",
    "DAAD (DE)": "https://news.google.com/rss/search?q=site:daad.de+call+OR+scholarship+OR+fellowship",
    # União Europeia (Funding & Tenders)
    "EU Funding & Tenders": "https://news.google.com/rss/search?q=site:funding.ted.europa.eu+call+OR+grant",
    # ERC – Consolidator Grants
    "ERC (Consolidator)": "https://news.google.com/rss/search?q=site:erc.europa.eu+Consolidator+Grant+OR+call",
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
    return any(k.lower() in text for k in KEYWORDS)

def collect_items():
    items = []
    for name, url in RSS_SOURCES.items():
        feed = feedparser.parse(url)
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
        return "No calls found for the configured period."
    items.sort(key=lambda x: x.get("published") or "", reverse=True)
    lines = []
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
    print(f"OK: {len(items)} items sent to {EMAIL_TO}")

if __name__ == "__main__":
    main()

