#!/usr/bin/env python3
"""
Portfoy fiyat guncelleme scripti.

Akis:
1. Google Sheets'ten Ozkan_Portfoy ve Derya_Portfoy sekmelerini oku
2. Her enstruman icin guncel fiyati cek (yfinance, tefas-crawler)
3. prices.json yaz (fiyat verisi)
4. portfoy.json yaz (Sheets aynasi + hesaplanmis TL degerler)
5. Eger kapanis calistirmasi ise gecmis.json'a snapshot ekle

Kullanim: python scripts/fiyat_guncelle.py [--kapanis]
  --kapanis: Bu calistirma kapanis (18:35 cron) ise gecmis.json'a kayit yapar.

Cevre degiskenleri (GitHub Secrets):
- GOOGLE_SHEETS_CREDENTIALS: Service account JSON (string)
- SHEETS_ID: Google Sheets dosya ID'si
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import gspread
import pandas as pd
import requests
import yfinance as yf
from google.oauth2.service_account import Credentials

try:
    from tefas import Crawler as TefasCrawler
except ImportError:
    print("UYARI: tefas-crawler import edilemedi.")
    TefasCrawler = None


# =====================================================================
# SABITLER
# =====================================================================

# Repo kok dizini (script scripts/ icindeyse bir ust)
REPO_ROOT = Path(__file__).resolve().parent.parent

# Cikti dosyalari
PRICES_FILE = REPO_ROOT / "prices.json"
PORTFOY_FILE = REPO_ROOT / "portfoy.json"
GECMIS_FILE = REPO_ROOT / "gecmis.json"

# Sheets sekme adlari (sabit, CLAUDE.md'ye gore)
SEKMELER = ["Ozkan_Portfoy", "Derya_Portfoy", "TUFE"]

# TR saati
TR_TZ = timezone(timedelta(hours=3))

# Tip normalizasyon - gecerli tipler
GECERLI_TIPLER = {
    "hisse", "fon", "altinfonu", "yurtdisifonu",
    "emeklilik", "altin", "alacak", "nakit", "kripto",
}

# yil basi fiyatlari icin ayri dosya - korunmali
YILBASI_FILE = REPO_ROOT / "yilbasi_fiyatlari.json"


# =====================================================================
# YARDIMCI FONKSIYONLAR
# =====================================================================

def log(msg, level="INFO"):
    """Standart log formati."""
    ts = datetime.now(TR_TZ).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def normalize_tip(tip_str):
    """
    Tip kolonunu normalize et:
    - Turkce karakter -> Latin
    - Bosluk -> kaldir
    - Lowercase
    """
    if not tip_str:
        return ""
    s = str(tip_str).strip()
    cevir = {
        "ı": "i", "İ": "I", "ş": "s", "Ş": "S",
        "ç": "c", "Ç": "C", "ğ": "g", "Ğ": "G",
        "ü": "u", "Ü": "U", "ö": "o", "Ö": "O",
    }
    for tr, lat in cevir.items():
        s = s.replace(tr, lat)
    s = s.replace(" ", "").lower()
    return s


def parse_sayi(deger):
    """
    Sheets'ten gelen sayiyi parse et.
    Hem virgul hem nokta ondalik tanir.
    Bosluksa None doner.
    """
    if deger is None or deger == "":
        return None
    try:
        s = str(deger).strip()
        if not s:
            return None
        # Once virgul, sonra nokta - turkce locale
        # 37,86 -> 37.86 (turkce ondalik)
        # 1.234,56 -> 1234.56 (turkce binlik nokta + ondalik virgul)
        # 1,234.56 -> 1234.56 (ingilizce binlik virgul + ondalik nokta)

        # Eger hem virgul hem nokta varsa: son karakter ondaliktir
        if "," in s and "." in s:
            son_virgul = s.rfind(",")
            son_nokta = s.rfind(".")
            if son_virgul > son_nokta:
                # Turkce: 1.234,56
                s = s.replace(".", "").replace(",", ".")
            else:
                # Ingilizce: 1,234.56
                s = s.replace(",", "")
        elif "," in s:
            # Sadece virgul: ondalik kabul et (37,86)
            s = s.replace(",", ".")
        # Sadece nokta varsa zaten dogru

        return float(s)
    except (ValueError, TypeError):
        return None


def temiz_kod(kod):
    """Kod kolonundan boslugu kaldir, buyuk harfe cevir (Sheets'te '24 ayar' -> '24AYAR')."""
    if not kod:
        return ""
    return str(kod).strip().replace(" ", "").upper()


def safe_get(dic, *keys, default=None):
    """Ic ice dict'lerden guvenli okuma."""
    cur = dic
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


# =====================================================================
# GOOGLE SHEETS BAGLANTISI
# =====================================================================

def sheets_baglan():
    """Service account ile Sheets'e baglan, gspread client dondur."""
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    sheets_id = os.environ.get("SHEETS_ID")

    if not creds_json:
        log("HATA: GOOGLE_SHEETS_CREDENTIALS env degiskeni bulunamadi.", "ERROR")
        sys.exit(1)
    if not sheets_id:
        log("HATA: SHEETS_ID env degiskeni bulunamadi.", "ERROR")
        sys.exit(1)

    try:
        creds_dict = json.loads(creds_json)
    except json.JSONDecodeError as e:
        log(f"HATA: GOOGLE_SHEETS_CREDENTIALS parse edilemedi: {e}", "ERROR")
        sys.exit(1)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)

    try:
        spreadsheet = client.open_by_key(sheets_id)
    except Exception as e:
        log(f"HATA: Sheets dosyasi acilamadi (ID: {sheets_id[:20]}...): {e}", "ERROR")
        sys.exit(1)

    return spreadsheet


