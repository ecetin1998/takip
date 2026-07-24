import re
import sqlite3
from datetime import date, datetime, timedelta

import requests
import streamlit as st
from bs4 import BeautifulSoup

DB_PATH = "borctakip.db"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

st.set_page_config(page_title="Borç/Varlık Takip", page_icon="💰", layout="centered")


def parse_tr_number(s: str) -> float:
    """'1.234,56' -> 1234.56 ; '87,33' -> 87.33"""
    s = s.strip()
    s = s.replace(".", "").replace(",", ".")
    return float(s)


# ---------- Canlı fiyat çekme ----------
@st.cache_data(ttl=300, show_spinner=False)
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


@st.cache_data(ttl=300, show_spinner=False)
def fetch_phe_fiyat():
    """TEFAS resmi API'sinden PHE fonunun son birim pay fiyatını çeker (TL).
    (fintables da bu veriyi TEFAS'tan alıyor, JS ile render ettiği için direkt
    fintables sayfasını scrape etmek güvenilir değil.)"""
    bugun = date.today()
    bas = bugun - timedelta(days=10)
    url = "https://www.tefas.gov.tr/api/DB/BindHistoryInfo"
    data = {
        "fontip": "YAT",
        "fonkod": "PHE",
        "bastarih": bas.strftime("%d.%m.%Y"),
        "bittarih": bugun.strftime("%d.%m.%Y"),
    }
    headers = {**UA, "Referer": "https://www.tefas.gov.tr/TarihselVeriler.aspx"}
    r = requests.post(url, data=data, headers=headers, timeout=10)
    r.raise_for_status()
    payload = r.json()
    rows = payload.get("data", [])
    if not rows:
        raise ValueError("TEFAS'tan PHE için veri dönmedi.")
    son = sorted(rows, key=lambda x: x["TARIH"])[-1]
    return float(son["FIYAT"])


# ---------- DB ----------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            gumus_gram REAL DEFAULT 335,
            gumus_fiyat REAL DEFAULT 0,
            phe_adet REAL DEFAULT 0,
            phe_fiyat REAL DEFAULT 0,
            faiz_borc REAL DEFAULT 45000,
            taksit_sayisi INTEGER DEFAULT 5
        )
        """
    )
    c.execute("SELECT COUNT(*) FROM settings")
    if c.fetchone()[0] == 0:
        c.execute(
            "INSERT INTO settings (id, gumus_gram, gumus_fiyat, phe_adet, phe_fiyat, faiz_borc, taksit_sayisi) "
            "VALUES (1, 335, 0, 0, 0, 45000, 5)"
        )
    conn.commit()

    # eski şemadan geçiş yapan varsa eksik kolonları ekle
    c.execute("PRAGMA table_info(settings)")
    cols = {row[1] for row in c.fetchall()}
    if "phe_adet" not in cols:
        c.execute("ALTER TABLE settings ADD COLUMN phe_adet REAL DEFAULT 0")
    if "phe_fiyat" not in cols:
        c.execute("ALTER TABLE settings ADD COLUMN phe_fiyat REAL DEFAULT 0")
    conn.commit()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            tutar REAL,
            not_ TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def get_settings():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT gumus_gram, gumus_fiyat, phe_adet, phe_fiyat, faiz_borc, taksit_sayisi FROM settings WHERE id = 1")
    row = c.fetchone()
    conn.close()
    return {
        "gumus_gram": row[0],
        "gumus_fiyat": row[1],
        "phe_adet": row[2],
        "phe_fiyat": row[3],
        "faiz_borc": row[4],
        "taksit_sayisi": row[5],
    }


def update_settings(gumus_gram, gumus_fiyat, phe_adet, phe_fiyat, faiz_borc, taksit_sayisi):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        UPDATE settings
        SET gumus_gram = ?, gumus_fiyat = ?, phe_adet = ?, phe_fiyat = ?, faiz_borc = ?, taksit_sayisi = ?
        WHERE id = 1
        """,
        (gumus_gram, gumus_fiyat, phe_adet, phe_fiyat, faiz_borc, taksit_sayisi),
    )
    conn.commit()
    conn.close()


def get_payments():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, tarih, tutar, not_ FROM payments ORDER BY tarih DESC, id DESC")
    rows = c.fetchall()
    conn.close()
    return rows


