# -*- coding: utf-8 -*-
"""
Internacional (NL/DE/EU) via Google News RSS — padrão Colab
- Janela: 14 dias (padrão)
- Foco: Holanda, Alemanha, União Europeia
- Envia para EMAIL_TO_EXTERIOR
Requer secrets: GMAIL_USER, GMAIL_APP_PASS, EMAIL_TO_EXTERIOR
"""

import os
import datetime
from urllib.parse import quote_plus
import feedparser
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ===== Parâmetros (podem ser sobrepostos no workflow) =====
LANG = os.getenv("LANG_INT", "en")
COUNTRY = os.getenv("COUNTRY_INT", "US")     # US funciona bem para buscas globais
DAYS = int(os.getenv("DAYS_INT", "14"))
MAX_PER_TERM = int(os.getenv("MAX_PER_TERM_INT", "8"))

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASS = os.environ["GMAIL_APP_PASS"]
EMAIL_TO = os.environ["EMAIL_TO_EXTERIOR"]
EMAIL_SUBJECT = os.getenv(
    "EMAIL_SUBJECT_INT",
    f"📨 Editais Internacionais — NL/DE/EU — últimos {DAYS} dias"
)

# ===== Consultas focadas em domínios oficiais (menos ruído) =====
TERMS = [
    # União Europeia
    'site:erc.europa.eu "Consolidator Grant"',
    'site:erc.europa.eu "Advanced Grant"',
    'site:marie-sklodowska-curie-actions.ec.europa.eu fellowship',
    'site:ec.europa.eu MSCA',
    'site:rea.ec.europa.eu MSCA',
    'site:cordis.europa.eu "call for proposals"',

    # Holanda (NL)
    'site:nwo.nl Vidi',
    'site:nwo.nl Vici',
    'site:nwo.nl "open call"',
    'site:euraxess.ec.europa.eu Netherlands postdoctoral',

    # Alemanha (DE)
    'site:daad.de postdoctoral fellowship',
    'site:dfg.de "individual research grant"',
    'site:humboldt-foundation.de fellowship',
    'site:avh.de fellowship',  # domínio curto da Humboldt
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
    head = (f"<h2>Editais Internacionais — NL/DE/EU — últimos {dias} dias</h2>"
            f"<p class='muted'>Fonte: Google News RSS (domínios oficiais).</p>")
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
    out = [f"Editais Internacionais — NL/DE/EU — últimos {dias} dias", ""]
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
    print(f"INT-NL/DE/EU OK: {total} itens enviados para {EMAIL_TO}")

if __name__ == "__main__":
    main()
