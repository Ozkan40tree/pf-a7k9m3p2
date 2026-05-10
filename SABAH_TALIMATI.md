# SABAH TALİMATI - Oturum 2 Devamı

**Hazırlayan:** Claude (gece)
**Yapacak:** Özkan (sabah)
**Tahmini süre:** 30-45 dakika

Bu dosya, hazır dosyaları repo'ya yerleştirmen ve ilk testi yapman için
adım adım talimattır. Her adımı sırayla yap, sorun olursa bana yaz.

---

## HAZIR DOSYALAR

Sabah indireceğin dosyalar:

```
portfoy/
├── requirements.txt
├── .gitignore
├── scripts/
│   ├── fiyat_guncelle.py        (ana fiyat scripti)
│   └── benchmark_fiyat.py        (benchmark scripti)
└── .github/
    └── workflows/
        ├── portfoy-guncelle.yml  (4 zamanlı cron)
        └── benchmark-guncelle.yml (günlük benchmark cron)
```

---

## ADIM 1 — Dosyaları repo klasörüne taşı

Bu dosyaları sana ZIP olarak vereceğim. İndirilenler klasörüne iner.

Terminal'i aç, şu komutları **SIRAYLA** yapıştır:

### 1.1 Repo klasörüne git ve son durumu çek

```bash
cd ~/Documents/pf-a7k9m3p2
git pull origin main
```

Beklenen çıktı: `Already up to date.` veya yeni commitler indi.

### 1.2 ZIP'i aç ve içeriği repo klasörüne kopyala

**Önemli:** macOS'te `cp -R` komutu varsayılan olarak `.gitignore` ve
`.github` gibi gizli dosyaları kopyalar. Aşağıdaki komutlar bunu
sağlar (özellikle `cp -R` kullanıyoruz).

```bash
cd ~/Downloads
unzip -o portfoy-oturum2.zip -d portfoy-oturum2/
cp -R portfoy-oturum2/portfoy/. ~/Documents/pf-a7k9m3p2/
ls -la ~/Documents/pf-a7k9m3p2/
```

Beklenen çıktı: Repo klasöründe yeni dosyalar görmen lazım:
- `requirements.txt`
- `scripts/` klasörü (içinde 2 .py dosyası)
- `.github/` klasörü (içinde workflows alt klasörü, içinde 2 .yml dosyası)
- `.gitignore`
- `SABAH_TALIMATI.md`

Önceden olan: `CLAUDE.md`, `index.html`, `prices.json`, `portfoy.json`, `robots.txt`

### 1.3 .github klasörünün gerçekten geldiğini doğrula

```bash
ls -la ~/Documents/pf-a7k9m3p2/.github/workflows/
```

Beklenen çıktı: `portfoy-guncelle.yml` ve `benchmark-guncelle.yml` görünmeli.
Eğer "No such file or directory" derse, ZIP düzgün açılmamış demektir,
bana yaz.

---

## ADIM 2 — Lock kontrolü ve commit

### 2.1 Repo klasörüne dön ve lock kontrol et

```bash
cd ~/Documents/pf-a7k9m3p2
rm -f .git/index.lock .git/HEAD.lock
git status
```

Beklenen çıktı: Yeni eklenen dosyalar **"Untracked files:"** altında listelenir.

### 2.2 Hassas dosya kontrolü (KRİTİK!)

Şu komutu çalıştır — eğer JSON anahtarı varsa görürüz:

```bash
ls ~/Documents/pf-a7k9m3p2/*.json | grep -i "portfoy-dashboard\|service\|credential" || echo "TEMIZ - hassas JSON yok"
```

**Beklenen çıktı:** `TEMIZ - hassas JSON yok`

Eğer bir hassas dosya görürsen DUR ve bana yaz, commit etme.

### 2.3 Tüm yeni dosyaları commit et

```bash
git add requirements.txt .gitignore scripts/ .github/
git commit -m "Oturum 2: Python scripts ve GitHub Actions workflows"
git push origin main
```

Beklenen çıktı son satır: `main -> main` ✅

---

## ADIM 3 — GitHub Actions'tan ilk testi çalıştır

Şimdi gerçek test! Tarayıcıda şu adresi aç:

```
https://github.com/Ozkan40tree/pf-a7k9m3p2/actions
```

