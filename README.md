# Borç / Varlık Takip

335g gümüş + PHE fon + faiz borcunun toplam değerini takip edip, ödeme planını, ödedikçe düşen bakiyeyi
ve **ayın 5'inde otomatik Telegram + mail hatırlatmasını** gösteren Streamlit uygulaması.

## Dosyalar

| Dosya | Ne işe yarar |
|---|---|
| `app.py` | Streamlit arayüzü |
| `hesaplama.py` | Fiyat çekme + faiz hesaplama (app.py ve notify.py ortak kullanır) |
| `data_store.py` | `data.json` üzerinde okuma/yazma |
| `git_sync.py` | Her değişiklikten sonra `data.json`'ı otomatik commit+push eder |
| `notify.py` | GitHub Actions'ın ayın 5'inde çalıştırdığı bildirim scripti |
| `data.json` | Tüm veri (ayarlar + ödemeler) — hem Streamlit hem GitHub Actions bunu okur |
| `.github/workflows/monthly-notify.yml` | Cron tanımı |

## Neden SQLite değil de JSON + git?

Streamlit Cloud'daki uygulama ile GitHub Actions'taki cron job'u **farklı, birbirinden habersiz ortamlar**.
Cron job'un "kalan borç ne kadar, kaç taksit ödendi" gibi güncel veriyi görebilmesi için, Streamlit'in her
kaydettiği değişikliği GitHub'a **commit+push** etmesi lazım. Bu yüzden veri SQLite yerine düz `data.json`
dosyasında tutuluyor; app.py her "Kaydet"/ödeme ekle-düzenle-sil işleminde bunu otomatik commit'liyor.

## Kurulum — Streamlit Cloud tarafı

1. Repoyu GitHub'a push'la, Streamlit Cloud'da deploy et (öncekiyle aynı).
2. **Streamlit Cloud > App > Settings > Secrets** kısmına şunu ekle:

   ```toml
   GH_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxx"
   GH_REPO = "kullaniciadi/repo-adi"
   ```

   `GH_TOKEN`: GitHub'da **Settings > Developer settings > Personal access tokens > Fine-grained tokens**
   üzerinden, sadece bu repoya **Contents: Read and write** izni olan bir token oluştur.

   Bu secrets olmadan da uygulama çalışır, sadece otomatik GitHub senkronu atlanır (yerelde normal kaydeder).

## Kurulum — Bildirim tarafı (GitHub Actions)

Repo **Settings > Secrets and variables > Actions > New repository secret** üzerinden şunları ekle:

| Secret | Açıklama |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram'da [@BotFather](https://t.me/BotFather)'a `/newbot` yazarak alınır |
| `TELEGRAM_CHAT_ID` | Botunla bir kere mesajlaşıp [@userinfobot](https://t.me/userinfobot)'tan kendi chat id'ni öğren |

(Mail bildirimi kaldırıldı, sadece Telegram var. İstersen ilerde `GMAIL_USER` + `GMAIL_APP_PASSWORD`
secret'larını eklersin, `notify.py` mail kısmını otomatik ekler — kod zaten hazır, sadece secret eksik olduğu
için atlıyor.)

Kurulumdan sonra **Actions** sekmesinden `Aylık Borç Hatırlatma` workflow'unu seçip **Run workflow** ile
elle bir kere test et — cron'u ayın 5'ine kadar beklemene gerek yok.

Cron zamanı `0 6 5 * *` = her ayın 5'i, 06:00 UTC = **09:00 Türkiye saati**. Değiştirmek istersen
`.github/workflows/monthly-notify.yml` içindeki cron satırını düzenle.

## Yerelde çalıştırma

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Fiyatlar nereden geliyor?

- **Gram gümüş**: https://altin.doviz.com/gumus (5 dk cache'li).
- **PHE fon fiyatı**: TEFAS'ın 2026'da yenilenen resmi API'si (`pytefas` kütüphanesi). fintables de zaten
  fiyatı TEFAS'tan alıyor; fintables sayfası JS ile render ettiği için direkt scrape güvenilir değildi.
- Kaynak erişilemezse otomatik manuel giriş kutusuna düşer, hiçbir şey kırılmaz.

### Tek seferlik: PHE pay adedi

```
adet = 35000 / (o günkü PHE pay fiyatı)
```

Bunu sol panelden bir kere gir, gerisi otomatik güncellenir.

## Faiz Borcu

- Anapara, **başlangıç tarihi**, **oran** (aylık/yıllık %) ve **tip** (bileşik/basit) giriyorsun.
- Uygulama her açılışta `bugün - başlangıç tarihi` gün farkını alıp faizi otomatik hesaplıyor.
- Bileşik: `anapara x (1+oran)^dönem_sayısı` — Basit: `anapara x (1 + oran x dönem_sayısı)`.
- Ödeme yaptıkça toplam kalan (gümüş + PHE + işleyen faiz borcu - ödenen) küçülüyor, güncel taksit ona göre
  yeniden hesaplanıyor.

## Kullanım

- Sol panelde gümüş gram sayısı, PHE pay adedi, faiz ayarları ve taksit sayısı ayarlanıyor — fiyatlar otomatik geliyor.
- Ana ekranda toplam varlık/borç değeri, ödenen, kalan ve **güncel taksit tutarı** otomatik hesaplanıyor.
- "Ödeme Gir" formundan her ödemeyi kaydettikçe kalan ve güncel taksit otomatik güncelleniyor; her satırın
  yanındaki ✏️ ile geçmiş ödemeleri düzenleyebilir, 🗑️ ile silebilirsin.
- "🔄 Fiyatları Şimdi Yenile" butonuyla cache'i temizleyip anlık fiyatı yeniden çekebilirsin.
- Her kayıt işleminde `data.json` otomatik olarak GitHub'a commit+push edilir (secrets tanımlıysa), böylece
  ayın 5'indeki otomatik bildirim her zaman güncel veriyle çalışır.