def sekme_oku(spreadsheet, sekme_adi):
    """
    Belirli bir sekmeyi oku.
    SADECE CLAUDE.md'de izinli sekmeler okunur (guvenlik).
    """
    if sekme_adi not in SEKMELER:
        log(f"HATA: Yetkisiz sekme istegi: {sekme_adi}", "ERROR")
        return None

    try:
        sheet = spreadsheet.worksheet(sekme_adi)
        data = sheet.get_all_values()
        if not data:
            log(f"UYARI: {sekme_adi} sekmesi bos.", "WARN")
            return []
        # Ilk satir baslik
        headers = data[0]
        rows = []
        for row in data[1:]:
            if not any(cell.strip() for cell in row):
                continue  # bos satir
            row_dict = {}
            for i, h in enumerate(headers):
                row_dict[h.strip()] = row[i] if i < len(row) else ""
            rows.append(row_dict)
        return rows
    except gspread.exceptions.WorksheetNotFound:
        log(f"UYARI: {sekme_adi} sekmesi bulunamadi.", "WARN")
        return []
    except Exception as e:
        log(f"HATA: {sekme_adi} okunurken: {e}", "ERROR")
        return []


def portfoy_oku(spreadsheet, sekme_adi):
    """
    Bir portfoy sekmesini parse edilmis halde dondur.
    Cikti: list of dict {tip, tip_norm, kod, adet, maliyet}
    """
    rows = sekme_oku(spreadsheet, sekme_adi)
    if rows is None:
        return []

    parsed = []
    for r in rows:
        tip_raw = r.get("Tip", "").strip()
        kod_raw = r.get("Kod", "").strip()
        adet_raw = r.get("Adet", "")
        maliyet_raw = r.get("Maliyet", "")

        if not tip_raw or not kod_raw:
            continue

        tip_norm = normalize_tip(tip_raw)
        if tip_norm not in GECERLI_TIPLER:
            log(f"UYARI: Bilinmeyen tip '{tip_raw}' (sekme: {sekme_adi}, kod: {kod_raw})", "WARN")
            continue

        adet = parse_sayi(adet_raw)
        maliyet = parse_sayi(maliyet_raw)

        if adet is None:
            log(f"UYARI: Adet okunamadi (tip: {tip_raw}, kod: {kod_raw}, deger: '{adet_raw}')", "WARN")
            continue

        parsed.append({
            "tip_orjinal": tip_raw,
            "tip": tip_norm,
            "kod": temiz_kod(kod_raw),
            "kod_orjinal": kod_raw,
            "adet": adet,
            "maliyet": maliyet,
        })

    return parsed


