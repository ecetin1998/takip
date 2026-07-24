# Borç / Varlık Takip

335g gümüş + PHE fon + faiz borcunun toplam değerini takip edip, 5 ayda (veya kaç ay istersen) ödeme planını
ve ödedikçe düşen bakiyeyi gösteren basit Streamlit uygulaması.

## Yerelde çalıştırma

```bash
pip install -r requirements.txt
streamlit run app.py
```

## GitHub + Streamlit Cloud'a deploy

1. Bu klasörü bir GitHub reposuna push'la (BEYSWC2026'da yaptığın gibi).
2. https://share.streamlit.io üzerinden repoyu seç, `app.py`'yi main file olarak göster, deploy et.

## Önemli not (kalıcılık)

Ödemeler ve ayarlar `borctakip.db` adlı bir SQLite dosyasına yazılıyor. Streamlit Community Cloud'da bu dosya
uygulama "uyumadığı" sürece kalıcı kalır ama **redeploy / reboot / uzun süre boşta kalma** durumunda sıfırlanabilir
(disk ephemeral). Yani rastgele silinme riskine karşı ödemeleri arada bir not almanı öneririm.

Eğer kalıcılığı garantilemek istersen ilerde Supabase'e (zaten FM projende kullanıyorsun) taşımak çok kolay —
istersen o versiyonunu da yazarım.

## Fiyatlar nereden geliyor?

- **Gram gümüş**: https://altin.doviz.com/gumus sayfası anlık olarak scrape ediliyor (5 dakika cache'li).
- **PHE fon fiyatı**: TEFAS'ın resmi API'si (fintables da bu veriyi TEFAS'tan alıyor; fintables sayfası
  fiyatı JS ile render ettiği için direkt oradan scrape etmek kırılgan olurdu, TEFAS daha sağlam).
- Bir siteler değişir/erişilemezse uygulama otomatik olarak o alan için **manuel giriş kutusu** gösterir,
  hiçbir şey kırılmaz.

### Tek seferlik: PHE pay adedi

Fon değerini otomatik hesaplayabilmek için kaç **pay** (adet) sahibi olduğunu bilmemiz lazım
(değer = adet x güncel pay fiyatı). 35.000 TL'yi hangi fiyattan aldıysan:

```
adet = 35000 / (o günkü PHE pay fiyatı)
```

Bunu sol panelden bir kere gir, gerisi otomatik güncellenir.

## Kullanım

- Sol panelde gümüş gram sayısı, PHE pay adedi, faiz borcu ve taksit sayısı ayarlanıyor — fiyatlar otomatik geliyor.
- Ana ekranda toplam varlık/borç değeri, ödenen, kalan ve **güncel taksit tutarı** (kalan tutar / kalan ay) otomatik
  hesaplanıyor.
- "Ödeme Gir" formundan her ödemeyi kaydettikçe kalan ve güncel taksit otomatik güncelleniyor.
- "🔄 Fiyatları Şimdi Yenile" butonuyla cache'i temizleyip anlık fiyatı yeniden çekebilirsin.
