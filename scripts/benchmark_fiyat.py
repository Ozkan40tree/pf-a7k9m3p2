#!/usr/bin/env python3
"""
Benchmark verilerini cek ve benchmark_gecmis.json olarak kaydet.

Benchmark seti (CLAUDE.md'ye gore):
- BIST100 (borsapy Index "XU100" birincil, yfinance "XU100.IS" yedek)
- Amerika Hisse (TL) (borsapy Fund "AFA" birincil, "ABE" yedek, son care yfinance ^GSPC*USDTRY)
- Gram Altin (borsapy FX "gram-altin" birincil, yfinance GC=F*USDTRY/31.1035 yedek)
- YAE fonu (borsapy Fund "YAE")
- TUFE (Sheets'ten okunur, ayri akista)

Mod 1 (--gecmis): 5 yillik gecmisi tek seferlik cek (ilk kurulum).
Mod 2 (gunluk): Mevcut JSON'a son gun ekle.

Kullanim:
  python scripts/benchmark_fiyat.py            # gunluk guncelleme
  python scripts/benchmark_fiyat.py --gecmis   # 5 yil gecmisi cek
"""

import argparse
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import gspread
import pandas as pd
import requests
import yfinance as yf
from google.oauth2.service_account import Credentials

try:
    import borsapy as bp
    BORSAPY_OK = True
except ImportError:
    BORSAPY_OK = False


REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_FILE = REPO_ROOT / "benchmark_gecmis.json"
TR_TZ = timezone(timedelta(hours=3))


def log(msg, level="INFO"):
    ts = datetime.now(TR_TZ).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def yfinance_seri(sembol, baslangic, bitis):
    """yfinance'tan tarih araligi serisi al. Cikti: {tarih: kapanis}"""
    try:
        ticker = yf.Ticker(sembol)
        hist = ticker.history(start=baslangic, end=bitis)
        if hist.empty:
            return {}
        seri = {}
        for tarih, row in hist.iterrows():
            kapanis = row.get("Close")
            if pd.isna(kapanis):
                continue
            seri[tarih.strftime("%Y-%m-%d")] = float(kapanis)
        return seri
    except Exception as e:
        log(f"yfinance hata ({sembol}): {e}", "WARN")
        return {}


def borsapy_index_seri(sembol, baslangic, bitis):
    """Borsapy Index serisi: bp.Index(sembol).history(start, end). Cikti: {tarih: Close}."""
    if not BORSAPY_OK:
        return {}
    try:
        idx = bp.Index(sembol)
        df = idx.history(start=baslangic, end=bitis)
        if df is None or df.empty:
            return {}
        seri = {}
        for tarih, row in df.iterrows():
            fiyat = row.get("Close")
            if fiyat is None or pd.isna(fiyat):
                continue
            seri[pd.to_datetime(tarih).strftime("%Y-%m-%d")] = float(fiyat)
        return seri
    except Exception as e:
        log(f"borsapy Index hata ({sembol}): {e}", "WARN")
        return {}


def borsapy_fx_seri(asset, baslangic, bitis):
    """Borsapy FX serisi: bp.FX(asset).history(start, end). Cikti: {tarih: Close}."""
    if not BORSAPY_OK:
        return {}
    try:
        fx = bp.FX(asset)
        df = fx.history(start=baslangic, end=bitis)
        if df is None or df.empty:
            return {}
        seri = {}
        for tarih, row in df.iterrows():
            fiyat = row.get("Close")
            if fiyat is None or pd.isna(fiyat):
                continue
            seri[pd.to_datetime(tarih).strftime("%Y-%m-%d")] = float(fiyat)
        return seri
    except Exception as e:
        log(f"borsapy FX hata ({asset}): {e}", "WARN")
        return {}


