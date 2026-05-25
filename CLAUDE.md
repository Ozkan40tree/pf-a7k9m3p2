# CLAUDE.md — Portföy Dashboard Kuralları

Bu dosya, bu repo üzerinde çalışan her Claude oturumu için kalıcı kurallar
dosyasıdır. Yeni bir sohbet açıldığında Claude bu dosyayı okur ve buradaki
kurallara uyar.

---

## 0. ÇALIŞMA KURALLARI (asla esnetilmez)

1. **Halüsinasyon yasak.** Veriyi tahmin etme, uydurma. Bilmiyorsan
   "bilmiyorum" de, atla. Atlanan kod/veri varsa kullanıcıya raporla.
2. **Adım adım, yavaş yavaş.** Bir adımı bitirmeden diğerine geçme.
3. **Emin olmadan ilerleme.** Her adımda kullanıcı onayı bekle.
4. **Hata varsa açık bildir.** "Şu çalışmadı çünkü şu" diye net yaz.
5. **Talimatlar net olmalı.** Kullanıcı teknik kişi değil; kopyala-yapıştır
   ve tıklama seviyesinde rahat. Adımları ona göre yaz.
6. **Veri kaynağı tek:** Google Sheets. Kullanıcı sadece Sheets'e veri
   girer. Diğer her şey otomatik gelir. Bu kural değişmez.
7. **Önden risk düşün.** Yapmadan önce nelerin ters gidebileceğini
   kullanıcıya söyle. Yarım yolda yöntem değiştirmek yasak.

---

## 1. SİSTEM HARİTASI

- **Site:** GitHub Pages üzerinde yayınlanır, basit şifre koruması var.
- **Lokal repo:** `~/Documents/pf-a7k9m3p2/` (kullanıcının makinesinde)
- **Branch:** main
- **Veri akışı:** Google Sheets → Python scripti (GitHub Actions) →
  JSON dosyaları → GitHub Pages frontend.
- **Cron motoru:** GitHub Actions (cloud). Cowork'ten geçiş yapıldı,
  geçiş gerekçesi: FUSE mount lock bug'ı.

> **Not:** Repo URL'leri, Sheets ID, şifreler, token'lar bu dosyada
> tutulmaz. Bunlar lokal `.gitignore` altındaki bir notes dosyasında ve
> GitHub Secrets'tadır.

---

## 2. SHEETS ŞEMASI

**Sekmeler:** `Ozkan_Portfoy`, `Derya_Portfoy`

**Sütunlar (her sekme aynı):**