### 3.1 Sol tarafta workflow'ları gör

Sol menüde 2 workflow görmen lazım:
- **Portfoy Fiyat Guncelleme**
- **Benchmark Guncelleme**

### 3.2 Önce ana workflow'u test et

**"Portfoy Fiyat Guncelleme"** üstüne tıkla.

Sağ üstte **"Run workflow"** mavi butonu var, ona tıkla.

Açılan dropdown'da:
- Branch: `main` (zaten seçili)
- "Kapanis modu": **`false`** olarak bırak (intraday test ediyoruz)
- Yeşil **"Run workflow"** butonuna bas

### 3.3 Çalışmasını izle

Sayfayı yenile (F5). Üstte yeni bir satır görürsün:
- Sarı/turuncu nokta = çalışıyor
- Yeşil tik = başarılı ✅
- Kırmızı X = hata ❌

Süre: 1-3 dakika.

### 3.4 Çıktıyı bana gönder

İşlem bitince üstündeki başlığa tıkla. Sonra **"guncelle"** job'una tıkla. Açılan sayfada **"Fiyat guncelleme calistir"** satırını genişlet.

**Tüm çıktıyı kopyala ve sohbete yapıştır.**

---

## ADIM 4 — Eğer ilk test başarılı olursa

İki durum olabilir:

### Durum A — YEŞİL TİK (her şey çalıştı)
Süper! O zaman:

1. Repoya gidip `prices.json` ve `portfoy.json` dosyalarına bak — yeni güncelleme tarihi olmalı.
2. Sırada **benchmark gecmişini ilk kez çekmek** var (5 yıllık veri):
   - Actions sayfasında **"Benchmark Guncelleme"** workflow'u seç
   - **"Run workflow"** → "gecmis" seçeneği **`true`** yap → çalıştır
   - Bu daha uzun sürer (5-10 dakika), 5 yıllık veri çekiyor

### Durum B — KIRMIZI X (hata var)
Endişelenme, ilk testte hata çıkması NORMAL. Çıktıyı yapıştır, birlikte çözeriz.

En olası hatalar:
- **TEFAS kodu tanınmadı** (örn. `ZBJ` yerine farklı kod) → düzeltiriz
- **yfinance hisse kodu** (örn. `ALVES.IS` listede yok) → düzeltiriz
- **Sheets API izni** → service account adresini Sheets'e eklemeyi unuttuysak

Hata mesajı netse, çözüm de hızlı olur.

---

## ÖNEMLİ NOTLAR

### Cowork görevlerine NE YAPACAĞIZ?

**ŞİMDİLİK HİÇBİR ŞEY.** Cowork görevleri çalışmaya devam etsin. GitHub Actions ile birkaç gün paralel çalıştıralım. Aynı dosyaya iki yerden push olabilir, ama:

- Çakışma olursa bir taraf hata verir, biz log'larda görürüz
- Birkaç gün sonra Cowork stabil değil, GitHub Actions stabil ise → Cowork görevlerini DURDUR (silme!)
- 1-2 hafta sonra problemsizse Cowork'ü sil

Bu yaklaşım "tekrar başa dönmek istemiyorum" şartına uygun: GitHub Actions çalışmazsa Cowork yedek.

### Service account Sheets'e eklendi mi kontrol et

Eğer "Cannot read worksheet" hatası alırsan:
1. Google Sheets'i aç
2. Sağ üst → Paylaş
3. Şu adresin orada olduğunu kontrol et: `sheets-reader@portfoy-dashboard-ozkan.iam.gserviceaccount.com`
4. Yetki: Görüntüleyen olmalı

### Test sırasında Mac'i kapatabilir misin?

EVET. Artık GitHub Actions cloud'da çalışıyor. Mac kapalı olsun da olmasın da fark etmez.

---

## SONRAKİ OTURUM (Pazar/sonra)

Bugün test başarılı olursa:
- Cowork görevlerini durdurma (silme)
- gecmis.json'a günlük snapshot atılmaya başlaması (kapanış görevi 18:35'te)
- Frontend yeniden tasarımı (Oturum 3-4)

**Bugünkü hedef:** GitHub Actions başarılı şekilde Sheets okusun, prices.json/portfoy.json üretsin.

İyi sabahlar! 🌅