def tufe_oku(spreadsheet):
    """
    TUFE sekmesini oku.
    Cikti: list of dict {ay, gerceklesen, beklenti}
    """
    rows = sekme_oku(spreadsheet, "TUFE")
    if not rows:
        return []

    parsed = []
    for r in rows:
        ay = r.get("Ay", "").strip()
        ger = parse_sayi(r.get("Yillik_Gerceklesen", ""))
        bek = parse_sayi(r.get("Yillik_Beklenti_12Ay", ""))
        if not ay:
            continue
        parsed.append({"ay": ay, "gerceklesen": ger, "beklenti": bek})
    return parsed


# =====================================================================
# FIYAT KAYNAKLARI
# =====================================================================

def yfinance_fiyat(sembol, retries=3):
    """
    Yahoo Finance'den son 5 gunluk veriyi al, son 2 gunu dondur.
    Cikti: {"guncel": x, "onceki": y} veya None
    """
    for attempt in range(retries):
        try:
            ticker = yf.Ticker(sembol)
            hist = ticker.history(period="5d")
            if hist.empty or len(hist) < 1:
                log(f"yfinance bos: {sembol}", "WARN")
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                return None
            kapanis = hist["Close"].dropna().tolist()
            if not kapanis:
                return None
            guncel = float(kapanis[-1])
            onceki = float(kapanis[-2]) if len(kapanis) >= 2 else guncel
            return {"guncel": guncel, "onceki": onceki}
        except Exception as e:
            log(f"yfinance hata ({sembol}, attempt {attempt+1}): {e}", "WARN")
            if attempt < retries - 1:
                time.sleep(2)
    return None


def kur_cek():
    """USDTRY ve EURTRY kurlarini cek."""
    sonuc = {}
    for sembol, anahtar in [("USDTRY=X", "usd_try"), ("EURTRY=X", "eur_try")]:
        veri = yfinance_fiyat(sembol)
        if veri:
            sonuc[anahtar] = veri
        else:
            log(f"HATA: {anahtar} kuru cekilemedi.", "ERROR")
            sonuc[anahtar] = None
    return sonuc


def gram_altin_cek(usd_try_guncel, usd_try_onceki):
    """
    Gram altin TL fiyati cek.
    Yontem: GC=F (altin futures, USD/oz) * USDTRY / 31.1035 (oz->gram)
    """
    if not usd_try_guncel:
        return None
    altin_oz = yfinance_fiyat("GC=F")
    if not altin_oz:
        return None
    OZ_TO_GRAM = 31.1035
    guncel = (altin_oz["guncel"] * usd_try_guncel) / OZ_TO_GRAM
    onceki = (altin_oz["onceki"] * usd_try_onceki) / OZ_TO_GRAM
    return {"guncel": guncel, "onceki": onceki}


def bist_hisse_cek(kod):
    """BIST hisse fiyati: yfinance KOD.IS"""
    return yfinance_fiyat(f"{kod}.IS")


def btc_tl_cek(usd_try_guncel, usd_try_onceki):
    """Bitcoin TL fiyati: BTC-USD * USDTRY"""
    if not usd_try_guncel:
        return None
    btc_usd = yfinance_fiyat("BTC-USD")
    if not btc_usd:
        return None
    return {
        "guncel": btc_usd["guncel"] * usd_try_guncel,
        "onceki": btc_usd["onceki"] * usd_try_onceki,
    }