| Sütun | Anlam |
|---|---|
| A — Tip | Varlık kategorisi (sabit liste, aşağıda) |
| B — Kod | Sembol veya etiket |
| C — Adet | Adet, gram veya tutar (Tip'e göre) |
| D — Maliyet | Birim maliyet (bazı tiplerde boş kalır) |

**Geçerli Tip değerleri:**

```
Hisse, Fon, AltinFonu, YurtdisiFonu, Emeklilik, Altin, Alacak, Nakit, Kripto
```

### 2.1 Tip normalizasyon kuralı

Tip kolonu okunurken şu işlemler uygulanır:

- Türkçe karakterler Latin'e dönüştürülür: `ı→i, ş→s, ç→c, ğ→g, ü→u, ö→o, İ→I, Ş→S, Ç→C, Ğ→G, Ü→U, Ö→O`
- Tüm boşluklar atılır.
- Büyük/küçük harf farkı önemsiz (lowercase ile karşılaştırılır).

Yani şunlar hepsi aynı kabul edilir:

- `AltınFonu` = `AltinFonu` = `altinfonu` = `Altın Fonu`
- `YurtdışıFonu` = `YurtdisiFonu` = `yurtdisi fonu`
- `Altın` = `Altin` = `altin`

**Kod kolonu** için sadece boşluk atma uygulanır:
`24 ayar` = `24ayar`. Büyük/küçük harf önemsiz değildir
(BIST/TEFAS kodları her zaman BÜYÜK harf).

**Ekran gösteriminde** Türkçe karakterli güzel hal kullanılır:
`Altın Fonu`, `Yurtdışı Fonu`, `Altın`.

### 2.2 Tip'e göre kurallar

| Tip | Kod | Adet anlamı | Maliyet | Fiyat kaynağı |
|---|---|---|---|---|
| Hisse | BIST kodu | adet | zorunlu | yfinance (`.IS` suffix) |
| Fon | TEFAS kodu | adet | zorunlu | tefas-crawler |
| AltinFonu | TEFAS kodu | adet | zorunlu | tefas-crawler |
| YurtdisiFonu | TEFAS kodu | adet | zorunlu | tefas-crawler |
| Emeklilik | TEFAS BES kodu | adet | boş | tefas-crawler |
| Altin | `24ayar` | gram | boş | yfinance (`GC=F` × USDTRY ÷ 31.1035) |
| Alacak | serbest etiket | TL tutar | boş | sabit (TL) |
| Nakit | `TL`/`USD`/`EUR` | birim sayısı | boş | yfinance kuru |
| Kripto | `BTC` vb. | adet | TL maliyet | Yahoo Finance × USDTRY |

**Maliyet boşsa:** kazanç yüzdesi hesaplanmaz, sadece güncel TL değer ve
zaman içindeki TL değişim gösterilir.

### 2.4 Sayı formatı

Sheets'ten gelen sayılar şu kuralla parse edilir:

- `37,86` → 37.86 (Türkçe ondalık)
- `37.86` → 37.86 (İngilizce ondalık)
- `1.234,56` → 1234.56 (Türkçe binlik + ondalık)
- `1,234.56` → 1234.56 (İngilizce binlik + ondalık)

Yani sen virgül de yazsan nokta da yazsan sistem doğru parse eder.

### 2.5 Sheets sekme güvenliği

Service account (`sheets-reader@portfoy-dashboard-ozkan.iam.gserviceaccount.com`)
tüm dosyaya erişim hakkına sahip (Sheets'in paylaşım modeli sekme bazlı değil).

**Ama Python script'leri şu sekmeleri SADECE okur:**
- `Ozkan_Portfoy`
- `Derya_Portfoy`
- `TUFE`

Başka sekmeler (analiz, vs.) script tarafından okunmaz. Bu kural
`scripts/fiyat_guncelle.py` içindeki `SEKMELER` listesi ile
sabitlenmiştir.

### 2.3 Tip-bazlı kategori grupları (dashboard ve benchmark için)

- **Aktif Yatırım:** Hisse + Fon + YurtdisiFonu + AltinFonu + Kripto
- **Hisse+Fon+Yurtdışı:** Hisse + Fon + YurtdisiFonu
- **Pasif/Uzun Vade:** Emeklilik + Alacak
- **Genel Toplam:** tüm tipler dahil

---

## 3. JSON DOSYALARI

Repodaki canlı dosyalar:

- `prices.json` — En son fiyatlar. Her güncellemede üzerine yazılır.
- `portfoy.json` — Sheets'in JSON aynası + hesaplanmış TL değerler
  (her satır için `guncel_tl`, `onceki_tl`, `gunluk_kazanc_tl`,
  `gunluk_yuzde`).
- `gecmis.json` — Günlük kapanış snapshot'ı. Sadece kapanış görevi
  (TR saati 18:35) yazar. **Milat: 21 Mayıs 2026.**
- `benchmark_gecmis.json` — BIST100, S&P500 (TL), Gram Altın, YAE, TÜFE
  serileri. 5 yıl geriye tek seferlik çekilir, sonra her gün son güne
  ekleme yapılır.
- `yilbasi_fiyatlari.json` — Her yıl ilk fiyat çekiminde yılbaşı fiyatı
  olarak kaydedilir, bir daha üzerine yazılmaz. YTD getiri hesabı için.

**Tatil/hafta sonu kuralı:** Kapanış görevi cron olarak Pzt-Cum çalışır.
Tatil günleri için akıllı kontrol: "Bugün tarihte kayıt var mı?" → varsa
atla.

---

## 4. BENCHMARK SETİ

| Benchmark | Amaç | Kaynak (19 Mayıs 2026 itibarıyla) |
|---|---|---|
| BIST100 | Hisse karşılaştırması | `borsapy.Index("XU100")` birincil, yfinance `XU100.IS` yedek |
| **Amerika Hisse (TL)** | Yurtdışı hisse karşılaştırması | `borsapy.Fund("AFA")` birincil, `Fund("ABE")` yedek, yfinance `^GSPC × USDTRY` son çare |
| Gram Altın | Altın varlıkların karşılaştırması | `borsapy.FX("gram-altin")` birincil (TL direkt), yfinance `GC=F × USDTRY ÷ 31.1035` yedek |
| YAE fonu | Faiz / para piyasası karşılaştırması (ZBJ için) | `borsapy.Fund("YAE")` (TEFAS v2 API) |
| TÜFE | Reel getiri (1 ay+ kıyaslamalar) | Google Sheets `TUFE` sekmesi |

**Karşılaştırma türü:** sadece **% getiri** (mutlak değer değil).

**Not (19 Mayıs 2026):** "S&P500 (TL)" → "Amerika Hisse (AFA)" olarak değişti. borsapy doğrudan S&P500 endeksini desteklemediği için Türk yatırımcının S&P500 erişim aracı olan TEFAS S&P500 takipli fonlardan AFA kullanılıyor. Detay: §12.2.

---

## 5. DASHBOARD YAPISI

> **GÜNCEL DURUM (22 Mayıs 2026):** Sidebar **6 tab** içeriyor: Özkan, Derya, Aile, Benchmark, Geçmiş Veriler, Grafik. Aile tabı 22 Mayıs akşamı tamamlandı (commit f57230f). Tab'lar artık `flex-wrap: wrap` ile mobilde iki satıra dönüşüyor.

**Sidebar tabları:**
1. Özkan ✅
2. Derya ✅
3. Aile ✅ (22 Mayıs, §12.10 madde 2 tamamlandı)
4. Benchmark ✅
5. Geçmiş Veriler ✅ (§12.4)
6. Grafik ✅ (§12.4)

### 5.1 Özkan tabı — kart sırası

| # | Kart | İçerik | Gösterim |
|---|---|---|---|
| 1 | Hisse + Fon + Yurtdışı | Hisse + Fon + YurtdisiFonu | TL + bugün/1H/1A/YTD % |
| 2 | Altın Fonu | AltinFonu | TL + bugün/1H/1A/YTD % |
| 3 | Kripto | Kripto | TL + bugün/1H/1A/YTD % |
| 4 | Aktif Yatırım Toplamı | 1+2+3 | TL + dönemsel % |
| 5 | Emeklilik | Emeklilik | sadece TL gelişimi (% yok) |
| 6 | Alacak | Alacak | sadece TL (sabit) |
| 7 | Genel Toplam | hepsi | TL + dönemsel % |

### 5.2 Derya tabı

| # | Kart | İçerik | Gösterim |
|---|---|---|---|
| 1 | Hisse Toplamı | Hisse | TL + dönemsel % |
| 2 | Altın | Altin | TL + dönemsel % |
| 3 | Emeklilik | Emeklilik | sadece TL gelişimi |
| 4 | Genel Toplam | hepsi | TL + dönemsel % |

### 5.3 Genel (Aile) tabı

| # | Kart | İçerik |
|---|---|---|
| 1 | Aile Aktif Yatırım | Özkan(1+2+3) + Derya(Hisse+Altın) |
| 2 | Aile Emeklilik | iki kişi toplamı |
| 3 | Aile Toplam | hepsi |

### 5.4 Ortak elementler (her tabta)

- **Üst banner:** Toplam Aile, Özkan Toplam, Derya Toplam, Günlük Kazanç (TL)
- **Sağ üst:** Göz ikonu (gizlilik modu — 1.000.000 TL'ye normalize)
- **Donut grafik:** kategori dağılımı
- **Çizgi grafik:** portföy değeri zamanla (milat sonrası)
- **Kategori tablosu:** Tip, Tutar, Pay %, Günlük Değişim %

### 5.5 Gösterilmez

- Toplam Maliyet
- Net K/Z
- Varlık Sayısı kutusu
- **Dashboard'da benchmark grafiği yok** (ayrı tabta).

### 5.6 Tema

- Koyu lacivert/teal arka plan
- Turkuaz vurgular
- Dijital dalga arka plan deseni (sağ üst)
- Modern fintech estetiği

---

## 6. BENCHMARK TABI

### 6.1 Üstte iki seçici

**Karşılaştırılacak varlık** (dropdown, 15 öğe):

```
ÖZKAN
  Özkan – Genel Toplam
  Özkan – Aktif Yatırım (Hisse+Fon+Yurtdışı+AltınFonu+Kripto)
  Özkan – Hisse+Fon+Yurtdışı
  Özkan – Hisse
  Özkan – Fon
  Özkan – YurtdışıFon
  Özkan – AltınFonu
  Özkan – Kripto
  Özkan – Emeklilik

DERYA
  Derya – Genel
  Derya – Hisse
  Derya – Altın
  Derya – Emeklilik

AİLE
  Aile – Toplam
  Aile – Aktif Yatırım
```

**Dönem** (buton grubu):

```
1H  /  1A  /  YTD  /  6A  /  1Y  /  3Y  /  5Y  /  Özel tarih aralığı
```

### 6.2 Alttaki içerik

**(a) Çizgi grafik:** Seçilen varlık + 5 benchmark'ın kümülatif %
getirisi. Başlangıç %0, sonra zamanla nasıl ayrıştığı gözükür.
Renkler: portföy turkuaz vurgu, benchmarklar farklı renk tonları.

**(b) Karşılaştırma tablosu** (7 kolon, 7 satır):

| | 1H | 1A | YTD | 6A | 1Y | 3Y | 5Y |
|---|---|---|---|---|---|---|---|
| Seçilen varlık | | | | | | | |
| BIST100 | | | | | | | |
| S&P500 (TL) | | | | | | | |
| Gram Altın | | | | | | | |
| YAE Fonu | | | | | | | |
| TÜFE | | | | | | | |
| **Fark (en iyi vs varlık)** | | | | | | | |

**(c) Bilgi notu (grafik altında):**

```
Portföy verisi 21 Mayıs 2026 itibarıyla kayıtlıdır.
Daha uzun dönemli karşılaştırmalarda benchmark çizgileri tamdır,
portföy çizgisi milat tarihinden itibaren çıkar.
```

---

## 7. OTOMASYON ALTYAPISI

### 7.1 Repo dosya yapısı

```
pf-a7k9m3p2/
├── CLAUDE.md                        Bu dosya
├── index.html                        Frontend
├── prices.json                       Anlık fiyatlar
├── portfoy.json                      Hesaplanmış TL değerler
├── gecmis.json                       Günlük kapanış snapshot'ları
├── benchmark_gecmis.json             Benchmark zaman serileri
├── yilbasi_fiyatlari.json            YTD hesabı için
├── robots.txt
├── requirements.txt                  Python kütüphaneleri
├── .gitignore                        Hassas dosya filtreleri
├── scripts/
│   ├── fiyat_guncelle.py             Ana fiyat scripti
│   └── benchmark_fiyat.py            Benchmark scripti
└── .github/
    └── workflows/
        ├── portfoy-guncelle.yml      4 zamanlı cron
        └── benchmark-guncelle.yml    Günlük benchmark cron
```

### 7.2 Cron tetikleyiciler

**portfoy-guncelle.yml** (Pzt-Cum):
- 10:30 TR (intraday)
- 12:30 TR (intraday)
- 14:30 TR (intraday)
- 18:35 TR (kapanış — `--kapanis` parametresi ile, gecmis.json'a yazar)

**benchmark-guncelle.yml** (Pzt-Cum):
- 19:00 TR (kapanış sonrası — benchmark_gecmis.json'a son günü ekler)

### 7.3 Manuel çalıştırma

GitHub Actions sayfasından `workflow_dispatch` ile manuel tetiklenir:
- `Run workflow` → `Branch: main` → `Run workflow`
- Ana workflow için: `kapanis` parametresi `true` yapılırsa gecmis.json'a yazar
- Benchmark için: `gecmis` parametresi `true` yapılırsa 5 yıllık veriyi sıfırdan çeker

### 7.4 GitHub Secrets (zorunlu)

- `GOOGLE_SHEETS_CREDENTIALS` — Service account JSON içeriği
- `SHEETS_ID` — Google Sheets dosya ID'si

### 7.5 Veri akışı

```
Sheets okuma → fiyat çekme (yfinance + tefas-crawler)
            → JSON yazma (prices, portfoy, gecmis)
            → git commit + push (github-actions[bot] ile)
```

---

## 8. YEDEKLEME STRATEJİSİ

Birincil veri kaynakları (yfinance, tefas-crawler) düştüğünde script'in
çakılmaması ve dashboard'un mümkün olduğunca canlı kalması için katmanlı
yedek mantığı kuruldu (10 Mayıs 2026, Seçenek C).

### 8.1 Katmanlı yedek tablosu

| Veri | Birincil | Yedek | Yedek tipi |
|---|---|---|---|
| USD/TRY ve EUR/TRY | yfinance `=X` | **TCMB resmi XML** | Anlık (tek nokta) |
| Bitcoin TL | yfinance `BTC-USD × USDTRY` | **CoinGecko API** | TRY direkt + 24h değişim |
| BIST hisse | yfinance `.IS` | yok | — |
| TEFAS fon/emeklilik | tefas-crawler | yok | — |
| Gram altın | yfinance `GC=F × USDTRY ÷ 31.1035` | yok (USD kuru yedeğine bağımlı) | — |

> **Not:** Hisse, TEFAS ve gram altın için ayrı yedek kurulmadı. Test
> edilmiş kaynaklar (scraping siteleri) kırılgan olduğu için v2'ye
> bırakıldı. Hisse veya TEFAS verisi gelmezse o satır `fiyat_eksik: true`
> ile işaretlenir, dashboard "—" gösterir.

### 8.2 Hata durumunda davranış

- **Birincil çalıştı:** Normal akış, `prices.json.kaynak_durumu`
  içinde `kur_kaynak: "yfinance"` ve `btc_kaynak: "yfinance"`.
- **Birincil çöktü, yedek çalıştı:** Akış devam eder,
  `kaynak_durumu` içinde `"tcmb"` veya `"coingecko"` yazar. Frontend
  ileride bu alana bakıp uyarı gösterebilir ("Şu an TCMB resmi kurundan
  geliyor").
- **Birincil + yedek ikisi de çöktü:** İlgili alan `null` döner, satır
  `fiyat_eksik: true` ile işaretlenir. **Script çakılmaz**, diğer
  veriler normal akışla yazılır.

### 8.3 TCMB sınırlamaları

TCMB `today.xml` sadece **bugünkü** kuru verir, tarihsel seri vermez.
Bu yüzden:
- `fiyat_guncelle.py`'de TCMB tam yedek olarak çalışır (anlık fiyat
  yeterli, `onceki = guncel` kabul edilir, günlük yüzde değişim sıfır
  görünür ama dashboard kopmaz).
- `benchmark_fiyat.py`'de TCMB **sınırlı yedek**: sadece bugünün tek
  noktasını seriye ekler. Ertesi gün yfinance düzelirse 10 günlük
  pencere kendini onarır.

### 8.4 CoinGecko detayları

CoinGecko ücretsiz public API, rate limit ~30 req/dakika. Script
maksimum 4 cron × 1 BTC sorgusu = günde 4 istek yapar, limit içinde
fazlasıyla. `try_24h_change` alanından önceki gün hesaplanır:
`onceki = guncel / (1 + change_24h / 100)`.

### 8.5 Manuel müdahale

Hata mesajları log'a yazılır (`[WARN]` veya `[ERROR]` prefix). Kullanıcı
GitHub Actions log'unu Claude'a gösterirse Claude alternatif önerebilir
(ek scraping yedek, kaynak değişikliği, vb.). v2'de `altinkaynak.com`,
`bigpara`, `mynet` scraping yedekleri eklenebilir.

---

## 9. ACİL DURUM — LOCK BUG (referans)

GitHub Actions geçişi öncesi Cowork'te `.git/index.lock` sürpriz sorunu
için manuel çözüm:

```bash
cd ~/Documents/pf-a7k9m3p2 && \
  rm -f .git/index.lock .git/HEAD.lock && \
  git rebase --abort 2>/dev/null; \
  git fetch origin && git reset --hard origin/main && git status
```

GitHub Actions stabil çalışmaya başladıktan sonra Cowork görevleri
silinir, bu bölüm dosyadan çıkarılır.

---

## 10. GÜVENLİK NOTU

- Repo public (GitHub Pages için).
- Site şifresi sadece HTML içinde basit koruma; hassas veri JSON'larda.
- Bu bilinçli bir tercih (kişisel kullanım, tehdit modeli düşük).
- **Bu dosyaya ASLA yazılmaz:** şifreler, token'lar, Sheets ID,
  service account key, kişiyle özdeşleşen tutarlar.

---

## 11. SON GÜNCELLEMELER (15 Mayıs 2026)

### 11.1 Altın veri kaynağı

- **Birincil:** yfinance `GC=F` (ons altın USD × USDTRY ÷ 31.1035)
- **Yedek:** prices.json snapshot koruması (§14.1 — 3. yedek katman)
- **Kaynak kodu:** `scripts/fiyat_guncelle.py` → `gram_altin_cek()`

Yedek tablosu (bkz. Bölüm 8.1):

| Veri | Birincil | Yedek |
|---|---|---|
| Gram altın | yfinance `GC=F × USDTRY ÷ 31.1035` | **prices.json snapshot** (§14.1) |

### 11.2 Dashboard altın render

- `index.html` güncellendi: `tip == "altin"` kalemleri artık **"🥇 Altın"** bölümünde gösteriliyor.
- Derya portföyünde `24AYAR` 301.86 gram → ~2.06M TL.

### 11.3 Otomasyon (cron-job.org)

- **Servis:** `https://console.cron-job.org` (Özkan hesabı)
- **Cron 1 — "Portfoy Otomatik":** 10:30, 12:30, 14:30, 16:30 (Pzt-Cum) → normal mod
- **Cron 2 — "Portfoy Kapanis":** 18:35 (Pzt-Cum) → kapanış modu (`inputs.kapanis=true`)
- **GitHub PAT:** `cron-job-org-portfoy-tetikleyici` (geçerlilik: 2027-05-14)
- GitHub schedule cron'ları paralel sigorta olarak korunuyor.

### 11.4 Yapılacaklar (15 Mayıs'ta belirlendi)

> **Durum (19 Mayıs 2026):** Hepsi tamamlandı. Detaylar için §12.

1. ~~Dashboard toplamları düzeltme~~ ✅ (§12.1)
2. ~~Benchmark Guncelleme hatası~~ ✅ (§12.2)
3. ~~Geçmiş Veriler sekmesi~~ ✅ (§12.4, 21 Mayıs'ı bekliyor)
4. ~~Privacy/gizlilik mode~~ ✅ (§12.3)

---

## 12. 19 MAYIS 2026 — FAZ 2 GÜNCELLEMELERİ (kapsamlı)

**Amaç:** Yarın bir gün repo silinse bile bu bölümle her şeyi
yeniden kurmak mümkün. Bu oturumda yaptıklarımız, çıkardığımız
dersler, mimari kararlar ve sırada ne var.

### 12.1 Dashboard yeniden düzenlemesi

**Üst aile bar (`<div class="header">` içinde):**
- "Toplam Maliyet" ve "Net K/Z" kartları **kaldırıldı**.
- "Toplam Aile Varlığı" başlığının altındaki K/Z % rozeti (`genel-badge`) **kaldırıldı**.
- "Günlük Kazanç" kartı yeniden yazıldı:
  - Negatif → `-₺xxx` ön eki + kırmızı renk
  - Pozitif → `+₺xxx` ön eki + yeşil renk
  - Sıfır → işaretsiz + nötr
  - TL'nin **altına yüzde satırı** eklendi (aynı renkte, daha küçük font)

**CSS özgüllük (specificity) bug fix:**
- `.summary-card .val` kuralı `color: white` belirliyordu.
- `.green` ve `.red` modifier class'ları özgüllükte alttaydı (alt sayfaya bakın §12.6.4), o yüzden hiç çalışmıyordu.
- Çözüm: `.summary-card .val.green` ve `.summary-card .val.red` kuralları eklendi (özgüllük 0,3,0 > 0,2,0).

**Tab içi üst kartlar (Özkan ve Derya tablarında):**
- "Toplam K/Z" kartı **kaldırıldı**.
- "Portföy Değeri" kartı **dinamik** oldu:
  - Özkan tabında: başlık `"Emeklilik ve Alacak Hariç Özkan Varlık"`, değer = `toplam − emeklilik − alacak`
  - Derya tabında: başlık `"Emeklilik Hariç Derya Varlık"`, değer = `toplam − emeklilik`
- Diğer kartlar (Günlük K/Z, Günün Yıldızı, Günün En Zayıfı) aynı kaldı.

**Fonlar & Emeklilik bölümü — komple refactor:**
- Eski tek tablo (`fonlarRaw` karışık) yerine **4 ayrı blok**:
  1. 🏦 YurtdışıFon
  2. 🏦 Fon
  3. 🏦 AltınFonu
  4. 🏦 Emeklilik
- Her blok kendi başlığında alt-toplam, kendi 12-sütunlu tablosu, kendi TOPLAM satırı.
- **Ağırlık sütunu** o blok içindeki yüzde (`item.tg / blokToplam × 100`), tüm portföye değil.
- Boş tip render edilmez (`if (list.length === 0) return ''`).
- **Emeklilik bloğunda** maliyet null olduğu için: Maliyet, K/Z ₺, K/Z %, YBB hücreleri "—" gösterilir. Bunu desteklemek için `enrichItem()` fonksiyonuna `maliyetVar` flag eklendi.

**Kripto kartı:**
- Sarı/krem gradient zemin (`linear-gradient(to right, #fffbeb, #fef3c7)`) → **beyaz/gri** (diğer bölümlerle uyumlu, `#e2e8f0` border).
- `.kitem .kv`'den `color` özelliği **kaldırıldı**. Eskiden `color: #78350f` (kahverengi) idi, bu `.val-pos/.val-neg` (yeşil/kırmızı) class'larını override ediyordu.
- "Günlük ₺" ve "Günlük %" item'ları eklendi (Değer ile K/Z arasında).
- Günlük ₺ ve K/Z için yeni `fullSign(v)` helper kullanılıyor:
  - Pozitif: `+₺xxx` (yeşil)
  - Negatif: `-₺xxx` (kırmızı)
  - Sıfır: işaretsiz

### 12.2 Benchmark backend güncellemesi

**Sorun (11–18 Mayıs):**
- `scripts/benchmark_fiyat.py` PyPI'dan `tefas-crawler==0.6.0` paketi kullanıyordu. Bu paket güvenilmez (TEFAS API değişiklikleri).
- Ek olarak, yfinance GitHub Actions IP havuzundan **Yahoo Finance'a erişemiyor** (rate limit/block: `"Expecting value: line 1 column 1 (char 0)"` hatası).
- Sonuç: 6 gün boyunca her gece benchmark cron'u failure verdi, `benchmark_gecmis.json` hiç oluşturulamadı.

**Bonus problem:** İlk kurulum `--gecmis` parametresiyle hiç yapılmamıştı. Workflow `workflow_dispatch` input dropdown'undan `true` seçimi atlanmıştı.

**Çözüm:** Ana script `fiyat_guncelle.py` zaten `borsapy` (saidsurucu/borsapy) kullanıyordu. Benchmark script'i de aynı pattern'e alındı.

**Yeni katmanlı yapı (`scripts/benchmark_fiyat.py`):**

| Seri | Birincil | Yedek 1 | Yedek 2 (son çare) |
|---|---|---|---|
| BIST100 | `bp.Index("XU100")` | yfinance `XU100.IS` | — |
| USD/TRY | `bp.FX("USD")` | yfinance `USDTRY=X` | TCMB anlık (tek nokta) |
| Gram Altın | `bp.FX("gram-altin")` (TL direkt) | yfinance `GC=F × USDTRY ÷ 31.1035` | — |
| Amerika Hisse (TL) | `bp.Fund("AFA")` | `bp.Fund("ABE")` | yfinance `^GSPC × USDTRY` |
| YAE | `bp.Fund("YAE")` | — | — |
| TÜFE | Sheets `TUFE` sekmesi | — | — |

**Önemli karar — Amerika Hisse (AFA):**
- borsapy doğrudan S&P500 endeksini desteklemiyor (TR piyasa odaklı paket).
- Türk yatırımcının S&P500'e erişim aracı: TEFAS S&P500 takipli fonlar.
- **AFA** = Amerika hisse senedi fonu (kullanıcı tercihi). 5 yıllık veride S&P500'e çok yakın hareket etti (gözlenen +793% vs beklenen ~+750%).
- Yedek **ABE** (Amerika Hisse Senedi Fonu).
- JSON anahtarı `sp500_tl` → `amerika_hisse` olarak değişti.
- Yardımcı fonksiyonlar: `borsapy_index_seri`, `borsapy_fx_seri`, `borsapy_fund_seri`.

**`requirements.txt` değişikliği:**
- `tefas-crawler==0.6.0` **silindi**. (Eski paket, artık kullanılmıyor.)
- `borsapy==0.10.0` **kalır** (saidsurucu/borsapy).

**İlk kurulum:** `benchmark_gecmis.json` hiç yoktu. Workflow `gecmis=true` ile manuel tetiklendi (Actions → "Benchmark Guncelleme" → "Run workflow" → dropdown'dan `true` seç → "Run workflow"). 5 yıllık seri çekildi:
- BIST100: 1268 kayıt
- Amerika Hisse (AFA): 1256 kayıt
- Gram Altın: 1726 kayıt
- YAE: 71 kayıt (TEFAS v2 API'da fonun yaşı sınırlı)
- TÜFE: 1 kayıt (Sheets'te sadece 2025-04 var, kullanıcı zamanla ay ekleyecek)

### 12.3 Privacy (gizlilik) modu

Sağ üst header'da göz ikonu (👁 ↔ 🙈) ile aç/kapat.

**Mekanik:**
- Aile toplamı sabit ₺1.000.000 olarak görünür.
- Katsayı `k = 1.000.000 / gerçek_aile_toplamı` hesaplanır.
- Her portföy satırında çarpılanlar: `adet`, `guncel_tl`, `onceki_tl`, `gunluk_kazanc_tl`.
- Çarpılmayanlar: `maliyet` (birim, gerçek piyasa bilgisi), `gunluk_yuzde` (oran zaten korunur).
- **Maliyet hücreleri görüntüde "—" maskelenir** (kullanıcı tercihi: "matematiğe gerek yok"). Hisseler tablosu, fon blokları, kripto kartı hepsinde.
- Yüzdeler (ağırlık, günlük %, K/Z %, YBB) aynen kalır.
- Birim güncel fiyat aynen kalır (`adet × birim_fiyat = TL` ilişkisi korunur çünkü `tg/adet = guncel`, hem `tg` hem `adet` aynı `k` ile çarpılır, oran aynı).

**Geçmiş veriler için normalize:**
- Her gün için **kendi katsayısı** hesaplanır (`1.000.000 / o_günün_aile_toplamı`).
- Sonuç: her satır 1.000.000 sabit toplam gösterir, ama günler arası oran zamanla değişir (yani %20'den %25'e büyüme görsel kalır).
- `normalizeGecmis()` fonksiyonu `doRender()` içinde çağrılır.

**`doRender()` sarmalayıcı:**
- `loadData()` raw verileri 4 global'e atar (`_rawPortfoy`, `_rawPrices`, `_rawBenchmark`, `_rawGecmis`), sonra `doRender()`.
- `doRender()` privacy durumuna göre veriyi normalize edip `render(p, prices, b, g)` çağırır.
- Privacy toggle yapıldığında **aktif tab hatırlanır**, Chart.js instance'ları destroy edilir, render yapılır, aktif tab geri yüklenir (canvas'lar yeniden çizilir).

**State persistence:** `sessionStorage.getItem('privacy') === '1'`. Sekme kapanınca sıfırlanır, sayfa yenilenince korunur.

### 12.4 Dashboard yeni tablar

Sidebar artık **5 tab**:

```
👤 Özkan • ₺...   |   👤 Derya • ₺...   |   📊 Benchmark   |   📋 Geçmiş Veriler   |   📈 Grafik
```

**📊 Benchmark tabı:**
- Üstte 2 seçici:
  - "Karşılaştırılacak varlık" dropdown (`<select>` + `<optgroup>`, 15 öğe, ÖZKAN/DERYA/AİLE grupları)
  - Dönem buton grubu: 1H / 1A / YTD / 6A / 1Y / 3Y / 5Y (varsayılan 1A)
  - Not: "Özel tarih aralığı" v2'ye bırakıldı.
- **Chart.js çizgi grafik**: seçilen varlık (turkuaz, kalın, dolgu YOK, düz çizgi) + 4 benchmark (BIST100, Amerika Hisse AFA, Gram Altın, YAE; ince kesik çizgi, farklı renkler) — hepsi kümülatif % getiri, başlangıç %0.
  - TÜFE grafikte yok (aylık veri, günlük çizgiyle uyumsuz).
- **7×7 karşılaştırma tablosu**: 7 dönem × (1 varlık + 5 benchmark + 1 "Fark") = 7 sütun + 7 satır.
- Alt bilgi notu: portföy milat tarihi (21 Mayıs).

**📋 Geçmiş Veriler tabı (Excel benzeri tablo):**
- 12 sütun (kullanıcı kesin listesi):
  1. **Tarih** (sticky-left — yatay scroll'da görünür kalır)
  2. Özkan (em+alacak hariç)
  3. Özkan Toplam
  4. Özkan Emeklilik
  5. Kripto (sadece Özkan'da)
  6. Derya (em hariç)
  7. Derya Toplam
  8. Derya Emeklilik
  9. Derya Altın
  10. Aile Toplam
  11. Aile (em+alacak hariç)
  12. Aile Emeklilik
- Üstte tarih seçici (`<input type="date">`): seçilen tarihin satırı **sarı highlight + scrollIntoView**.
- "Vurguyu temizle" butonu.
- Sıralama: en yeni en üstte.
- Grafik yok, indir butonu yok (kullanıcı tercihi).
- gecmis.json yoksa: "📭 Geçmiş veri henüz yok — milat tarihi 21 Mayıs 2026" mesajı.

**📈 Grafik tabı:**
- 15-öğeli dropdown (Benchmark ile aynı liste).
- 7 dönem butonu (1H/1A/YTD/6A/1Y/3Y/5Y).
- **Chart.js çizgi grafik**: SADECE seçilen varlığın kümülatif % getirisi (turkuaz, alan dolgu var). Benchmark karşılaştırması yok.
- Alt durum kutusunda dönem getirisi rakamı (örn. "1A dönemde toplam değişim: +5,23%").
- gecmis.json yoksa boş canvas + uyarı mesajı.

### 12.5 CDN bağımlılıkları (yeni)

`index.html` `<head>` içinde:

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
```

**Chart.js v4'te `time` scale için date-fns adapter zorunlu.** Toplam ~70 KB, CDN, ek build adımı yok.

### 12.6 Öğrenilen dersler — YAPILMAMASI GEREKENLER

**12.6.1 — Workflow_dispatch dropdown'u atlamak:**
GitHub Actions'ta `workflow_dispatch` ile manuel tetiklerken, varsayılan input değerleri (örn. `gecmis: 'false'`) **kullanıcı dropdown'a tıklayıp `true` seçmedikçe** geçmez. İlk benchmark çalıştırmasında bu atlandı, 6 gün boyunca cron her gün hata verdi.
**Doktrin:** Manuel tetikleme talimatı verirken adım adım, dropdown'a tıklama seviyesinde net olunmalı. Log'da `Run if [ "false" = "true" ]; then` görüldüğünde dropdown atlanmış demektir.

**12.6.2 — `tefas-crawler` PyPI paketi güvenilmez:**
TEFAS API değişiklikleri yüzünden zaman zaman bozuluyor. **TEFAS verisi için tek doğru kaynak:** `borsapy.Fund(kod)` (saidsurucu/borsapy, TEFAS v2 API). `tefas-crawler==0.6.0` bağımlılığı `requirements.txt`'ten silindi.

**12.6.3 — yfinance GitHub Actions IP'lerinden çalışmıyor:**
Yahoo Finance, GitHub Actions IP havuzunu rate-limit'liyor. yfinance log'unda `"Expecting value: line 1 column 1 (char 0)"` ya da `"possibly delisted; no timezone found"` görürsen sebep budur.
**Doktrin:** Tüm fiyat çekimlerinde **borsapy birincil, yfinance yedek, TCMB son çare** sıralaması.

**12.6.4 — CSS specificity (özgüllük) bug'ı:**
Bir parent class'ı (`.summary-card`) içindeki child class'a (`.val`) `color: X` verirsen, sonra `.green/.red/.blue` modifier class'ları **özgüllük olarak alttadır**:
- `.summary-card .val` → (0, 2, 0) = 20
- `.green` → (0, 1, 0) = 10  → **özgüllük yetmiyor**
- `.summary-card .val.green` → (0, 3, 0) = 30 → ✓
**Çözüm:** Modifier class'larını parent scope ile birlikte yaz: `.summary-card .val.green { color: ... }`.

**12.6.5 — `Math.abs(negatif)` + sadece "+" döndüren `tlSign` çakışması:**
`fmt(Math.abs(v))` mutlak değer alır (eksi gider). `tlSign(v)` sadece pozitif için "+" döndürür (negatif için boş string). Sonuç: negatif değerler pozitif gibi görünür ("−122.237 TL" yerine "₺122.237").
**Çözüm:** Yeni `fullSign(v)` helper: `v > 0 ? '+' : (v < 0 ? '-' : '')`. Üst banner ve kripto kartında bu kullanılıyor.

**12.6.6 — Chart.js v4 + `time` scale = adapter şart:**
Chart.js v4'te `scales: { x: { type: 'time' } }` kullanmak için tarih adapter'ı **zorunlu**. `chartjs-adapter-date-fns` CDN ile yükleniyor. Olmadan: "Time scale: cannot find a date adapter" hatası.

**12.6.7 — Tab değişimi sonrası Chart.js yeniden çizim:**
Chart.js bir canvas'a bağlandığında, canvas DOM'dan kalkınca (`panel-X` `hidden` olunca) yeniden açıldığında **otomatik canlanmaz**.
**Doktrin:** `switchTab(name)` içinde ilgili tab açıldığında `setTimeout(refreshX, 0)` çağrısı yap. `setTimeout 0` canvas görünür hale gelince çalışacağı için Chart.js boyut alabilir.

**12.6.8 — `doRender()` sonrası aktif tab restorasyonu:**
Privacy toggle → `doRender()` → `render()` panelsHtml'i yeniden yazar → varsayılan ilk tab aktif olur. Eğer kullanıcı benchmark/grafik tabındaysa, kaybolur.
**Doktrin:** `doRender()` başında aktif tab'ı hatırla, render sonrası eski tab'a dön. Aynı zamanda eski Chart.js instance'larını destroy et (yeni canvas oluştuğunda dangle ref kalmasın).

**12.6.9 — Claude Preview MCP ve `defaults write` sandbox engeli:**
Claude Preview MCP `python -m http.server`'ı sandbox altında çalıştıramıyor (`os.getcwd()` `PermissionError`). `defaults write com.apple.Safari ...` da Safari container'a yazma izni yok.
**Pratik yol:** Bash ile manuel `python3 -m http.server PORT`. Dikkat: hangi dizinden başlatıldığı önemli! Worktree'den başlatırsan ana repodaki `benchmark_gecmis.json` 404 döner (worktree'de yok). **Ana repodan başlat veya worktree'ye dosyaları kopyala.**

**12.6.10 — Git lock dosyası ve cron çakışması:**
Otomatik commit cron'u (cron-job.org veya GitHub Actions) tam o anda push yaparsa, lokal `.git/index.lock` kalabilir.
**Acil kurtarma:**
```bash
cd ~/Documents/pf-a7k9m3p2
rm -f .git/index.lock .git/HEAD.lock
git rebase --abort 2>/dev/null
git fetch origin
git reset --hard origin/main
git status
```
**Sonra worktree'den `index.html`'i tekrar kopyala** (reset --hard lokali sildi).

**12.6.11 — Tarayıcı cache + lokal sunucu:**
Python `http.server` cache header göndermiyor, ama tarayıcı yine de cache'leyebilir. JS değişiklikleri yansımayabilir.
**Pratik:** `Cmd+Shift+R` (hard refresh) ya da JSON'lara cache-busting eklenmiş (`?t=Date.now()`).

### 12.7 Mimari kararlar

**Privacy modu nasıl çalışır:**
1. `loadData()` 4 dosyayı fetch eder → raw veriler global'lere (`_rawPortfoy` vs.).
2. `doRender()` privacy durumuna göre veriyi normalize eder (orijinal raw'dan yeni clone üretir).
3. `render(p, prices, b, g)` her zaman normalize edilmiş veya raw veriyle çağrılır.
4. `_benchmarkData = b; _gecmisData = g;` global'leri render içinde set edilir; refreshBenchmark/refreshGecmis/refreshGrafik bunlardan okur.
5. Privacy toggle → sadece `doRender()` yeniden çağrılır; fetch yapılmaz (raw'lar zaten elde).

**Veri yapısı (özet):**
- **`prices.json`** — anlık fiyatlar (`hisseler`, `fonlar_ve_emeklilik`, `kripto`, `gram_altin_tl`, `usd_try`, `eur_try`, `kaynak_durumu`, vs.). Her güncellemede üzerine yazılır.
- **`portfoy.json`** — `{portfoyler: {ozkan: [], derya: []}}`. Her satırda: `tip`, `tip_orjinal`, `kod`, `kod_orjinal`, `adet`, `maliyet` (birim), `guncel_tl`, `onceki_tl`, `gunluk_kazanc_tl`, `gunluk_yuzde`, `fiyat_eksik`.
- **`gecmis.json`** — `{kayit_baslangic: "2026-05-21", gunler: {tarih: {ozkan: {kategoriler: {hisse, fon, ...}, toplam: X}, derya: {...}, genel_toplam: Y}}}`. **21 Mayıs'tan itibaren her iş günü 18:35 kapanışta bir satır**.
- **`benchmark_gecmis.json`** — `{kayit_baslangic: "2021-04-20", son_guncelleme, seriler: {bist100: {YYYY-MM-DD: değer}, amerika_hisse, gram_altin, yae, tufe_aylik_gerceklesen, tufe_aylik_beklenti}}`. Her gün 19:00 cron'unda son gün eklenir (son 10 gün yedek).
- **`yilbasi_fiyatlari.json`** — Her yıl ilk fiyat çekiminde yılbaşı snapshot, YTD getiri için.

**Tip normalizasyonu** (§2.1'den): Türkçe karakterler Latin'e (`ı→i, ş→s, ç→c, ğ→g, ü→u, ö→o`), boşluk atılır, lowercase karşılaştırma. Portfoy.json'da `tip` zaten lowercase Latin (`yurtdisifonu, altinfonu, emeklilik` vs.). Ekran gösteriminde `tip_orjinal` (`YurtdisiFonu` vs.) kullanılır.

### 12.8 Hangi dosyada ne var (REFERANS HARİTASI)

| Dosya | İçerik | Boyut |
|---|---|---|
| `index.html` | Tüm frontend (HTML + CSS + JS). | ~1370 satır, 31 JS fonksiyonu |
| `scripts/fiyat_guncelle.py` | Ana fiyat scripti. Sheets oku, fiyat çek, JSON yaz. | ~1100 satır |
| `scripts/benchmark_fiyat.py` | Benchmark veri scripti (5 yıllık + günlük). | ~400 satır |
| `.github/workflows/portfoy-guncelle.yml` | Cron 4 zamanlı (10:30, 12:30, 14:30, 18:35 TR). | 50 satır |
| `.github/workflows/benchmark-guncelle.yml` | Cron 1 zamanlı (19:00 TR). | 60 satır |
| `requirements.txt` | Python bağımlılıkları (`gspread, google-auth, yfinance, borsapy, requests, pandas`). **tefas-crawler artık yok.** | 6 satır |
| `portfoy.json` | Anlık portföy verisi. | ~7 KB |
| `prices.json` | Anlık fiyatlar. | ~2 KB |
| `gecmis.json` | Günlük kapanış snapshot'ı. **Henüz yok**, 21 Mayıs'tan itibaren oluşur. | — |
| `benchmark_gecmis.json` | 5 yıllık + günlük benchmark serileri. | ~130 KB |
| `yilbasi_fiyatlari.json` | Yılbaşı fiyatları. | <1 KB |

**Frontend ana JS fonksiyonları (`index.html` içinde):**

| Fonksiyon | Görev |
|---|---|
| `loadData()` | Tüm JSON dosyalarını fetch et, global'lere ata, `doRender()` çağır. |
| `doRender()` | Privacy durumuna göre veriyi normalize et, render çağır, aktif tab'a dön. |
| `render(p, pr, b, g)` | Üst banner + tab butonları + paneller (5 tab). |
| `renderPortfoy(name, items, prices)` | Bir kişinin tab içeriği (üst kartlar + dağılım + Hisseler + 4 fon bloğu + Kripto + Altın + Alacak). |
| `renderFonBlok(baslik, list)` | Tek bir fon tipi için tablo (YurtdışıFon/Fon/AltınFonu/Emeklilik). |
| `enrichItem(it, prices)` | Bir portföy satırını hesaplı alanlarla zenginleştirir (`tg, tm, kz, kzp, ybb, gunlukKZ, gunlukP, maliyetVar`). |
| `benchmarkPanelHtml()` / `refreshBenchmark()` | Benchmark tabı. |
| `gecmisPanelHtml()` / `refreshGecmis()` | Geçmiş Veriler tabı. |
| `gecmisDegerleri(gun)` | Bir günden 12 sütunun TL değerlerini hesapla. |
| `grafikPanelHtml()` / `refreshGrafik()` | Grafik tabı. |
| `switchTab(name)` | Tab geçişi, Chart.js redraw tetikleyici. |
| `togglePrivacy()` / `normalizePortfoy()` / `normalizeGecmis()` / `updatePrivacyButton()` | Privacy modu. |
| `portfoySerisi(secim, gecmis)` | Dropdown seçimine göre gecmis.json'dan zaman serisi {tarih: TL}. |
| `cumulativeSeri(seri, b, e)` | Kümülatif % getiri hesabı (Chart.js datasets formatında). |
| `donemBaslangic(donem, sonTarih)` | "1H/1A/YTD/6A/1Y/3Y/5Y" → tarih string. |
| `donemGetirisi(seri, b, e)` | Tek skaler % getiri (tablo için). |
| `tufeDonemGetirisi(tufe, b, e)` | Aylık TÜFE'den kümülatif: (1+r1)(1+r2)...-1. |

### 12.9 Şu anki durum (19 Mayıs 2026 gece)

✅ **Tamamlandı (tüm 19 Mayıs işleri):**
- Tüm dashboard düzenlemeleri (§12.1)
- Benchmark backend borsapy geçişi (§12.2)
- Privacy modu (§12.3)
- Benchmark / Geçmiş Veriler / Grafik tabları (§12.4)

⏳ **Otomatik bekleniyor:**
- **21 Mayıs 2026 18:35** → `gecmis.json` ilk satır.
- **25-26 Mayıs** → 3-5 günlük veri biriktiğinde Geçmiş Veriler ve Grafik tabları gerçek veriyle test edilebilir.

### 12.10 Sonraki yapılacaklar (öncelik sırasıyla)

1. **21 Mayıs sonrası ufak UX düzeltmeleri** — Gerçek `gecmis.json` verisiyle Geçmiş Veriler tablosu ve Grafik tabı test edilecek, küçük görsel/etkileşim düzeltmeleri çıkabilir.

2. ~~**Genel (Aile) tabı**~~ ✅ (22 Mayıs, commit f57230f) — renderAile() fonksiyonu, 4 kart + kategori dağılım tablosu. Tab CSS'i `flex-wrap: wrap` yapıldı.

3. **Her tab için küçük portföy çizgi grafiği** (CLAUDE.md §5.4) — Tab içeriğinin üstüne ufak bir trend grafiği. Grafik tabıyla kısmen örtüşüyor, kararı veri gelince ver.

4. ~~**Veri Güncelle butonu**~~ — İptal edildi (25 May). Cron zaten günde 4 kez çalışıyor; manuel yenileme ihtiyacı yok. Gerekirse tarayıcı F5 yeterli, acil fiyat çekimi için Actions → "Run workflow" var (§7.3).

5. ~~**Twelve Data altın yedeği temizliği**~~ ✅ (25 May, commit 5f7df88) — `twelve_data_xau_usd()` fonksiyonu silindi, secret kullanımdan kaldırıldı, §11.1 güncellendi.

6. **Benchmark günlük güncelleme gözlemi** — Her gün 19:00 TR cron'unda 4 ana serinin son gününün eklenmesi takip edilecek. AFA fonu için TEFAS v2 API her gün başarılı çalışmalı; çalışmazsa ABE'ye düşer, o da olmazsa yfinance'a (genelde çalışmaz).

7. **Benchmark tabı "Özel tarih aralığı"** (CLAUDE.md §6.1) — Şu an yok, v2.

8. **TÜFE Sheets güncellemesi** — `TUFE` sekmesinde şu an sadece 2025-04 verisi var. Kullanıcı her ay yeni TÜİK rakamını eklemeli (ay sonu açıklanır). Otomasyon yok (manuel).

### 12.11 Yeni bir Claude oturumu nasıl başlamalı?

Yeni oturum bu CLAUDE.md'yi otomatik okur, ama hızlı kontrol için:

```bash
ls -la *.json scripts/ .github/workflows/
git log --oneline -10
cat CLAUDE.md | head -50  # bağlam için
```

**Önemli son commit'ler (kronolojik):**
- `6e93ce2` — Geçmiş Veriler + Grafik tabları (19 May)
- `9a9ff68` — Gizlilik (privacy) modu (göz ikonu) (19 May)
- `9af06dc` — Benchmark dashboard tabı (Chart.js + 7×7 tablo) (19 May)
- `88fb442` — S&P500 → Amerika Hisse (AFA) (19 May)
- `97e2784` — Tüm benchmark serileri için borsapy birincil (19 May)
- `f281069` — tefas-crawler → borsapy (YAE fix) (19 May)
- `d9ada90` — Kripto kartı beyaz tema + işaret düzeltmesi (19 May)
- `db4fe1b` — Günlük Kazanç işaret/renk/yüzde + kripto Günlük ₺/% (19 May)
- `caa20d6` — Dashboard üst kartlar + Fonlar 4 ayrı blok (19 May)
- `b265f8a` — CLAUDE.md Bölüm 11 eklendi (19 May)

**Felaket kurtarma (her şey silinirse):**
1. Repo clone: `git clone https://github.com/Ozkan40tree/pf-a7k9m3p2.git`
2. GitHub Secrets ayarlı mı kontrol et: `GOOGLE_SHEETS_CREDENTIALS`, `SHEETS_ID`, `TWELVE_DATA_API_KEY` (opsiyonel).
3. `requirements.txt`'i yükle: `pip install -r requirements.txt`
4. Sheets'in `Ozkan_Portfoy`, `Derya_Portfoy`, `TUFE` sekmelerinin servisAccount ile paylaşıldığından emin ol.
5. Cron'lar (cron-job.org + GitHub Actions schedule) zaten çalışır.
6. İlk kurulum: benchmark'i `gecmis=true` ile manuel tetikle (5 yıllık seri çekmek için).
7. `gecmis.json` 21 Mayıs sonrası kendiliğinden dolar.

### 12.12 Bu dosyayı güncellerken kurallar

- Her büyük faz sonunda yeni numaralı bölüm ekle (§13, §14, vs.).
- Eski bölümleri **silme** — sadece "Durum: bkz §X" notu ekle.
- Hatalardan dersleri **12.6'daki formatla** kaydet: ne oldu, sebep, çözüm.
- "Yapılmaması gerekenler" bölümünü canlı tut.
- Tarih ve commit hash'leri her dersle birlikte.

---

## 13. SIFIRDAN KURULUM REHBERİ (bağımsız AI/yeni kullanıcı için)

> Bu bölüm, bağımsız bir yapay zeka veya yeni bir geliştiricinin bu
> CLAUDE.md'yi okuyup sistemi **sıfırdan kurabilmesi** için yazılmıştır.
> §0-§12 davranışı ve kararları açıklar; §13 eylem adımlarını içerir.
> Bu bölüm self-contained'dir: dış kaynağa bakmadan kurulum yapılabilir.

### 13.1 Sistem genel bakışı

**Ne yapar?** Bir Türk ailenin (Özkan + Derya) yatırım portföyünü
takip eden, GitHub Pages üzerinde yayınlanan, basit şifre korumalı bir
web dashboard.

**Mimari:**

```
┌─────────────────┐  okur  ┌────────────────┐  yazar  ┌──────────────┐
│  Google Sheets  │ ◄───── │ Python script  │ ──────► │ JSON dosyalar│
│ (kullanıcı veri │  (gspread)  │(fiyat_guncelle)│       │ (repo'ya commit)│
│  girdiği yer)   │        │(benchmark_fiyat)│       └──────────────┘
└─────────────────┘        └────────────────┘                │
                                ▲                            ▼
                                │                  ┌──────────────────┐
                          ┌─────┴─────┐            │ GitHub Pages     │
                          │GitHub      │            │ frontend         │
                          │Actions cron│            │ (index.html)     │
                          └────────────┘            └──────────────────┘
                                                            ▲
                                                            │
                                                       ┌────┴────┐
                                                       │ Tarayıcı│
                                                       └─────────┘
```

**Kullanıcı sadece Sheets'e veri girer.** Diğer her şey otomatik.

**Bileşenler:**

- **Backend:** 2 Python scripti + 2 GitHub Actions workflow + ~5 JSON dosyası
- **Frontend:** Tek bir `index.html` dosyası (HTML + CSS + JS, ~1370 satır, CDN'den Chart.js)
- **Veri kaynakları (öncelik sırasıyla):**
  - `borsapy` (saidsurucu/borsapy) — BIST hisse, döviz, gram altın, TEFAS fon
  - `yfinance` — yedek (Yahoo Finance, GitHub Actions'tan genelde çalışmaz)
  - `TCMB` resmi XML — döviz son çare
  - Google Sheets `TUFE` sekmesi — enflasyon (manuel ay ekleme)

### 13.2 Google Cloud kurulumu (Service Account)

Service account, Python script'in Sheets'e erişmesi için gereken
"robot kullanıcı".

1. **Google Cloud Console**'a git: `https://console.cloud.google.com`
2. Yeni bir proje oluştur: "portfoy-dashboard-ozkan" (veya istediğin isim)
3. **APIs & Services → Library**:
   - "Google Sheets API"yi etkinleştir
   - "Google Drive API"yi etkinleştir
4. **APIs & Services → Credentials → Create Credentials → Service Account**:
   - Service account name: `sheets-reader`
   - Role: gerek yok (boş bırak)
   - Sonraki adımda **Key → Create New Key → JSON** seç → indir
5. İndirilen JSON dosyasının içeriğini sakla (GitHub Secrets'a koyacaksın).
   - Service account e-postası: `sheets-reader@portfoy-dashboard-ozkan.iam.gserviceaccount.com` formatında.

### 13.3 Google Sheets kurulumu

1. Yeni bir Google Sheets oluştur.
2. **Paylaşım:** Service account e-postasını "Görüntüleyici" yetkisiyle paylaş.
3. **Sekme 1: `Ozkan_Portfoy`** — sütunlar (A→D):
   ```
   A: Tip      B: Kod       C: Adet       D: Maliyet
   ```
4. **Sekme 2: `Derya_Portfoy`** — aynı sütunlar.
5. **Sekme 3: `TUFE`** — sütunlar:
   ```
   A: Ay (YYYY-MM)    B: Gerçekleşen (%)    C: Beklenti (%)
   ```

**Tip geçerli değerleri (§2):**
```
Hisse, Fon, AltinFonu, YurtdisiFonu, Emeklilik, Altin, Alacak, Nakit, Kripto
```

**Örnek satırlar (Ozkan_Portfoy):**
| Tip | Kod | Adet | Maliyet |
|---|---|---|---|
| Hisse | INFO | 100179 | 3,9 |
| Hisse | TRGYO | 3919 | 81,44 |
| Fon | ZBJ | 54470 | 2,22 |
| AltinFonu | HBF | 4515 | 29,8066 |
| YurtdisiFonu | TFF | 4855 | 26,76 |
| Emeklilik | HES | 1334608 | (boş) |
| Kripto | BTC | 0,065751 | 3631243 |
| Alacak | Anne | 135000 | (boş) |

**Örnek satırlar (Derya_Portfoy):**
| Tip | Kod | Adet | Maliyet |
|---|---|---|---|
| Hisse | INFO | 65327 | 3,9 |
| Emeklilik | FFC | 7299919 | (boş) |
| Altin | 24ayar | 301,86 | (boş) |

**Sheets ID:** URL'den çıkar:
`https://docs.google.com/spreadsheets/d/<SHEETS_ID>/edit`

### 13.4 GitHub repo kurulumu

1. GitHub'da yeni public repo oluştur: `pf-a7k9m3p2` (veya istediğin isim).
   - **Public olmalı** — GitHub Pages için.
   - Tehdit modeli düşük (şifre + obscure URL yeterli kabul edilmiş).

2. Repo'ya şu dosya yapısını kur:
   ```
   pf-a7k9m3p2/
   ├── CLAUDE.md                       (bu dosya)
   ├── index.html                       (frontend, ~1370 satır)
   ├── robots.txt                       (`User-agent: * \n Disallow: /`)
   ├── requirements.txt                 (Python paketleri)
   ├── prices.json                      (boş başlangıç: {})
   ├── portfoy.json                     (boş başlangıç: {"portfoyler":{"ozkan":[],"derya":[]}})
   ├── yilbasi_fiyatlari.json           (boş başlangıç: {})
   ├── .gitignore
   ├── scripts/
   │   ├── fiyat_guncelle.py
   │   └── benchmark_fiyat.py
   └── .github/
       └── workflows/
           ├── portfoy-guncelle.yml
           └── benchmark-guncelle.yml
   ```

3. **`requirements.txt`** içeriği:
   ```
   gspread==6.1.4
   google-auth==2.35.0
   yfinance==0.2.50
   borsapy==0.10.0
   requests==2.32.3
   pandas==2.2.3
   ```
   > `tefas-crawler` **YOK** (§12.6.2).

4. **`.gitignore`** içeriği (en azından):
   ```
   *.eski
   *.eski2
   *.eski3
   notes.md
   secrets.txt
   .claude/
   .preview_server.py
   ```

### 13.5 GitHub Secrets ayarları

Repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret adı | Değer |
|---|---|
| `GOOGLE_SHEETS_CREDENTIALS` | Service account JSON dosyasının tüm içeriği |
| `SHEETS_ID` | Google Sheets URL'sindeki ID |

### 13.6 GitHub Pages aktivasyonu

1. Repo → Settings → Pages
2. **Source:** "Deploy from a branch"
3. **Branch:** `main`, folder: `/ (root)`
4. Save
5. Birkaç dakikada `https://<github-username>.github.io/<repo-adı>/` URL'sinde yayında olur.

**Basit parola koruması:** `index.html` içinde `PASSWORD_HASH = "ozdege15"` (örnek). Bu profesyonel güvenlik değil, sadece arama motorlarından ve gelişigüzel görülmesinden korur (§10).

### 13.7 cron-job.org tetikleyicileri (opsiyonel ama önerilen)

GitHub Actions schedule cron'larının güvenilirliği için ek tetikleyici.
GitHub Actions schedule'ı bazen 30 dk gecikiyor; cron-job.org garanti tetik atıyor.

1. `https://console.cron-job.org` hesap aç.
2. **Personal Access Token (PAT) üret** — GitHub → Settings → Developer settings → Tokens → Fine-grained:
   - Repo permissions: `Actions: Read and write`
   - Geçerlilik: 1-2 yıl
   - Name: `cron-job-org-portfoy-tetikleyici`
3. cron-job.org'da yeni job:
   - **URL:** `https://api.github.com/repos/<github-username>/<repo>/actions/workflows/portfoy-guncelle.yml/dispatches`
   - **Method:** POST
   - **Header:** `Authorization: Bearer <PAT>`, `Accept: application/vnd.github+json`, `Content-Type: application/json`
   - **Body (intraday):** `{"ref":"main"}`
   - **Body (kapanış):** `{"ref":"main","inputs":{"kapanis":"true"}}`
   - **Schedule:** Pzt-Cum, TR saati:
     - Intraday: 10:30, 12:30, 14:30, 16:30
     - Kapanış: 18:35 (ayrı job)

### 13.8 İlk kurulum adımları (kritik sıra)

1. **Sheets paylaş** — service account'ı görüntüleyici olarak ekle.
2. **GitHub repo, secrets, Pages** ayarlarını tamamla.
3. **İlk benchmark çekimi** — Actions → "Benchmark Guncelleme" → "Run workflow":
   - **DİKKAT:** Dropdown'dan `gecmis: true` seç (§12.6.1 dersi!).
   - 5-10 dakikada `benchmark_gecmis.json` oluşur (5 yıllık seri).
4. **İlk portföy fiyat çekimi** — Actions → "Portföy Guncelleme" → "Run workflow":
   - Normal mod (intraday). `prices.json` ve `portfoy.json` dolar.
5. **Frontend kontrolü** — GitHub Pages URL'sinde dashboard açılmalı.

### 13.9 Doğrulama

- **portfoy.json**: `{"portfoyler":{"ozkan":[...], "derya":[...]}}` dolu mu?
- **prices.json**: USD, EUR, gram altın, hisseler dolu mu?
- **benchmark_gecmis.json**: 5 seri (bist100, amerika_hisse, gram_altin, yae, tufe) hepsi kayıt var mı?
- **GitHub Pages**: parola gir → dashboard 5 tab açılıyor mu?
- **Cron çalışıyor mu?** Birkaç saat sonra "Otomatik guncelleme" commit'leri repo log'unda görünmeli.

### 13.10 Bilinen sınırlamalar ve gözlemler

- **yfinance GitHub Actions'tan çalışmaz** (§12.6.3). Yedek olarak kalır ama beklemeden borsapy birincil olarak ayarlı.
- **tefas-crawler PyPI bozuk** (§12.6.2). borsapy.Fund() kullan.
- **TEFAS v2 API'de YAE'nin geçmişi sınırlı** — fon yaşı ya da API window'una bağlı. Şu an ~71 kayıt (3 ay).
- **TÜFE manuel** — kullanıcı her ay TÜİK rakamını Sheets'e ekler.
- **GitHub Actions schedule güvenilmez** — cron-job.org paralel sigorta.
- **Mac sandbox sınırlamaları** — Preview MCP ve `defaults write` çalışmaz; Bash kullan (§12.6.9).
- **Lokal sunucuyu HER ZAMAN ana repo dizininden başlat**, worktree'den değil (§12.6.9).

### 13.11 Hızlı referans — TEFAS fon kodları (Türk yatırımcı pratiği)

| Fon kodu | Tipi | Amaç |
|---|---|---|
| **AFA** | Amerika Hisse | S&P500 takipli (yaklaşık), benchmark birincil |
| **ABE** | Amerika Hisse | Benchmark yedek |
| **YAE** | Para Piyasası | Faiz benchmark'ı (ZBJ portföy kalemi için) |
| **HBF** | Altın Fonu | Portföy kalemi |
| **NAU** | Altın Fonu | Portföy kalemi |
| **TFF** | Yurt Dışı Hisse | Portföy kalemi |
| **MPP** | Yurt Dışı Hisse | Portföy kalemi |
| **ZBJ** | Para Piyasası | Portföy kalemi |
| **HES** | Emeklilik (BES) | Portföy kalemi |
| **AJR** | Emeklilik (BES) | Portföy kalemi (Özkan) |
| **FFC** | Emeklilik (BES) | Portföy kalemi (Derya) |

### 13.12 Hızlı referans — BIST hisse kodları (portföydeki)

| Kod | Şirket |
|---|---|
| INFO | İnfo Yatırım |
| TRGYO | Torunlar GYO |
| SAHOL | Sabancı Holding |

### 13.13 Tasarım kararları (NEDEN böyle?)

- **Tek HTML dosyası (no build step)**: dağıtım kolaylığı, GitHub Pages'a statik yükle.
- **Chart.js CDN**: ek build tooling yok, sayfa hızlı yüklenir.
- **CSS dark theme + 5 tab sidebar**: modern fintech estetiği (CLAUDE.md §5.6).
- **Tüm hesap frontend'de**: backend sadece raw veri sağlar, frontend hesap ve render yapar. Bu sayede ihtiyaca göre frontend güncellemesi yeterli, backend'e dokunulmaz.
- **Privacy modu**: kullanıcı ekran paylaşırken portföy büyüklüğünü gizler. Yüzdeler ve oranlar gösterilir, mutlak rakamlar normalize edilir.
- **gecmis.json milat tarihi**: 21 Mayıs 2026'dan önce kayıt yok (sistem o zaman tasarlandı). Geçmiş verilerle backfill yapılmaz — sadece ileriye doğru kayıt tutulur.
- **borsapy birincil yfinance yedek**: ana script `fiyat_guncelle.py`'de kanıtlanmış pattern; benchmark da aynı pattern'e geçirildi.

### 13.14 Felaket senaryoları

**Senaryo 1: Repo silindi**
- Lokal kopya: `~/Documents/pf-a7k9m3p2/`. Buradan tekrar push.
- GitHub Secrets manuel yeniden gir.
- GitHub Pages tekrar aktif et.

**Senaryo 2: Google Sheets silindi**
- Yeniden oluştur (§13.3).
- Service account ile paylaş.
- `SHEETS_ID` secret'ı güncelle.

**Senaryo 3: Service account silindi/kapatıldı**
- Yeni service account oluştur (§13.2).
- JSON'u yeni Sheets'le paylaş.
- `GOOGLE_SHEETS_CREDENTIALS` secret'ı güncelle.

**Senaryo 4: borsapy çalışmıyor**
- Script otomatik yfinance'a düşer (genelde GitHub Actions'tan çalışmaz, ama lokal'de çalışır).
- O da olmazsa TCMB anlık kuru (tek nokta, geçmiş yok).
- Hisse/fon için manual fallback yok — script o satırı `fiyat_eksik: true` ile işaretler, dashboard "—" gösterir.

**Senaryo 5: Cron çakışması/lock dosyası**
- Bkz §12.6.10 acil kurtarma.

**Senaryo 6: AFA fonu kapatıldı/değişti**
- `scripts/benchmark_fiyat.py` → `amerika_hisse_seri()` → birincil kod değişir.
- `benchmark_gecmis.json` üzerine yazılır (manuel `gecmis=true` tetik gerekir).
- Tüm kullanıcılar için aile vurgu rengi/etiket değişebilir (frontend).

### 13.15 Bu dosyanın kendi felaketi

Eğer **CLAUDE.md silinirse**:
- GitHub commit history'den herhangi bir versiyonu geri al.
- En kapsamlı versiyon: §13'lü versiyon (commit hash'i §12.11'de).
- Bağımsız bir AI bu dosyayı okuyup tüm sistemi sıfırdan kurabilir.

---

## 14. 20 MAYIS 2026 — MİLAT ÖNCESİ DEFANS PAKETİ

**Amaç:** 21 Mayıs milat günü `gecmis.json`'a ilk snapshot düşmeden önce
oluşabilecek hataları kapatmak. İki commit, iki farklı koruma katmanı.

### 14.1 TEFAS transient hata → snapshot koruma (3. yedek katman)

**Olay:** 20 Mayıs 12:31 cron'unda TEFAS API geçici hata verdi. AJR, HBF,
HES, ZBJ fonları çekilemedi. Mevcut script bu durumda ilgili alanları
`null` yazıyordu. Frontend'de `enrichItem()` içindeki
`tg = guncel_tl ?? tm` fallback'i maliyet × adet'ten hesap yapıyordu.
Sonuç: HBF gerçek ~228k TL yerine maliyet × adet = 134k TL gösterdi.
HES ve AJR maliyet null olduğu için 0 TL göründü.

**Ne yapıldı (`scripts/fiyat_guncelle.py` — `tefas_fiyat_toplu`):**

3. yedek katman eklendi. Yedek katman sırası artık:

| Sıra | Kaynak | Tetik |
|---|---|---|
| 1 (birincil) | tefas-crawler (import varsa) | her zaman önce denenir |
| 2 (yedek 1) | borsapy `Fund(kod)` | birincil çekemediklerini kapatır |
| 3 (yedek 2, yeni) | `prices.json` snapshot (son bilinen fiyat) | ikisi de başarısız olursa |

3. yedek çalışırken: eski `guncel` hem `guncel` hem `onceki` yapılır →
günlük değişim 0 görünür ama tutar mantıklı kalır. `kaynak` alanına
`"onceki_snapshot"` yazılır. Bir sonraki başarılı cron'da gerçek fiyat
üzerine yazılır, her şey düzelir.

**Frontend (`index.html` — tablo toplamları):**
Hisseler, YurtdışıFon, Fon, AltınFonu, Emeklilik ve Altın tablolarının
TOPLAM satırında "Günlük ₺" sütununun yanında boş bırakılan hücreye
**günlük % rozeti** eklendi. Hesap:

```
t_gp = (t_gk / (blokTop - t_gk)) × 100
```

Pozitif → yeşil `+%x,xx`, negatif → kırmızı, sıfır → nötr.
Hisseler tablosunda `hisseTop` ve `t_gk`, fon bloklarında `blokTop` ve
`t_gk`, altın tablosunda `altinTop` ve `t_gk` kullanılır.

**Commit:** `b07caff`

### 14.2 gecmis_kaydet defansif fix — eksik kalem varsa snapshot atla

**Sorun:** Kapanış cron'u (18:35) çalışırken TEFAS API hâlâ hata
veriyorsa, 3 yedek katman da başarısız olabilir ve bazı kalemlerin
`guncel_tl` alanı `None` kalabilir. Önceki `gecmis_kaydet()` bu durumu
kontrol etmiyordu: eksik kalemler `None` → `0.0` gibi davranıp kategoriye
yanlış toplam yazabilirdi. `gecmis.json`'da kalıcı bozuk satır kalırdı.

**Milat için kritik:** 21 Mayıs 2026 ilk snapshot ya doğru düşmeli ya da
hiç düşmemeli — yanlış kayıt kabul edilemez.

**Ne yapıldı (`scripts/fiyat_guncelle.py` — `gecmis_kaydet`):**

`_kisi_toplam()` yardımcı fonksiyonu `_eksikler` listesi döndürecek
şekilde genişletildi. Her portföy satırı taranır; `guncel_tl is None`
olan kalemler `_eksikler`'e eklenir, toplamdan çıkarılır.

Ardından yeni **defansif kontrol** eklendi:

```python
tum_eksikler = ozkan_t["_eksikler"] + derya_t["_eksikler"]
if tum_eksikler:
    log(f"GECMIS ATLANDI: {bugun} icin {len(tum_eksikler)} kalem fiyat eksik.", "ERROR")
    # ... detay logları
    return False   # snapshot YAZILMAZ
```

Snapshot atlanınca log'a `[ERROR]` düşer. Kullanıcı veya bir sonraki
cron farkeder. Manuel kurtarma: Actions → "Portföy Fiyat Guncelleme" →
"Run workflow" → `kapanis: true`. TEFAS o anda veri yayınladıysa
snapshot başarıyla düşer.

**Commit:** `7c346c1`

### 14.3 Öğrenilen dersler (20 Mayıs)

**14.3.1 — TEFAS transient hataları beklenmeli, savunma zorunlu:**
TEFAS API gün içinde birkaç dakikalık kesinti verebiliyor. Hisse ve
benchmark için anlık veri yokluğu tolere edilebilir (dashboard "—"
gösterir); ama gecmis.json için yanlış yazılmış kalıcı kayıt ileride
grafikleri bozar. İki ayrı savunma katmanı birbirini tamamlıyor:
- `tefas_fiyat_toplu`'da snapshot koruması → intraday cron'larda
  dashboard tutarlı kalır.
- `gecmis_kaydet`'te eksik kalem kontrolü → kapanış cron'unda bozuk
  kayıt kalmasını engeller.

**14.3.2 — `kaynak_durumu` alanını ileride izle:**
`prices.json.kaynak_durumu` içinde her fon için hangi kaynaktan
çekildiği yazılıyor (`"borsapy"`, `"onceki_snapshot"` vb.).
Frontend bu alana bakıp "⚠️ Bazı veriler gecikebilir" uyarısı
gösterebilir (v2 önerisi).

**14.3.3 — Defansif kod `_eksikler` alanını dışarı sızdırmamalı:**
`gecmis_kaydet`'e gönderilecek `ozkan` ve `derya` dict'lerinden
`_eksikler` key'i çıkarılmalı (kodda yapıldı: `{"kategoriler":...,
"toplam":...}` şeklinde yeniden paketleniyor). Yoksa gecmis.json'a
`_eksikler: []` yazılır, şema bozulur.

**14.3.4 — `.gitignore`'da `gecmis.json` ölümcül tuzak (22 Mayıs bug):**
Milat tarihi (21 Mayıs) öncesinde dosya henüz yokken `.gitignore`'a
`gecmis.json` satırı yazılmıştı. 21 ve 22 Mayıs kapanış cron'larında
script dosyayı başarıyla yazdı (`[INFO] Gecmis: ... snapshot
kaydedildi`), ama `git add -A` adımı `.gitignore` nedeniyle dosyayı
atladı — `gecmis.json` hiç commit'lenmedi. GitHub Actions runner her
çalıştırmadan sonra imha edildiği için, yazılan dosya kaybolmuş gibi
oldu, bir sonraki cron'da fresh checkout yapıldı, kısır döngü tekrar.
- **Sebep:** `.gitignore`, **tracked dosyaları görmezden gelmez** ama
  henüz tracked olmayanları (örn. milat günü ilk kez yaratılan
  `gecmis.json`) atlar. Aynı listede olan `prices.json`, `portfoy.json`,
  `yilbasi_fiyatlari.json` ise zaten tracked olduğu için sorun çıkarmadı.
- **Çözüm:** `.gitignore`'dan `gecmis.json` satırı silindi. Diğerleri
  zararsız olduğu için bırakıldı, ama satırlara uyarı yorumu eklendi
  ("ASLA gecmis.json'i buraya ekleme").
- **Kurtarma:** 21 ve 22 Mayıs kapanış commit'lerinde portfoy.json
  mevcut olduğu için (ce65dcd ve 636d499), bu commit'lerden veri çıkarılıp
  `gecmis_kaydet` mantığı lokal simüle edilerek `gecmis.json`
  retrospektif olarak oluşturuldu (iki gün için tam doğru kayıtlar).
- **Doktrin:** Cron'da yazılması beklenen veri dosyalarını **ASLA**
  `.gitignore`'a yazma — milat öncesi yokken zararsız görünse bile,
  ilk yazıldığı an gizlice commit dışı kalır.

### 14.4 Şu anki durum (22 Mayıs 2026 gece — güncel)

✅ **Tamamlandı:**
- TEFAS transient hata → prices.json snapshot koruması (3. yedek katman)
- Tablo TOPLAM satırları günlük % rozeti
- gecmis_kaydet defansif fix (eksik kalem varsa atla)
- **`.gitignore` `gecmis.json` bug fix + 21+22 Mayıs retrospektif
  snapshot kurtarma (22 Mayıs akşamı, §14.3.4)**

📊 **gecmis.json durumu:**
- 2026-05-21: 8.591.562 TL (Özkan 4.78M, Derya 3.81M) — HES Özkan'da
- 2026-05-22: 7.428.626 TL (Özkan 3.63M, Derya 3.80M) — Özkan'dan HES
  çıkarılmış, FFC eklenmiş (Sheets'te yapısal değişiklik)

### 14.5 Sonraki yapılacaklar (20 Mayıs güncellemesiyle değişen öncelikler)

§12.10'daki liste geçerliliğini koruyor. Ek notlar:

1. **21 Mayıs kapanış sonrası doğrulama** — `gecmis.json` oluştuysa
   Actions log'unda `[INFO] Gecmis kaydedildi: 2026-05-21` mesajı
   görünmeli. Görünmüyorsa `[ERROR] GECMIS ATLANDI` loguna bak.
2. **`kaynak_durumu` frontend uyarısı** (v2) — snapshot yedek devredeyse
   kullanıcıya bilgi notu göster (§14.3.2).

### 14.6 Önemli commit'ler (20–22 Mayıs)

- `b07caff` — TEFAS snapshot yedeği + tablo TOPLAM günlük % rozeti (20 May)
- `7c346c1` — gecmis_kaydet defansif fix (eksik kalem varsa atla) (20 May)
- `9d8ab7c` — CLAUDE.md §14 eklendi (20 May gece)
- **(22 May)** — `.gitignore` `gecmis.json` satırı silindi + retrospektif
  `gecmis.json` (21+22 Mayıs) + CLAUDE.md §14.3.4 dersi eklendi
