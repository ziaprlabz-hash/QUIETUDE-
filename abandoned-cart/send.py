#!/usr/bin/env python3
"""Relance paniers abandonnés QUIETUDE via SMTP IONOS (contact@quietude-bands.com).

Identifiants lus dans l'environnement (jamais dans le code) :
  IONOS_SMTP_USER      (ex. contact@quietude-bands.com)
  IONOS_SMTP_PASSWORD
Optionnel : IONOS_SMTP_HOST (défaut smtp.ionos.fr), IONOS_SMTP_PORT (défaut 465)

Usage :
  python3 send.py                 # dry-run : génère les aperçus HTML dans previews/
  python3 send.py --test moi@x.fr # envoie 1 exemple FR + 1 EN à une adresse de test
  python3 send.py --send          # envoi réel (saute ceux déjà dans sent.log)
"""
import json, os, sys, ssl, smtplib, time, html
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path

HERE = Path(__file__).parent
CODE = os.environ.get("DISCOUNT_CODE", "COMEBACK10")
FROM = os.environ.get("IONOS_SMTP_USER", "contact@quietude-bands.com")

T = {
 "fr": {"subject": "Ton panier QUIETUDE t'attend (-10% pendant 48h)",
        "hi": "Salut {n},", "hi0": "Salut,",
        "l1": "Tu as laissé quelque chose dans ton panier :",
        "l2": "Bonne nouvelle : avec le code <b>{c}</b> tu as <b>-10%</b> sur ta commande, valable 48h.",
        "cta": "Finaliser ma commande", "total": "Total panier",
        "sig": "À très vite,<br>L'équipe QUIETUDE",
        "ps": "Une question sur la taille ou la livraison ? Réponds simplement à ce mail."},
 "en": {"subject": "Your QUIETUDE cart is waiting (10% off for 48h)",
        "hi": "Hey {n},", "hi0": "Hey,",
        "l1": "You left something in your cart:",
        "l2": "Good news: use code <b>{c}</b> for <b>10% off</b> your order, valid for 48 hours.",
        "cta": "Complete my order", "total": "Cart total",
        "sig": "See you soon,<br>The QUIETUDE team",
        "ps": "Questions about sizing or shipping? Just reply to this email."},
}

def build(r):
    t = T[r["lang"]]
    hi = t["hi"].format(n=html.escape(r["first_name"])) if r["first_name"] else t["hi0"]
    items = "".join(f"<li>{html.escape(i)}</li>" for i in r["items"])
    body = f"""<!doctype html><html><body style="margin:0;background:#f5f3ef;font-family:Helvetica,Arial,sans-serif;color:#111">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:32px 16px">
<table width="520" cellpadding="0" cellspacing="0" style="max-width:520px;background:#fff;border-radius:8px">
<tr><td style="padding:28px 32px;text-align:center;letter-spacing:6px;font-weight:700;font-size:20px;border-bottom:1px solid #eee">QUIETUDE</td></tr>
<tr><td style="padding:28px 32px;font-size:15px;line-height:1.6">
<p>{hi}</p><p>{t['l1']}</p><ul style="padding-left:18px">{items}</ul>
<p style="color:#555">{t['total']} : {r['total']} €</p>
<p>{t['l2'].format(c=CODE)}</p>
<p style="text-align:center;padding:12px 0"><a href="{html.escape(r['url'])}" style="background:#111;color:#fff;text-decoration:none;padding:14px 28px;border-radius:4px;font-weight:600;display:inline-block">{t['cta']}</a></p>
<p>{t['sig']}</p><p style="font-size:13px;color:#777">{t['ps']}</p>
</td></tr></table></td></tr></table></body></html>"""
    text = f"{hi.replace('<b>','').replace('</b>','')}\n\n{t['l1']}\n" + "\n".join("- "+i for i in r["items"]) + \
           f"\n\n{t['l2'].format(c=CODE).replace('<b>','').replace('</b>','')}\n\n{t['cta']} : {r['url']}\n\nQUIETUDE"
    m = EmailMessage()
    m["From"] = formataddr(("QUIETUDE", FROM)); m["To"] = r["email"]; m["Reply-To"] = FROM
    m["Subject"] = t["subject"]; m["Message-ID"] = make_msgid(domain="quietude-bands.com")
    m.set_content(text); m.add_alternative(body, subtype="html")
    return m, body

def smtp():
    host = os.environ.get("IONOS_SMTP_HOST", "smtp.ionos.fr"); port = int(os.environ.get("IONOS_SMTP_PORT", "465"))
    user, pw = os.environ.get("IONOS_SMTP_USER"), os.environ.get("IONOS_SMTP_PASSWORD")
    if not (user and pw): sys.exit("IONOS_SMTP_USER / IONOS_SMTP_PASSWORD manquants dans l'environnement.")
    ctx = ssl.create_default_context()
    s = smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) if port == 465 else smtplib.SMTP(host, port, timeout=20)
    if port != 465: s.starttls(context=ctx)
    s.login(user, pw); return s

def main():
    recips = json.loads((HERE / "recipients.json").read_text())
    args = sys.argv[1:]
    if not args:
        out = HERE / "previews"; out.mkdir(exist_ok=True)
        for r in recips:
            _, b = build(r); (out / f"{r['email']}.html").write_text(b)
        print(f"Dry-run : {len(recips)} aperçus dans {out}"); return
    s = smtp()
    if args[0] == "--test":
        for lang in ("fr", "en"):
            r = next(x for x in recips if x["lang"] == lang); m, _ = build(r)
            m.replace_header("To", args[1]); m.replace_header("Subject", "[TEST] " + m["Subject"]); s.send_message(m)
        print("2 emails de test envoyés à", args[1])
    elif args[0] == "--send":
        log = HERE / "sent.log"; done = set(log.read_text().split()) if log.exists() else set()
        for r in recips:
            if r["email"] in done: print("déjà envoyé :", r["email"]); continue
            m, _ = build(r); s.send_message(m)
            with log.open("a") as f: f.write(r["email"] + "\n")
            print("envoyé :", r["email"]); time.sleep(3)
    s.quit()

if __name__ == "__main__":
    main()
