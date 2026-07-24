"""GitHub Actions cron job'u tarafından çalıştırılır (ayın 5'i).
data.json'daki güncel durumu okuyup Telegram + mail ile özet gönderir.

Gerekli GitHub Actions secrets (repo Settings > Secrets and variables > Actions):
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID
    GMAIL_USER
    GMAIL_APP_PASSWORD
    NOTIFY_EMAIL   (opsiyonel, verilmezse GMAIL_USER'a gönderilir)
"""
import os
import smtplib
from datetime import date
from email.mime.text import MIMEText

import requests

from data_store import get_payments, get_settings, toplam_odenen
from hesaplama import fetch_gumus_fiyat, fetch_phe_fiyat, hesapla_faiz_borcu


def build_message() -> str:
    s = get_settings()

    try:
        gumus_fiyat = fetch_gumus_fiyat()
    except Exception:
        gumus_fiyat = s["gumus_fiyat"] or 0

    try:
        phe_fiyat = fetch_phe_fiyat()
    except Exception:
        phe_fiyat = s["phe_fiyat"] or 0

    gumus_deger = s["gumus_gram"] * gumus_fiyat
    phe_deger = s["phe_adet"] * phe_fiyat
    faiz_borc = hesapla_faiz_borcu(
        s["faiz_anapara"], s["faiz_orani"], s["faiz_periyot"], s["faiz_tip"],
        date.fromisoformat(s["faiz_baslangic"]),
    )
    toplam = gumus_deger + phe_deger + faiz_borc
    odenen = toplam_odenen()
    kalan = max(toplam - odenen, 0)

    odeme_sayisi = len(get_payments())
    kalan_ay = max(int(s["taksit_sayisi"]) - odeme_sayisi, 1)
    guncel_taksit = kalan / kalan_ay if kalan_ay else 0

    return (
        "💰 Borç/Varlık Takip — Aylık Hatırlatma\n\n"
        f"🪙 Gümüş: {gumus_deger:,.0f} TL\n"
        f"📈 PHE Fon: {phe_deger:,.0f} TL\n"
        f"🏦 Faiz Borcu: {faiz_borc:,.0f} TL\n"
        "—\n"
        f"Toplam: {toplam:,.0f} TL\n"
        f"Ödenen: {odenen:,.0f} TL\n"
        f"Kalan: {kalan:,.0f} TL\n\n"
        f"📅 Bu ayki taksit tutarın: {guncel_taksit:,.0f} TL\n"
        f"(kalan {kalan_ay} taksit / {s['taksit_sayisi']} toplam taksit)"
    )


def send_telegram(msg: str):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": msg},
        timeout=15,
    )
    r.raise_for_status()


def send_email(msg: str):
    user = os.environ["GMAIL_USER"]
    pw = os.environ["GMAIL_APP_PASSWORD"]
    to = os.environ.get("NOTIFY_EMAIL", user)

    m = MIMEText(msg)
    m["Subject"] = "Borç/Varlık Takip - Aylık Hatırlatma"
    m["From"] = user
    m["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(user, pw)
        smtp.send_message(m)


if __name__ == "__main__":
    mesaj = build_message()
    print(mesaj)

    hatalar = []
    try:
        send_telegram(mesaj)
        print("✅ Telegram gönderildi.")
    except Exception as e:
        hatalar.append(f"Telegram: {e}")

    try:
        send_email(mesaj)
        print("✅ Mail gönderildi.")
    except Exception as e:
        hatalar.append(f"Email: {e}")

    if hatalar:
        raise SystemExit("\n".join(hatalar))
