from datetime import date

import streamlit as st

from data_store import (
    add_payment,
    delete_payment,
    get_payments,
    get_settings,
    toplam_odenen,
    update_payment,
    update_settings,
)
from git_sync import commit_and_push
from hesaplama import fetch_gumus_fiyat as _fetch_gumus_fiyat
from hesaplama import fetch_phe_fiyat as _fetch_phe_fiyat
from hesaplama import hesapla_faiz_borcu

st.set_page_config(page_title="Borç/Varlık Takip", page_icon="💰", layout="centered")

fetch_gumus_fiyat = st.cache_data(ttl=300, show_spinner=False)(_fetch_gumus_fiyat)
fetch_phe_fiyat = st.cache_data(ttl=300, show_spinner=False)(_fetch_phe_fiyat)


def kaydet_ve_senkronla(basari_mesaji="Kaydedildi kanka."):
    ok, hata = commit_and_push("Ayarlar/ödeme güncellendi")
    if ok:
        st.success(f"{basari_mesaji} (GitHub'a da senkronlandı ✅)")
    elif hata and "tanımlı değil" in hata:
        st.success(basari_mesaji)
    else:
        st.warning(f"{basari_mesaji} Ama GitHub senkronu başarısız: {hata}")


# ---------- UI ----------
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
    faiz_anapara = st.number_input("Anapara (TL)", value=float(s["faiz_anapara"]), step=100.0)
    faiz_baslangic = st.date_input(
        "Borcun başlangıç tarihi", value=date.fromisoformat(s["faiz_baslangic"])
    )
    c1, c2 = st.columns(2)
    faiz_periyot = c1.selectbox("Periyot", ["Aylık", "Yıllık"],
                                 index=["Aylık", "Yıllık"].index(s["faiz_periyot"]))
    faiz_tip = c2.selectbox("Tip", ["Bileşik", "Basit"],
                             index=["Bileşik", "Basit"].index(s["faiz_tip"]))
    faiz_orani = st.number_input(
        f"{faiz_periyot} faiz oranı (%)", value=float(s["faiz_orani"]), step=0.1, format="%.2f"
    )
    faiz_borc = hesapla_faiz_borcu(faiz_anapara, faiz_orani, faiz_periyot, faiz_tip, faiz_baslangic)
    gecen_gun = max((date.today() - faiz_baslangic).days, 0)
    st.caption(f"📈 Güncel: {faiz_borc:,.2f} TL ({gecen_gun} gün geçti, +{faiz_borc - faiz_anapara:,.2f} TL faiz)")

    st.subheader("Ödeme Planı")
    taksit_sayisi = st.number_input("Toplam taksit sayısı (ay)", value=int(s["taksit_sayisi"]), step=1, min_value=1)

    st.subheader("🔔 Aylık Bildirim")
    st.caption(
        "Ayın 5'inde Telegram + mail ile otomatik hatırlatma gönderilir "
        "(GitHub Actions üzerinden — kurulum için README'ye bak)."
    )

    if st.button("💾 Ayarları Kaydet", use_container_width=True):
        update_settings(
            gumus_gram=gumus_gram, gumus_fiyat=gumus_fiyat, phe_adet=phe_adet, phe_fiyat=phe_fiyat,
            faiz_anapara=faiz_anapara, faiz_orani=faiz_orani, faiz_periyot=faiz_periyot,
            faiz_tip=faiz_tip, faiz_baslangic=faiz_baslangic.isoformat(),
            taksit_sayisi=int(taksit_sayisi),
        )
        kaydet_ve_senkronla()
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
col3.metric("🏦 Faiz Borcu", f"{faiz_borc:,.0f} TL", help=f"Anapara {faiz_anapara:,.0f} TL + işleyen faiz")

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
            kaydet_ve_senkronla(f"{tutar:,.0f} TL kaydedildi.")
            st.rerun()
        else:
            st.warning("Tutar 0'dan büyük olmalı hacı.")

st.subheader("📜 Ödeme Geçmişi")
rows = get_payments()
if rows:
    if "duzenlenen_id" not in st.session_state:
        st.session_state.duzenlenen_id = None

    for p in rows:
        pid, tarih_str, tutar_val, not_val = p["id"], p["tarih"], p["tutar"], p["not_"]
        if st.session_state.duzenlenen_id == pid:
            with st.form(f"duzenle_form_{pid}"):
                st.caption(f"Ödeme #{pid} düzenleniyor")
                c1, c2 = st.columns(2)
                yeni_tarih = c1.date_input("Tarih", value=date.fromisoformat(tarih_str), key=f"tarih_{pid}")
                yeni_tutar = c2.number_input("Tutar (TL)", value=float(tutar_val), min_value=0.0, step=100.0, key=f"tutar_{pid}")
                yeni_not = st.text_input("Not", value=not_val or "", key=f"not_{pid}")
                bc1, bc2 = st.columns(2)
                kaydet = bc1.form_submit_button("💾 Kaydet", use_container_width=True)
                vazgec = bc2.form_submit_button("Vazgeç", use_container_width=True)
                if kaydet:
                    update_payment(pid, yeni_tarih, yeni_tutar, yeni_not)
                    st.session_state.duzenlenen_id = None
                    kaydet_ve_senkronla("Güncellendi.")
                    st.rerun()
                if vazgec:
                    st.session_state.duzenlenen_id = None
                    st.rerun()
        else:
            c1, c2, c3, c4, c5 = st.columns([2, 2, 4, 1, 1])
            c1.write(tarih_str)
            c2.write(f"{tutar_val:,.0f} TL")
            c3.write(not_val or "—")
            if c4.button("✏️", key=f"edit_{pid}"):
                st.session_state.duzenlenen_id = pid
                st.rerun()
            if c5.button("🗑️", key=f"del_{pid}"):
                delete_payment(pid)
                commit_and_push("Ödeme silindi")
                st.rerun()
else:
    st.caption("Henüz ödeme girilmemiş.")
