"""Her veri değişikliğinden sonra data.json'ı GitHub'a otomatik commit+push eder.
Böylece GitHub Actions (cron) her zaman en güncel veriyi görür.

Gerekli Streamlit secrets (Streamlit Cloud > Settings > Secrets):
    GH_TOKEN = "ghp_xxx..."   # repo yazma izni olan bir GitHub Personal Access Token
    GH_REPO  = "kullaniciadi/repo-adi"
"""
import subprocess

import streamlit as st


def _run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def commit_and_push(message="Otomatik güncelleme"):
    """data.json'ı commit'leyip push'lar. Başarısız olursa (False, hata_mesajı) döner,
    token'ı hata mesajına asla yazmaz."""
    try:
        token = st.secrets["GH_TOKEN"]
        repo = st.secrets["GH_REPO"]
    except Exception:
        return False, "GH_TOKEN / GH_REPO secrets tanımlı değil, otomatik senkron atlandı."

    try:
        branch_result = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        branch = branch_result.stdout.strip() or "main"

        _run(["git", "config", "user.email", "borctakip-bot@local"])
        _run(["git", "config", "user.name", "BorcTakip Bot"])
        _run(["git", "add", "data.json"])

        commit_result = _run(["git", "commit", "-m", message])
        if commit_result.returncode != 0 and "nothing to commit" not in (commit_result.stdout + commit_result.stderr).lower():
            return False, "commit hatası (token gizlendi)"

        remote_url = f"https://{token}@github.com/{repo}.git"
        push_result = _run(["git", "push", remote_url, f"HEAD:{branch}"])
        if push_result.returncode != 0:
            return False, "push hatası (token gizlendi)"

        return True, None
    except Exception:
        return False, "beklenmeyen senkron hatası"