def borsapy_fund_seri(kod, baslangic, bitis):
    """Borsapy Fund serisi: bp.Fund(kod).history(start, end). Cikti: {tarih: Price}."""
    if not BORSAPY_OK:
        return {}
    try:
        f = bp.Fund(kod)
        df = f.history(start=baslangic, end=bitis)
        if df is None or df.empty:
            return {}
        seri = {}
        for tarih, row in df.iterrows():
            fiyat = row.get("Price")
            if fiyat is None or pd.isna(fiyat):
                continue
            seri[pd.to_datetime(tarih).strftime("%Y-%m-%d")] = float(fiyat)
        return seri
    except Exception as e:
        log(f"borsapy Fund hata ({kod}): {e}", "WARN")
        return {}


def bist100_seri(baslangic, bitis):
    """BIST100 - birincil borsapy Index('XU100'), yedek yfinance 'XU100.IS'."""
    seri = borsapy_index_seri("XU100", baslangic, bitis)
    if seri:
        log(f"BIST100: borsapy ile {len(seri)} kayit")
        return seri
    log("BIST100 borsapy bos, yfinance yedegine donuluyor.", "WARN")
    return yfinance_seri("XU100.IS", baslangic, bitis)


def tcmb_usd_anlik():
    """
    TCMB resmi XML'den anlik USD kurunu cek (sadece bugun, tek nokta).
    Benchmark scripti normalde tarihsel seri ister; TCMB sadece bugunu verir.
    Bu fonksiyon, yfinance USDTRY=X tamamen dustugunde, en azindan
    bugunku benchmark cizgisinin kopmamasi icin kullanilir.
    URL: https://www.tcmb.gov.tr/kurlar/today.xml
    Donus: float kur veya None
    """
    try:
        url = "https://www.tcmb.gov.tr/kurlar/today.xml"
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        for currency in root.findall("Currency"):
            if currency.get("CurrencyCode") == "USD":
                forex_sell = currency.find("ForexSelling")
                if forex_sell is not None and forex_sell.text:
                    try:
                        return float(forex_sell.text.strip())
                    except ValueError:
                        return None
        return None
    except Exception as e:
        log(f"TCMB USD anlik yedek hata: {e}", "WARN")
        return None


def usd_try_seri(baslangic, bitis):
    """
    USDTRY tarihsel seri - birincil borsapy FX('USD'), yedek yfinance 'USDTRY=X',
    son care TCMB anlik (sadece bugun, tek nokta).
    """
    seri = borsapy_fx_seri("USD", baslangic, bitis)
    if seri:
        log(f"USDTRY: borsapy ile {len(seri)} kayit")
        return seri
    log("USDTRY borsapy bos, yfinance yedegine donuluyor.", "WARN")
    seri = yfinance_seri("USDTRY=X", baslangic, bitis)
    if seri:
        return seri
    log("USDTRY yfinance de bos, TCMB anlik yedegine donuluyor (sadece bugun).", "WARN")
    tcmb_kur = tcmb_usd_anlik()
    if tcmb_kur is None:
        return {}
    bugun_str = datetime.now(TR_TZ).strftime("%Y-%m-%d")
    log(f"TCMB yedek: {bugun_str} -> {tcmb_kur:.4f}")
    return {bugun_str: tcmb_kur}


def amerika_hisse_seri(baslangic, bitis):
    """
    Amerika Hisse (TL) - Turk yatirimci perspektifi.
    Birincil: TEFAS AFA fonu (Amerika Hisse Senedi).
    Yedek: TEFAS ABE fonu (Amerika Hisse Senedi).
    Son care: yfinance ^GSPC * USDTRY (saf S&P500 yaklasimi, GitHub Actions
    IP'lerinden Yahoo Finance erisimi sorunlu oldugu icin genelde calismaz).

    Not: AFA/ABE saf S&P500 degil, Amerika hisse senedi pazarini takip eder.
    Endeks bilesimine bagli olarak S&P500'den hafif sapma gosterebilir;
    Turk yatirimci pratiginde "Amerika hissesi" karsilastirmasi icin yeterli.
    """
    seri = borsapy_fund_seri("AFA", baslangic, bitis)
    if seri:
        log(f"Amerika Hisse (TL, AFA): {len(seri)} kayit")
        return seri
    log("AFA bos, ABE yedegine donuluyor.", "WARN")
    seri = borsapy_fund_seri("ABE", baslangic, bitis)
    if seri:
        log(f"Amerika Hisse (TL, ABE): {len(seri)} kayit")
        return seri
    log("AFA ve ABE ikisi de bos, yfinance ^GSPC*USDTRY son caresine donuluyor.", "WARN")
    sp = yfinance_seri("^GSPC", baslangic, bitis)
    usd = usd_try_seri(baslangic, bitis)
    sonuc = {}
    for tarih, deger_usd in sp.items():
        kur = usd.get(tarih)
        if kur:
            sonuc[tarih] = deger_usd * kur
    return sonuc


