# monitor_editais_brasil.py
import os
import datetime
import feedparser
from urllib.parse import quote_plus
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ============== Parâmetros ==============
DAYS = int(os.getenv("DAYS_BR", "14"))
MAX_PER_TERM = int(os.getenv("MAX_PER_TERM_BR", "12"))

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASS = os.environ["GMAIL_APP_PASS"]
EMAIL_TO = os.environ["EMAIL_TO_BRASIL"]

# Domínios NACIONAIS (somente Brasil)
NATIONAL_DOMAINS = [
    "capes.gov.br",
    "cnpq.br",
    "finep.gov.br",
    "mcti.gov.br",
    "confap.org.br",
]

# Domínios ESTADUAIS (apenas Maranhão)
STATE_DOMAINS = [
    "fapema.br",
]

# termos “gatilhos” de edital/fomento
TERMS = [
    "edital", "chamada pública", "chamada", "seleção",
    "bolsa", "bolsas", "fomento", "pesquisa",
    "iniciação científica", "mestrado", "doutorado",
    "pós-doutorado", "pos-doutorado", "produtividade",
    "PPSUS", "Universal", "programa de bolsas",
]

# incluir e excluir (filtro simples de ruídos institucionais)
HARD_INCLUDE = [
    "edital", "chamada", "seleção", "bolsa", "bolsas",
    "fomento", "resultado", "retificação", "errata",
    "projeto", "pesquisa", "inscrições", "inscrição",
]
SOFT_EXCLUDE = [
    "licitação", "pregão", "contrato", "fornecedor",
    "transparência", "diário oficial", "ata de registro",
    "relatório de gestão",
]

def search_by_domains(terms, domains, label, days=DAYS, max_per_term=MAX_PER_TERM):
    hoje = datetime.date.today()
    limite = hoje - datetime.timedelta(days=days)
    blocos = []

    for domain in domains:
        for termo in terms:
            q = f'{termo} site:{domain}'
            url = (
                "https://news.google.com/rss/search?"
                f"q={quote_plus(q)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
            )
            feed = feedparser.parse(url)
            for entry in feed.entries:
                published = entry.get("published_parsed")
                if not published:
                    continue
                d = datetime.date(*published[:3])
                if d < limite:
                    continue

                title = (entry.title or "").strip()
                link = (entry.link or "").strip()
                lower = f"{title} {link}".lower()

                if not any(w in lower for w in HARD_INCLUDE):
                    continue
                if any(w in lower for w in SOFT_EXCLUDE):
                    continue

                blocos.append({
                    "label": label,
                    "domain": domain,
                    "term": termo,
                    "data": d.strftime("%d/%m/%Y"),
                    "titulo": title,
                    "link": link,
                })

    # ordena por data desc e limita por (label,domain,term)
    blocos.sort(key=lambda x: datetime.datetime.strptime(x["data"], "%d/%m/%Y"), reverse=True)

    # dedupe por link/título
    seen = set()
    dedup = []
    for it in blocos:
        key = (it["link"], it["titulo"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(it)

    # aplica limite por (label,domain,term)
    counted = {}
    limited = []
    for it in dedup:
        k = (it["label"], it["domain"], it["term"])
        counted[k] = counted.get(k, 0) + 1
        if counted[k] <= max_per_term:
            limited.append(it)
    return limited

def buscar_brasil():
    nacional = search_by_domains(TERMS, NATIONAL_DOMAINS, "Nacional")
    fapema = search_by_domains(TERMS, STATE_DOMAINS, "Maranhão (FAPEMA)")
    return nacional, fapema

def montar_email_html(nacional, fapema, dias=DAYS):
    style = """
    <style>
      body { font-family: Arial, Helvetica, sans-serif; font-size: 14px; color: #222; }
      h2 { margin: 0 0 10px 0; }
      h3 { margin: 16px 0 6px 0; }
      table { border-collapse: collapse; width: 100%; margin-top: 6px; }
      th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top; }
      th { background: #f5f5f5; text-align: left; }
      .muted { color: #666; }
    </style>"""
    head = f"<h2>Editais no Brasil — últimos {dias} dias</h2><p class='muted'>CAPES, CNPq, FINEP, MCTI, CONFAP + estadual (FAPEMA).</p>"

    def bloco(titulo, lista):
        if not lista:
            return f"<h3>{titulo}</h3><p>Nenhum resultado no período.</p>"
        linhas = "".join(
            f"<tr><td>{it['data']}</td><td>{it['domain']}</td>"
            f"<td>{it['term']}</td><td><a href='{it['link']}' target='_blank' rel='noopener'>{it['titulo']}</a></td></tr>"
            for it in lista
        )
        return f"""
          <h3>{titulo}</h3>
          <table>
            <thead><tr><th>Data</th><th>Domínio</th><th>Termo</th><th>Título / Link</th></tr></thead>
            <tbody>{linhas}</tbody>
          </table>
        """

    html = f"<!DOCTYPE html><html><head>{style}</head><body>{head}{bloco('Nacional', nacional)}{bloco('Maranhão (FAPEMA)', fapema)}</body></html>"
    return html

def montar_email_txt(nacional, fapema, dias=DAYS):
    lines = [f"Editais no Brasil — últimos {dias} dias", "", "== Nacional =="]
    if not nacional:
        lines.append("Nenhum resultado.")
    else:
        for it in nacional[:80]:
            lines.append(f"[{it['data']}] {it['domain']} | {it['term']} | {it['titulo']}  {it['link']}")
    lines.append("")
    lines.append("== Maranhão (FAPEMA) ==")
    if not fapema:
        lines.append("Nenhum resultado.")
    else:
        for it in fapema[:80]:
            lines.append(f"[{it['data']}] {it['domain']} | {it['term']} | {it['titulo']}  {it['link']}")
    return "\n".join(lines)

def enviar_email(html, txt):
    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = f"📨 Editais — Brasil (Nacional + FAPEMA) — últimos {DAYS} dias"
    msg.attach(MIMEText(txt, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(GMAIL_USER, GMAIL_APP_PASS)
        s.send_message(msg)

def main():
    nacional, fapema = buscar_brasil()
    html = montar_email_html(nacional, fapema, dias=DAYS)
    txt  = montar_email_txt(nacional, fapema, dias=DAYS)
    enviar_email(html, txt)

if __name__ == "__main__":
    main()