def tefas_fiyat_toplu(kodlar):
    """
    Tum TEFAS kodlarini toplu cek.
    tefas-crawler'dan son 7 gunluk veri al, son 2 gunu kaydet.
    Cikti: {"KOD": {"guncel": x, "onceki": y}}
    """
    if not kodlar:
        return {}
    if TefasCrawler is None:
        log("TefasCrawler import edilmedi, fonlar atlanir.", "ERROR")
        return {}

    sonuc = {}
    try:
        crawler = TefasCrawler()
        bugun = datetime.now(TR_TZ).date()
        baslangic = bugun - timedelta(days=10)

        # tefas-crawler tek tek sorgulamaya izin verir
        for kod in kodlar:
            try:
                df = crawler.fetch(start=str(baslangic), end=str(bugun), name=kod)
                if df is None or df.empty:
                    log(f"TEFAS bos: {kod}", "WARN")
                    continue
                df = df.sort_values("date")
                fiyatlar = df["price"].dropna().tolist()
                if not fiyatlar:
                    continue
                guncel = float(fiyatlar[-1])
                onceki = float(fiyatlar[-2]) if len(fiyatlar) >= 2 else guncel
                sonuc[kod] = {"guncel": guncel, "onceki": onceki}
                time.sleep(0.5)  # nezaket
            except Exception as e:
                log(f"TEFAS hata ({kod}): {e}", "WARN")
                continue
    except Exception as e:
        log(f"TEFAS toplu hata: {e}", "ERROR")
    return sonuc


# =====================================================================
# YIL BASI FIYATLARI YONETIMI
# =====================================================================

def yilbasi_oku():
    """yilbasi_fiyatlari.json varsa oku, yoksa bos dondur."""
    if not YILBASI_FILE.exists():
        return {}
    try:
        with open(YILBASI_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"yilbasi_fiyatlari.json okunamadi: {e}", "WARN")
        return {}