def gram_altin_seri(baslangic, bitis):
    """
    Gram altin TL - birincil borsapy FX('gram-altin') direkt TL,
    yedek yfinance GC=F (USD/oz) * USDTRY / 31.1035.
    """
    seri = borsapy_fx_seri("gram-altin", baslangic, bitis)
    if seri:
        log(f"Gram altin: borsapy ile {len(seri)} kayit")
        return seri
    log("Gram altin borsapy bos, yfinance GC=F*USDTRY/31.1035 yedegine donuluyor.", "WARN")
    OZ_TO_GRAM = 31.1035
    altin = yfinance_seri("GC=F", baslangic, bitis)
    usd = usd_try_seri(baslangic, bitis)
    sonuc = {}
    for tarih, fiyat_usd_oz in altin.items():
        kur = usd.get(tarih)
        if kur:
            sonuc[tarih] = (fiyat_usd_oz * kur) / OZ_TO_GRAM
    return sonuc


def yae_seri(baslangic, bitis):
    """YAE TEFAS fonu serisi - borsapy ile (saidsurucu/borsapy).

    borsapy.Fund.history() TEFAS v2 API'sini kullanir; max 5 yil destekler.
    DataFrame: Date index, 'Price' sutunu.
    """
    if not BORSAPY_OK:
        log("borsapy import edilemedi, YAE atlanir.", "WARN")
        return {}
    try:
        f = bp.Fund("YAE")
        df = f.history(start=baslangic, end=bitis)
        if df is None or df.empty:
            return {}
        seri = {}
        for tarih, row in df.iterrows():
            fiyat = row.get("Price")
            if fiyat is None or pd.isna(fiyat):
                continue
            seri[pd.to_datetime(tarih).strftime("%Y-%m-%d")] = float(fiyat)
        return seri
    except Exception as e:
        log(f"YAE hata: {e}", "WARN")
        return {}


def tufe_oku_sheets():
    """TUFE sekmesinden veri oku (gunluk akista da yapilir, burada bagimsiz)."""
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    sheets_id = os.environ.get("SHEETS_ID")
    if not creds_json or not sheets_id:
        log("TUFE icin Sheets credentials yok, atlaniyor.", "WARN")
        return {}

    try:
        creds_dict = json.loads(creds_json)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(sheets_id)
        sheet = spreadsheet.worksheet("TUFE")
        data = sheet.get_all_values()
        if not data or len(data) < 2:
            return {}
        sonuc = {"gerceklesen": {}, "beklenti": {}}
        for row in data[1:]:
            if not row or not row[0].strip():
                continue
            ay = row[0].strip()
            try:
                ger = float(str(row[1]).strip().replace(",", ".")) if len(row) > 1 and row[1].strip() else None
            except (ValueError, IndexError):
                ger = None
            try:
                bek = float(str(row[2]).strip().replace(",", ".")) if len(row) > 2 and row[2].strip() else None
            except (ValueError, IndexError):
                bek = None
            if ger is not None:
                sonuc["gerceklesen"][ay] = ger
            if bek is not None:
                sonuc["beklenti"][ay] = bek
        return sonuc
    except Exception as e:
        log(f"TUFE okunamadi: {e}", "WARN")
        return {}


