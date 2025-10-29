# -*- coding: utf-8 -*-
"""
EXTERIOR2 — Chamadas com conexão Brasil–Holanda / Brasil–Alemanha
Idiomas: EN/NL/DE/PT (pesquisas paralelas)
Agenda: Terça e Sábado (via workflow)
Janela padrão: 14 dias
Envia para: EMAIL_TO_EXTERIOR2

Secrets necessários:
- GMAIL_USER
- GMAIL_APP_PASS
- EMAIL_TO_EXTERIOR2
"""

import os
import datetime
from urllib.parse import quote_plus
import feedparser
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ===== Parâmetros sobreponíveis por ENV =====
DAYS = int(os.getenv("DAYS_EXT2", "14"))
MAX_PER_TERM = int(os.getenv("MAX_PER_TERM_EXT2", "8"))
EMAIL_SUBJECT = os.getenv(
    "EMAIL_SUBJECT_EXT2",
    f"📨 Editais INTERNACIONAIS (BR–NL/BR–DE) — últimos {DAYS} dias"
)

# **Conjuntos de idioma/país** (você pode ajustar via ENV se quiser)
# Formato: [(lang, country)]
LANG_COUNTRY_PAIRS = [
    ("en", "US"),
    ("nl", "NL"),
    ("de", "DE"),
    ("pt", "BR"),
]

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASS = os.environ["GMAIL_APP_PASS"]
EMAIL_TO = os.environ["EMAIL_TO_EXTERIOR2"]

# ===== Termos – foco BR–NL / BR–DE + temas do seu CV =====
TERMS = [
    # União Europeia (chamadas/calls)
    'site:cordis.europa.eu Brazil cooperation "call for proposals"',
    'Horizon Europe Brazil cooperation call',
    'site:ec.europa.eu Brazil cooperation call',
    'site:erc.europa.eu Brazil cooperation',

    # Holanda ↔ Brasil
    'site:nwo.nl Brazil cooperation',
    'site:nwo.nl "Brazil" "call"',
    'site:nwo.nl "bilateral" Brazil',
    'site:euraxess.ec.europa.eu Brazil Netherlands call',

    # Alemanha ↔ Brasil
    'site:dfg.de Brazil cooperation',
    'site:dfg.de "Brazil" "call"',
    'site:daad.de Brazil research funding',
    'site:bmbf.de Brazil cooperation call',
    'site:humboldt-foundation.de Brazil fellowship',

    # Agências brasileiras — bilaterais com NL/DE
    'site:fapesp.br Holanda chamada conjunta',
    'site:fapesp.br Alemanha chamada conjunta',
    'site:cnpq.br Holanda chamada',
    'site:cnpq.br Alemanha chamada',
    'site:capes.gov.br Holanda chamada',
    'site:capes.gov.br Alemanha chamada',
    'site:confap.org.br Holanda chamada',
    'site:confap.org.br Alemanha chamada',

    # ==== Temas conectados ao seu CV (sinônimos/variações) ====
    # Descarbonização portuária / OPS / energia
    'port decarbonisation call funding',
    'green ports funding call',
    'onshore power supply funding call',
    'shore power funding call',
    'cold ironing funding call',
    'OPS ports grant call',
    'maritime decarbonisation grant call',
    'energy transition ports call funding',

    # Combustíveis & vetores energéticos
    'green hydrogen port funding call',
    'ammonia maritime funding call',
    'methanol maritime funding call',
    'e-fuels maritime funding call',

    # Interfaces e sustentabilidade
    'port-city interface funding call',
    'sustainable ports grant call',
    'circular economy ports call',
    'blue economy funding call',
    'climate neutrality ports call',
    'SDG ports funding call',
    'sustainability reporting maritime funding',

    # Exemplos institucionais ligados aos temas
    'site:portofrotterdam.com decarbonisation funding',
]

def buscar_multilingue(termos, pairs, dias, max_per_termo):
    """
    Faz busca em vários idiomas/países e consolida resultados por termo,
    removendo duplicados (mesmo link ou mesmo título).
    """
    hoje = datetime.date.today()
    limite = hoje - datetime.timedelta(days=dias)
    resultados = {}

    for termo in termos:
        vistos_por_link = set()
        vistos_por_titulo = set()
        itens = []

        for lang, country in pairs:
            q = quote_plus(termo)
            url = f"https://news.google.com/rss/search?q={q}&hl={lang}&gl={country}&ceid={country}:{lang}"
            feed = feedparser.parse(url)

            for e in feed.entries:
                dp = e.get("published_parsed")
                if not dp:
                    continue
                d = datetime.date(*dp[:3])
                if d < limite:
                    continue

                title = (e.title or "").strip()
                link = (e.link or "").strip()

                # Deduplicação por link e por título
                key_link = link.lower()
                key_title = title.lower()

                if key_link in vistos_por_link or key_title in vistos_por_titulo:
                    continue

                vistos_por_link.add(key_link)
                vistos_por_titulo.add(key_title)

                itens.append({
                    "data": d.strftime("%d/%m/%Y"),
                    "titulo": title,
                    "link": link,
                    "lang": lang,
                    "country": country,
                })

        # Ordena por data desc e limita
        itens = sorted(
            itens,
            key=lambda x: datetime.datetime.strptime(x["data"], "%d/%m/%Y"),
            reverse=True
        )[:max_per_termo]

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
      .pill { font-size: 12px; color: #555; background:#f0f0f0; padding:2px 6px; border-radius:10px; }
    </style>
    """
    head = (f"<h2>Editais INTERNACIONAIS (BR–NL/BR–DE) — últimos {dias} dias</h2>"
            f"<p class='muted'>Fonte: Google News RSS • Idiomas: EN/NL/DE/PT • Deduplicação por link/título.</p>")
    blocks = []
    for termo, itens in noticias.items():
        if not itens:
            blocks.append(f"<div class='termo'>🔎 {termo}</div><div class='nores'>⚠️ Sem resultados</div>")
        else:
            linhas = "".join(
                f"<tr>"
                f"<td>{i['data']}</td>"
                f"<td><a href='{i['link']}' target='_blank' rel='noopener noreferrer'>{i['titulo']}</a><br>"
                f"<span class='pill'>{i['lang'].upper()}-{i['country'].upper()}</span></td>"
                f"</tr>"
                for i in itens
            )
            blocks.append(
                f"<div class='termo'>🔎 {termo}</div>"
                f"<table><thead><tr><th>Data</th><th>Título / Link</th></tr></thead>"
                f"<tbody>{linhas}</tbody></table>"
            )
    return f"<!DOCTYPE html><html><head>{style}</head><body>{head}{''.join(blocks)}</body></html>"

def txt_email(noticias, dias):
    out = [f"Editais INTERNACIONAIS (BR–NL/BR–DE) — últimos {dias} dias", ""]
    for termo, itens in noticias.items():
        out.append(f"🔎 {termo}")
        if not itens:
            out.append("  - Sem resultados")
        else:
            for i in itens[:5]:
                out.append(f"  - [{i['data']}] {i['titulo']} ({i['lang'].upper()}-{i['country'].upper()})  {i['link']}")
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
    data = buscar_multilingue(TERMS, LANG_COUNTRY_PAIRS, DAYS, MAX_PER_TERM)
    enviar(txt_email(data, DAYS), html_email(data, DAYS))
    total = sum(len(v) for v in data.values())
    print(f"EXTERIOR2 OK: {total} itens enviados para {EMAIL_TO}")

if __name__ == "__main__":
    main()