def add_payment(tarih, tutar, not_):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO payments (tarih, tutar, not_, created_at) VALUES (?, ?, ?, ?)",
        (tarih.isoformat(), tutar, not_, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def delete_payment(payment_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
    conn.commit()
    conn.close()


def toplam_odenen():
    rows = get_payments()
    return sum(r[2] for r in rows)


# ---------- UI ----------
init_db()
s = get_settings()

st.title("💰 Borç / Varlık Takip")

# --- Canlı fiyatları çek (cache'li, 5 dk) ---
gumus_fiyat_canli, gumus_hata = None, None
phe_fiyat_canli, phe_hata = None, None

try:
    gumus_fiyat_canli = fetch_gumus_fiyat()
except Exception as e:
    gumus_hata = str(e)

try:
    phe_fiyat_canli = fetch_phe_fiyat()
except Exception as e:
    phe_hata = str(e)

with st.sidebar:
    st.header("⚙️ Ayarlar")

    st.subheader("Gümüş")
    gumus_gram = st.number_input("Gümüş miktarı (gram)", value=float(s["gumus_gram"]), step=1.0)
    if gumus_hata:
        st.warning(f"Gümüş fiyatı çekilemedi: {gumus_hata}")
        gumus_fiyat = st.number_input(
            "Gram gümüş fiyatı (TL) — manuel gir", value=float(s["gumus_fiyat"] or 0), step=0.5
        )
    else:
        gumus_fiyat = gumus_fiyat_canli
        st.caption(f"✅ Canlı: {gumus_fiyat:,.2f} TL/gram (doviz.com)")

    st.subheader("PHE Hisse Senedi Fonu")
    phe_adet = st.number_input(
        "Sahip olduğun PHE pay adedi", value=float(s["phe_adet"] or 0), step=1.0,
        help="Bunu bir kere gir: 35.000 TL'yi hangi fiyattan aldıysan, o tutarı alış anındaki pay "
             "fiyatına bölüp adet sayısını yaz. Fiyat sonra otomatik güncellenir."
    )
    if phe_hata:
        st.warning(f"PHE fiyatı çekilemedi: {phe_hata}")
        phe_fiyat = st.number_input(
            "PHE pay fiyatı (TL) — manuel gir", value=float(s["phe_fiyat"] or 0), step=0.0001, format="%.6f"
        )
    else:
        phe_fiyat = phe_fiyat_canli
        st.caption(f"✅ Canlı: {phe_fiyat:,.6f} TL/pay (TEFAS)")

    st.subheader("Faiz Borcu")
    faiz_borc = st.number_input("Faize atılan borç (TL)", value=float(s["faiz_borc"]), step=100.0)

    st.subheader("Ödeme Planı")
    taksit_sayisi = st.number_input("Toplam taksit sayısı (ay)", value=int(s["taksit_sayisi"]), step=1, min_value=1)

    if st.button("💾 Ayarları Kaydet", use_container_width=True):
        update_settings(gumus_gram, gumus_fiyat, phe_adet, phe_fiyat, faiz_borc, int(taksit_sayisi))
        st.success("Kaydedildi kanka.")
        st.rerun()

    if st.button("🔄 Fiyatları Şimdi Yenile", use_container_width=True):
        fetch_gumus_fiyat.clear()
        fetch_phe_fiyat.clear()
        st.rerun()

# hesaplamalar (kaydedilmemiş güncel değerlerle canlı göster)
gumus_deger = gumus_gram * gumus_fiyat
phe_deger = phe_adet * phe_fiyat
toplam = gumus_deger + phe_deger + faiz_borc
odenen = toplam_odenen()
kalan = max(toplam - odenen, 0)

odeme_sayisi = len(get_payments())
kalan_ay = max(int(taksit_sayisi) - odeme_sayisi, 1)
guncel_taksit = kalan / kalan_ay if kalan_ay > 0 else 0

st.subheader("📊 Varlık Dağılımı")
col1, col2, col3 = st.columns(3)
col1.metric("🪙 Gümüş", f"{gumus_deger:,.0f} TL", help=f"{gumus_gram:g} gram x {gumus_fiyat:,.2f} TL")
col2.metric("📈 PHE Fon", f"{phe_deger:,.0f} TL", help=f"{phe_adet:g} pay x {phe_fiyat:,.6f} TL")
col3.metric("🏦 Faiz Borcu", f"{faiz_borc:,.0f} TL")

st.divider()

col4, col5, col6 = st.columns(3)
col4.metric("Toplam", f"{toplam:,.0f} TL")
col5.metric("Ödenen", f"{odenen:,.0f} TL", delta=f"-{odenen:,.0f}" if odenen else None)
col6.metric("Kalan", f"{kalan:,.0f} TL")

st.progress(min(odenen / toplam, 1.0) if toplam > 0 else 0)

st.info(f"📅 Güncel taksit tutarı: **{guncel_taksit:,.0f} TL** "
        f"(kalan {kalan_ay} taksit / {int(taksit_sayisi)} toplam taksit)")

st.divider()

st.subheader("➕ Ödeme Gir")
with st.form("odeme_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    tarih = c1.date_input("Tarih", value=date.today())
    tutar = c2.number_input("Tutar (TL)", min_value=0.0, step=100.0)
    not_ = st.text_input("Not (opsiyonel)")
    submitted = st.form_submit_button("Ödemeyi Kaydet", use_container_width=True)
    if submitted:
        if tutar > 0:
            add_payment(tarih, tutar, not_)
            st.success(f"{tutar:,.0f} TL kaydedildi.")
            st.rerun()
        else:
            st.warning("Tutar 0'dan büyük olmalı hacı.")

st.subheader("📜 Ödeme Geçmişi")
rows = get_payments()
if rows:
    for pid, tarih_str, tutar_val, not_val in rows:
        c1, c2, c3, c4 = st.columns([2, 2, 4, 1])
        c1.write(tarih_str)
        c2.write(f"{tutar_val:,.0f} TL")
        c3.write(not_val or "—")
        if c4.button("🗑️", key=f"del_{pid}"):
            delete_payment(pid)
            st.rerun()
else:
    st.caption("Henüz ödeme girilmemiş.")
