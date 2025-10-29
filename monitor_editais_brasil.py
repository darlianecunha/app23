# -*- coding: utf-8 -*-
"""
Brasil (apenas FAPEMA) via Google News RSS
- Locale BR/PT
- Janela de 14 dias (padrão)
- Envia para EMAIL_TO_BRASIL
Requer secrets: GMAIL_USER, GMAIL_APP_PASS, EMAIL_TO_BRASIL
"""
import os
import feedparser
from urllib.parse import quote_plus
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ===== Parâmetros =====
LANG = os.getenv("LANG_BR", "pt-BR")
COUNTRY = os.getenv("COUNTRY_BR", "BR")
DAYS = int(os.getenv("DAYS_BR", "14"))
MAX_PER_TERM = int(os.getenv("MAX_PER_TERM_BR", "10"))

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASS = os.environ["GMAIL_APP_PASS"]
EMAIL_TO = os.environ["EMAIL_TO_BRASIL"]
EMAIL_SUBJECT = os.getenv("EMAIL_SUBJECT_BR", f"📨 Editais Brasil (FAPEMA) — últimos {DAYS} dias")

# ===== Termos — Brasil com local apenas FAPEMA (site:fapema.br) =====
TERMS = [
    # Filtros por site e termos típicos
    "site:fapema.br edital",
    "site:fapema.br chamada pública",
    "site:fapema.br chamada publica",
    "site:fapema.br resultado edital",
    "site:fapema.br retificação edital",
    "site:fapema.br bolsa",
    "site:fapema.br pós-doutorado",
    "site:fapema.br inovação",
    # variações com www (alguns indexadores tratam diferente)
    "site:www.fapema.br edital",
    "site:www.fapema.br chamada pública",
    "site:www.fapema.br resultado edital",
]

def buscar(termos, lang, country, dias, max_por_termo):
    resultados = {}
    hoje = datetime.date.today()
    limite = hoje - datetime.timedelta(days=dias)

    for termo in termos:
        q = quote_plus(termo)
        url = f"https://news.google.com/rss/search?q={q}&hl={lang}&gl={country}&ceid={country}:{lang}"
        feed = feedparser.parse(url)
        itens = []
        for e in feed.entries:
            dp = e.get("published_parsed")
            if not dp:
                continue
            d = datetime.date(*dp[:3])
            if d >= limite:
                itens.append({
                    "data": d.strftime("%d/%m/%Y"),
                    "titulo": e.title,
                    "link": e.link,
                })
        itens = sorted(
            itens,
            key=lambda x: datetime.datetime.strptime(x["data"], "%d/%m/%Y"),
            reverse=True
        )[:max_por_termo]
        resultados[termo] = itens
    return resultados

def html_email(noticias, dias):
    style = """
    <style>
      body { font-family: Arial, Helvetica, sans-serif; font-size: 14px; color: #222; }
      h2 { margin: 0 0 8px 0; }
      .termo { font-weight: 600; margin-top: 14px; }
      table { border-collapse: collapse; width: 100%; margin-top: 6px; }
      th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top; }
      th { background: #f5f5f5; text-align: left; }
      .muted { color: #666; }
      .nores { color: #a00; }
    </style>
    """
    head = f"<h2>Editais Brasil (FAPEMA) — últimos {dias} dias</h2><p class='muted'>Fonte: Google News RSS (site:fapema.br).</p>"
    blocks = []
    for termo, itens in noticias.items():
        if not itens:
            blocks.append(f"<div class='termo'>🔎 {termo}</div><div class='nores'>⚠️ Sem resultados</div>")
        else:
            linhas = "".join(
                f"<tr><td>{i['data']}</td><td><a href='{i['link']}' target='_blank' rel='noopener noreferrer'>{i['titulo']}</a></td></tr>"
                for i in itens
            )
            blocks.append(
                f"<div class='termo'>🔎 {termo}</div>"
                f"<table><thead><tr><th>Data</th><th>Título / Link</th></tr></thead>"
                f"<tbody>{linhas}</tbody></table>"
            )
    return f"<!DOCTYPE html><html><head>{style}</head><body>{head}{''.join(blocks)}</body></html>"

def txt_email(noticias, dias):
    out = [f"Editais Brasil (FAPEMA) — últimos {dias} dias", ""]
    for termo, itens in noticias.items():
        out.append(f"🔎 {termo}")
        if not itens:
            out.append("  - Sem resultados")
        else:
            for i in itens[:5]:
                out.append(f"  - [{i['data']}] {i['titulo']}  {i['link']}")
        out.append("")
    return "\n".join(out)

def enviar(corpo_txt, corpo_html):
    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = EMAIL_SUBJECT
    msg.attach(MIMEText(corpo_txt, "plain", "utf-8"))
    msg.attach(MIMEText(corpo_html, "html", "utf-8"))
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=45) as s:
        s.starttls()
        s.login(GMAIL_USER, GMAIL_APP_PASS)
        s.send_message(msg)

def main():
    data = buscar(TERMS, LANG, COUNTRY, DAYS, MAX_PER_TERM)
    enviar(txt_email(data, DAYS), html_email(data, DAYS))
    total = sum(len(v) for v in data.values())
    print(f"BR-FAPEMA OK: {total} itens enviados para {EMAIL_TO}")

if __name__ == "__main__":
    main()

