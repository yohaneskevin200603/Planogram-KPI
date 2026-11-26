"""
Skrip auto-refresh Planogram_Storage.csv dari LWA.
Kode login & download di bawah ini sudah diisi dari hasil rekaman playwright codegen.

CARA PAKAI:
1. Pastikan secrets_lwa.json sudah ada di folder yang sama dengan file ini, isi:
   { "username": "dyah", "password": "PASSWORD_ASLI_KAMU", "github_token": "" }
   (ganti PASSWORD_ASLI_KAMU dengan password LWA yang sebenarnya)
2. Jalankan: python refresh_planogram.py
3. Cek Planogram_Storage.csv di folder KPI, tanggal "Date modified" harus berubah.
4. Kalau sudah jalan lancar berkali-kali manual, baru jadwalkan lewat Task Scheduler.
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

# --- Konfigurasi: sesuaikan kalau folder project kamu beda ---
FOLDER_PROJECT = Path(r"D:\DNG OTW RLM\KPI")
FILE_SECRETS = Path(__file__).parent / "secrets_lwa.json"
FOLDER_DOWNLOAD = Path(__file__).parent / "downloads"
FOLDER_DOWNLOAD.mkdir(exist_ok=True)


def muat_secrets():
    if not FILE_SECRETS.exists():
        print(f"ERROR: {FILE_SECRETS} tidak ditemukan. Buat file itu dulu, isi username & password LWA.")
        sys.exit(1)
    cfg = json.loads(FILE_SECRETS.read_text())
    if not cfg.get("username") or not cfg.get("password"):
        print("ERROR: username/password di secrets_lwa.json masih kosong.")
        sys.exit(1)
    return cfg


def main():
    cfg = muat_secrets()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)  # True = jalan diam-diam, tidak tampil jendelanya
        context = browser.new_context()
        page = context.new_page()

        page.goto("http://192.168.99.3/logisticwebappdcg261/Account/Login")
        page.get_by_role("textbox", name="Username").click()
        page.get_by_role("textbox", name="Username").fill(cfg["username"])
        page.get_by_role("textbox", name="Username").press("Tab")
        page.get_by_role("textbox", name="Password").fill(cfg["password"])
        page.get_by_role("button", name="Sign In").click()

        page.get_by_role("link", name="LAP PLANOGRAM").click()
        page.get_by_role("link", name="LAPORAN PLANOGRAM").click()
        page.get_by_role("link", name="LISTING PLANOGRAM").click()
        page.get_by_role("radio", name="Storage").check()

        with page.expect_download() as download_info:
            page.get_by_role("button", name="Download CSV").click()
        download = download_info.value

        tujuan_sementara = FOLDER_DOWNLOAD / f"Planogram_Storage_{datetime.now():%Y%m%d_%H%M}.csv"
        download.save_as(tujuan_sementara)
        print(f"Download tersimpan: {tujuan_sementara}")

        tujuan_akhir = FOLDER_PROJECT / "Planogram_Storage.csv"
        shutil.copy(tujuan_sementara, tujuan_akhir)
        print(f"File project diperbarui: {tujuan_akhir}")

        context.close()
        browser.close()

    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Berhasil.")

    # ------------------------------------------------------------------
    # OPSIONAL: auto-push ke GitHub. Baru aktifkan setelah langkah di atas
    # terbukti jalan stabil berkali-kali tanpa error. Tanya saya dulu kalau
    # belum pernah setup git token / auto-push sebelumnya.
    # ------------------------------------------------------------------
    # import subprocess
    # subprocess.run(["git", "-C", str(FOLDER_PROJECT), "add", "Planogram_Storage.csv"], check=True)
    # subprocess.run(["git", "-C", str(FOLDER_PROJECT), "commit", "-m", f"auto-refresh {datetime.now():%Y-%m-%d %H:%M}"], check=True)
    # subprocess.run(["git", "-C", str(FOLDER_PROJECT), "push"], check=True)


if __name__ == "__main__":
    main()