def gecmis_olustur():
    """5 yillik gecmis benchmark verilerini cek."""
    bugun = datetime.now(TR_TZ).date()
    bes_yil_once = bugun - timedelta(days=5 * 365 + 30)
    baslangic = str(bes_yil_once)
    bitis = str(bugun + timedelta(days=1))

    log(f"5 yillik benchmark gecmisi cekiliyor: {baslangic} -> {bitis}")

    log("BIST100 cekiliyor...")
    bist100 = bist100_seri(baslangic, bitis)
    log(f"  {len(bist100)} kayit")
    time.sleep(1)

    log("Amerika Hisse (TL) cekiliyor...")
    amerika_hisse = amerika_hisse_seri(baslangic, bitis)
    log(f"  {len(amerika_hisse)} kayit")
    time.sleep(1)

    log("Gram altin cekiliyor...")
    gram_altin = gram_altin_seri(baslangic, bitis)
    log(f"  {len(gram_altin)} kayit")
    time.sleep(1)

    log("YAE cekiliyor...")
    yae = yae_seri(baslangic, bitis)
    log(f"  {len(yae)} kayit")

    log("TUFE okunuyor...")
    tufe = tufe_oku_sheets()
    log(f"  Gerceklesen: {len(tufe.get('gerceklesen', {}))} | Beklenti: {len(tufe.get('beklenti', {}))}")

    return {
        "kayit_baslangic": baslangic,
        "son_guncelleme": datetime.now(TR_TZ).isoformat(timespec="seconds"),
        "seriler": {
            "bist100": bist100,
            "amerika_hisse": amerika_hisse,
            "gram_altin": gram_altin,
            "yae": yae,
            "tufe_aylik_gerceklesen": tufe.get("gerceklesen", {}),
            "tufe_aylik_beklenti": tufe.get("beklenti", {}),
        },
    }


def gunluk_guncelle():
    """Mevcut benchmark JSON'una son gunu ekle."""
    if not BENCHMARK_FILE.exists():
        log("HATA: benchmark_gecmis.json yok. Once --gecmis ile baslatilmali.", "ERROR")
        sys.exit(1)

    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        veri = json.load(f)

    bugun = datetime.now(TR_TZ).date()
    on_gun_once = bugun - timedelta(days=10)  # son 10 gun yedek
    baslangic = str(on_gun_once)
    bitis = str(bugun + timedelta(days=1))

    log(f"Gunluk guncelleme: {baslangic} -> {bitis}")

    yeni = {
        "bist100": bist100_seri(baslangic, bitis),
        "amerika_hisse": amerika_hisse_seri(baslangic, bitis),
        "gram_altin": gram_altin_seri(baslangic, bitis),
        "yae": yae_seri(baslangic, bitis),
    }

    # Mevcut serilere ekle (uzerine yazar - en taze veri kazanir)
    seriler = veri.get("seriler", {})
    for ad, yeni_seri in yeni.items():
        mevcut = seriler.get(ad, {})
        mevcut.update(yeni_seri)
        seriler[ad] = mevcut

    # TUFE'yi de guncelle (Sheets'ten)
    tufe = tufe_oku_sheets()
    if tufe.get("gerceklesen"):
        seriler["tufe_aylik_gerceklesen"] = tufe["gerceklesen"]
    if tufe.get("beklenti"):
        seriler["tufe_aylik_beklenti"] = tufe["beklenti"]

    veri["seriler"] = seriler
    veri["son_guncelleme"] = datetime.now(TR_TZ).isoformat(timespec="seconds")

    with open(BENCHMARK_FILE, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)

    log("benchmark_gecmis.json guncellendi.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gecmis", action="store_true", help="5 yillik gecmisi tek seferlik cek")
    args = parser.parse_args()

    if args.gecmis:
        veri = gecmis_olustur()
        with open(BENCHMARK_FILE, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
        log(f"benchmark_gecmis.json olusturuldu (5 yillik).")
    else:
        gunluk_guncelle()


if __name__ == "__main__":
    main()