def yilbasi_yaz(data):
    """yilbasi_fiyatlari.json yaz."""
    with open(YILBASI_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def yilbasi_guncelle(yeni_kodlar, mevcut, fiyatlar):
    """
    Yil basi fiyatlarini koru.
    Yeni kod gorulduyse simdiki fiyatini yil basi olarak kaydet (fallback).
    Bu sadece dosyada yoksa eklenir, varolan korunur.
    """
    yil = datetime.now(TR_TZ).year
    yil_str = str(yil)
    if yil_str not in mevcut:
        mevcut[yil_str] = {}

    for kod in yeni_kodlar:
        if kod in mevcut[yil_str]:
            continue  # zaten var, dokunma
        f = fiyatlar.get(kod)
        if f and f.get("guncel") is not None:
            mevcut[yil_str][kod] = f["guncel"]
            log(f"Yil basi fiyati kaydedildi (fallback): {kod} = {f['guncel']:.4f}")
    return mevcut


# =====================================================================
# JSON URETIMI
# =====================================================================

def prices_json_olustur(hisseler, tefas_fiyatlari, kripto, gram_altin, kurlar, yilbasi):
    """prices.json yapisini olustur."""
    yil_str = str(datetime.now(TR_TZ).year)
    yb = yilbasi.get(yil_str, {})

    def _fiyat_with_yilbasi(kod, fiyat_dict):
        if not fiyat_dict:
            return {"guncel": None, "onceki": None, "yilbasi": yb.get(kod)}
        return {
            "guncel": fiyat_dict["guncel"],
            "onceki": fiyat_dict["onceki"],
            "yilbasi": yb.get(kod),
        }

    return {
        "son_guncelleme": datetime.now(TR_TZ).isoformat(timespec="seconds"),
        "kaynak": "yfinance + tefas-crawler",
        "kurlar": {
            "usd_try": kurlar.get("usd_try"),
            "eur_try": kurlar.get("eur_try"),
        },
        "gram_altin_tl": gram_altin,
        "hisseler": {k: _fiyat_with_yilbasi(k, v) for k, v in hisseler.items()},
        "fonlar_ve_emeklilik": {k: _fiyat_with_yilbasi(k, v) for k, v in tefas_fiyatlari.items()},
        "kripto": {k: _fiyat_with_yilbasi(k, v) for k, v in kripto.items()},
    }


def portfoy_json_olustur(ozkan_satirlar, derya_satirlar, prices, tufe_data):
    """
    portfoy.json yapisini olustur.
    Her satir icin guncel_tl, onceki_tl, gunluk_kazanc_tl, gunluk_yuzde hesapla.
    """
    def _hesapla(satir, prices, kurlar):
        """Bir satir icin TL degerleri hesapla."""
        tip = satir["tip"]
        kod = satir["kod"]
        adet = satir["adet"]

        guncel_birim = None
        onceki_birim = None

        if tip == "hisse":
            f = safe_get(prices, "hisseler", kod)
            if f:
                guncel_birim = f.get("guncel")
                onceki_birim = f.get("onceki")
        elif tip in ("fon", "altinfonu", "yurtdisifonu", "emeklilik"):
            f = safe_get(prices, "fonlar_ve_emeklilik", kod)
            if f:
                guncel_birim = f.get("guncel")
                onceki_birim = f.get("onceki")
        elif tip == "kripto":
            f = safe_get(prices, "kripto", kod)
            if f:
                guncel_birim = f.get("guncel")
                onceki_birim = f.get("onceki")
        elif tip == "altin":
            ga = safe_get(prices, "gram_altin_tl")
            if ga:
                guncel_birim = ga.get("guncel")
                onceki_birim = ga.get("onceki")
        elif tip == "nakit":
            # Kod: TL/USD/EUR (veya TL-XYZ gibi onek)
            kod_uc = kod[:3].upper() if kod else ""
            if kod_uc == "TL" or kod.upper().startswith("TL"):
                guncel_birim = 1.0
                onceki_birim = 1.0
            elif kod_uc == "USD" or kod.upper().startswith("USD"):
                u = safe_get(kurlar, "usd_try")
                if u:
                    guncel_birim = u.get("guncel")
                    onceki_birim = u.get("onceki")
            elif kod_uc == "EUR" or kod.upper().startswith("EUR"):
                e = safe_get(kurlar, "eur_try")
                if e:
                    guncel_birim = e.get("guncel")
                    onceki_birim = e.get("onceki")
        elif tip == "alacak":
            # Adet TL tutar olarak girilir, sabit
            guncel_birim = 1.0
            onceki_birim = 1.0

        if guncel_birim is None:
            return {
                "guncel_tl": None,
                "onceki_tl": None,
                "gunluk_kazanc_tl": None,
                "gunluk_yuzde": None,
                "fiyat_eksik": True,
            }

        guncel_tl = adet * guncel_birim
        onceki_tl = adet * onceki_birim if onceki_birim is not None else guncel_tl
        gunluk_kazanc = guncel_tl - onceki_tl
        gunluk_yuzde = (gunluk_kazanc / onceki_tl * 100) if onceki_tl else 0.0

        return {
            "guncel_tl": guncel_tl,
            "onceki_tl": onceki_tl,
            "gunluk_kazanc_tl": gunluk_kazanc,
            "gunluk_yuzde": gunluk_yuzde,
            "fiyat_eksik": False,
        }

    kurlar = prices.get("kurlar", {})

    def _kisi_olustur(satirlar):
        olusan = []
        for s in satirlar:
            hesap = _hesapla(s, prices, kurlar)
            olusan.append({**s, **hesap})
        return olusan

    return {
        "olusturma_tarihi": datetime.now(TR_TZ).isoformat(timespec="seconds"),
        "milat": "2026-05-21",
        "portfoyler": {
            "ozkan": _kisi_olustur(ozkan_satirlar),
            "derya": _kisi_olustur(derya_satirlar),
        },
        "tufe": tufe_data,
    }


def gecmis_kaydet(portfoy_data):
    """
    Kapanis calistirmasi ise gecmis.json'a snapshot ekle.
    Snapshot: gunluk kategori bazli TL toplamlari.
    Ayni gunde zaten kayit varsa atla.
    """
    bugun = datetime.now(TR_TZ).strftime("%Y-%m-%d")

    # Mevcut gecmis dosyasini oku
    if GECMIS_FILE.exists():
        try:
            with open(GECMIS_FILE, "r", encoding="utf-8") as f:
                gecmis = json.load(f)
        except Exception:
            gecmis = {"kayit_baslangic": "2026-05-21", "gunler": {}}
    else:
        gecmis = {"kayit_baslangic": "2026-05-21", "gunler": {}}

    # Bugun zaten varsa atla
    if bugun in gecmis.get("gunler", {}):
        log(f"Gecmis: {bugun} icin zaten kayit var, atlaniyor.")
        return False

    # Milat kontrolu
    if bugun < gecmis["kayit_baslangic"]:
        log(f"Gecmis: bugun ({bugun}) milattan ({gecmis['kayit_baslangic']}) once, atlaniyor.")
        return False

    # Kategori toplamlari hesapla
    def _kisi_toplam(satirlar):
        kategoriler = {}
        toplam = 0.0
        for s in satirlar:
            tip = s.get("tip", "bilinmeyen")
            tl = s.get("guncel_tl")
            if tl is None:
                continue
            kategoriler[tip] = kategoriler.get(tip, 0.0) + tl
            toplam += tl
        return {"kategoriler": kategoriler, "toplam": toplam}

    ozkan = _kisi_toplam(portfoy_data["portfoyler"]["ozkan"])
    derya = _kisi_toplam(portfoy_data["portfoyler"]["derya"])
    genel_toplam = ozkan["toplam"] + derya["toplam"]

    gecmis["gunler"][bugun] = {
        "ozkan": ozkan,
        "derya": derya,
        "genel_toplam": genel_toplam,
    }

    # Tarih sirasiyla kaydet
    gecmis["gunler"] = dict(sorted(gecmis["gunler"].items()))

    with open(GECMIS_FILE, "w", encoding="utf-8") as f:
        json.dump(gecmis, f, ensure_ascii=False, indent=2)

    log(f"Gecmis: {bugun} icin snapshot kaydedildi (toplam: {genel_toplam:,.0f} TL)")
    return True


# =====================================================================
# ANA AKIS
# =====================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kapanis", action="store_true", help="Kapanis calistirmasi (gecmis.json'a kayit yapar)")
    args = parser.parse_args()

    log("=" * 60)
    log("Portfoy fiyat guncelleme baslatildi")
    log(f"Mod: {'KAPANIS' if args.kapanis else 'INTRADAY'}")
    log("=" * 60)

    # 1. Sheets'e baglan
    log("[1/6] Google Sheets'e baglaniliyor...")
    spreadsheet = sheets_baglan()
    log("Sheets baglandi.")

    # 2. Sekmeleri oku
    log("[2/6] Portfoy sekmeleri okunuyor...")
    ozkan = portfoy_oku(spreadsheet, "Ozkan_Portfoy")
    derya = portfoy_oku(spreadsheet, "Derya_Portfoy")
    tufe = tufe_oku(spreadsheet)
    log(f"  Ozkan: {len(ozkan)} satir")
    log(f"  Derya: {len(derya)} satir")
    log(f"  TUFE: {len(tufe)} satir")

    if not ozkan and not derya:
        log("HATA: Hicbir portfoy satiri okunamadi. Cikiliyor.", "ERROR")
        sys.exit(1)

    # 3. Benzersiz kodlari topla
    tum_satirlar = ozkan + derya
    hisse_kodlari = sorted({s["kod"] for s in tum_satirlar if s["tip"] == "hisse"})
    tefas_kodlari = sorted({
        s["kod"] for s in tum_satirlar
        if s["tip"] in ("fon", "altinfonu", "yurtdisifonu", "emeklilik")
    })
    kripto_kodlari = sorted({s["kod"] for s in tum_satirlar if s["tip"] == "kripto"})
    altin_var = any(s["tip"] == "altin" for s in tum_satirlar)
    nakit_var = any(s["tip"] == "nakit" for s in tum_satirlar)

    log(f"  Benzersiz hisse: {len(hisse_kodlari)} adet -> {hisse_kodlari}")
    log(f"  Benzersiz TEFAS: {len(tefas_kodlari)} adet -> {tefas_kodlari}")
    log(f"  Benzersiz kripto: {len(kripto_kodlari)} adet -> {kripto_kodlari}")
    log(f"  Altin: {altin_var} | Nakit: {nakit_var}")

    # 4. Fiyatlari cek
    log("[3/6] Kurlar cekiliyor...")
    kurlar = kur_cek()
    usd_g = safe_get(kurlar, "usd_try", "guncel")
    usd_o = safe_get(kurlar, "usd_try", "onceki")
    log(f"  USDTRY: guncel={usd_g}, onceki={usd_o}")

    log("[4/6] Hisseler cekiliyor...")
    hisseler = {}
    for kod in hisse_kodlari:
        f = bist_hisse_cek(kod)
        if f:
            hisseler[kod] = f
            log(f"  {kod}: {f['guncel']:.2f}")
        else:
            log(f"  {kod}: BASARISIZ", "WARN")
        time.sleep(0.5)

    log("[5/6] TEFAS fonlari + emeklilik + kripto + altin cekiliyor...")
    tefas_fiyatlari = tefas_fiyat_toplu(tefas_kodlari)
    for k, v in tefas_fiyatlari.items():
        log(f"  {k}: {v['guncel']:.4f}")

    kripto = {}
    if kripto_kodlari:
        if "BTC" in kripto_kodlari and usd_g:
            btc = btc_tl_cek(usd_g, usd_o)
            if btc:
                kripto["BTC"] = btc
                log(f"  BTC: {btc['guncel']:,.0f} TL")

    gram_altin = None
    if altin_var or True:  # her zaman cek - benchmark icin de lazim
        if usd_g:
            gram_altin = gram_altin_cek(usd_g, usd_o)
            if gram_altin:
                log(f"  Gram altin: {gram_altin['guncel']:,.2f} TL/gr")

    # 5. Yil basi fiyatlarini koru/guncelle
    log("[6/6] JSON dosyalari yaziliyor...")
    yilbasi = yilbasi_oku()

    # Tum kodlari yil basi takibine al
    tum_kodlar = (
        list(hisseler.keys())
        + list(tefas_fiyatlari.keys())
        + list(kripto.keys())
    )
    fiyat_dict_birlesik = {**hisseler, **tefas_fiyatlari, **kripto}
    yilbasi = yilbasi_guncelle(tum_kodlar, yilbasi, fiyat_dict_birlesik)
    yilbasi_yaz(yilbasi)

    # 6. JSON'lari yaz
    prices = prices_json_olustur(hisseler, tefas_fiyatlari, kripto, gram_altin, kurlar, yilbasi)
    with open(PRICES_FILE, "w", encoding="utf-8") as f:
        json.dump(prices, f, ensure_ascii=False, indent=2)
    log(f"  prices.json yazildi.")

    portfoy = portfoy_json_olustur(ozkan, derya, prices, tufe)
    with open(PORTFOY_FILE, "w", encoding="utf-8") as f:
        json.dump(portfoy, f, ensure_ascii=False, indent=2)
    log(f"  portfoy.json yazildi.")

    # Toplamlari log'la
    o_toplam = sum(s.get("guncel_tl") or 0 for s in portfoy["portfoyler"]["ozkan"])
    d_toplam = sum(s.get("guncel_tl") or 0 for s in portfoy["portfoyler"]["derya"])
    log(f"  Ozkan toplam: {o_toplam:,.0f} TL")
    log(f"  Derya toplam: {d_toplam:,.0f} TL")
    log(f"  Genel toplam: {o_toplam + d_toplam:,.0f} TL")

    # 7. Kapanis ise gecmis.json'a kayit
    if args.kapanis:
        log("[+] Kapanis modu: gecmis.json guncelleniyor...")
        gecmis_kaydet(portfoy)

    log("=" * 60)
    log("Tamamlandi.")
    log("=" * 60)


if __name__ == "__main__":
    main()
