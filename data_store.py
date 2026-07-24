"""data.json üzerinde okuma/yazma. SQLite yerine JSON kullanıyoruz çünkü
git commit/push ile GitHub Actions'a taşınabilir olması lazım (binary db yerine
düz metin dosyası diff'lemesi ve senkronu çok daha kolay)."""
import json
import os
from datetime import date, datetime

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")

DEFAULT_DATA = {
    "settings": {
        "gumus_gram": 335,
        "gumus_fiyat": 0,
        "phe_adet": 0,
        "phe_fiyat": 0,
        "faiz_anapara": 45000,
        "faiz_orani": 0,
        "faiz_periyot": "Aylık",
        "faiz_tip": "Bileşik",
        "faiz_baslangic": date.today().isoformat(),
        "taksit_sayisi": 5,
    },
    "payments": [],
    "next_id": 1,
}


def _load():
    if not os.path.exists(DATA_PATH):
        _save(DEFAULT_DATA)
        return json.loads(json.dumps(DEFAULT_DATA))
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    # eksik anahtarları default'tan tamamla (şema göçü)
    for k, v in DEFAULT_DATA["settings"].items():
        data.setdefault("settings", {}).setdefault(k, v)
    data.setdefault("payments", [])
    data.setdefault("next_id", 1)
    return data


def _save(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_settings():
    return _load()["settings"]


def update_settings(**kwargs):
    data = _load()
    data["settings"].update(kwargs)
    _save(data)


def get_payments():
    """En yeni tarih en üstte olacak şekilde döner."""
    data = _load()
    rows = sorted(data["payments"], key=lambda p: (p["tarih"], p["id"]), reverse=True)
    return rows


def add_payment(tarih, tutar, not_):
    data = _load()
    pid = data["next_id"]
    data["payments"].append(
        {
            "id": pid,
            "tarih": tarih.isoformat() if hasattr(tarih, "isoformat") else tarih,
            "tutar": tutar,
            "not_": not_,
            "created_at": datetime.now().isoformat(),
        }
    )
    data["next_id"] = pid + 1
    _save(data)
    return pid


def update_payment(payment_id, tarih, tutar, not_):
    data = _load()
    for p in data["payments"]:
        if p["id"] == payment_id:
            p["tarih"] = tarih.isoformat() if hasattr(tarih, "isoformat") else tarih
            p["tutar"] = tutar
            p["not_"] = not_
            break
    _save(data)


def delete_payment(payment_id):
    data = _load()
    data["payments"] = [p for p in data["payments"] if p["id"] != payment_id]
    _save(data)


def toplam_odenen():
    return sum(p["tutar"] for p in get_payments())
