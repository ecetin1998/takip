"""Fiyat çekme ve faiz hesaplama fonksiyonları.
app.py (Streamlit) ve notify.py (GitHub Actions) tarafından ortak kullanılır."""
import re
from datetime import date

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def parse_tr_number(s: str) -> float:
    """'1.234,56' -> 1234.56 ; '87,33' -> 87.33"""
    s = s.strip()
    s = s.replace(".", "").replace(",", ".")
    return float(s)


def fetch_gumus_fiyat():
    """doviz.com/gumus sayfasından anlık gram gümüş fiyatını çeker (TL)."""
    url = "https://altin.doviz.com/gumus"
    r = requests.get(url, headers=UA, timeout=10)
    r.raise_for_status()
    text = BeautifulSoup(r.text, "html.parser").get_text(separator=" ")

    m = re.search(r"anlık olarak\s*([\d\.,]+)\s*TL", text)
    if not m:
        m = re.search(r"GRAM GÜMÜŞ\s*([\d\.,]+)", text, re.IGNORECASE)
    if not m:
        raise ValueError("Gümüş fiyatı sayfada bulunamadı (site yapısı değişmiş olabilir).")
    return parse_tr_number(m.group(1))


def fetch_phe_fiyat():
    """TEFAS'ın yeni (2026) resmi API'sinden PHE fonunun son birim pay fiyatını çeker (TL)."""
    from datetime import timedelta

    from pytefas import Crawler

    tefas = Crawler(timeout=15)
    bugun = date.today()
    bas = bugun - timedelta(days=10)
    df = tefas.fetch(bas.isoformat(), bugun.isoformat(), columns="info", fund_code="PHE")
    if df.empty:
        raise ValueError("TEFAS'tan PHE için veri dönmedi (tatil/hafta sonu olabilir).")
    son = df.sort_values("date").iloc[-1]
    return float(son["price"])


def hesapla_faiz_borcu(anapara, oran_yuzde, periyot, tip, baslangic_tarihi):
    """Anaparanın başlangıç tarihinden bugüne kadar faizle büyümüş halini hesaplar."""
    gecen_gun = max((date.today() - baslangic_tarihi).days, 0)
    periyot_gun = 30.0 if periyot == "Aylık" else 365.0
    donem_sayisi = gecen_gun / periyot_gun
    oran = oran_yuzde / 100.0

    if tip == "Bileşik":
        return anapara * (1 + oran) ** donem_sayisi
    else:
        return anapara * (1 + oran * donem_sayisi)
