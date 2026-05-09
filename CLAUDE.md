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
| Altin | `24ayar` | gram | boş | TCMB / canlı altın |
| Alacak | serbest etiket | TL tutar | boş | sabit (TL) |
| Nakit | `TL`/`USD`/`EUR` | birim sayısı | boş | yfinance kuru |
| Kripto | `BTC` vb. | adet | TL maliyet | Yahoo Finance × USDTRY |

**Maliyet boşsa:** kazanç yüzdesi hesaplanmaz, sadece güncel TL değer ve
zaman içindeki TL değişim gösterilir.

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

**Tatil/hafta sonu kuralı:** Kapanış görevi cron olarak Pzt-Cum çalışır.
Tatil günleri için akıllı kontrol: "Bugün tarihte kayıt var mı?" → varsa
atla.

---

## 4. BENCHMARK SETİ

| Benchmark | Amaç | Kaynak |
|---|---|---|
| BIST100 | Hisse karşılaştırması | yfinance (`XU100.IS`) |
| S&P500 (TL) | Yurtdışı hisse karşılaştırması | yfinance × USDTRY |
| Gram Altın | Altın varlıkların karşılaştırması | TCMB / canlı altın |
| YAE fonu | Faiz / para piyasası karşılaştırması (ZBJ için) | tefas-crawler |
| TÜFE | Reel getiri (1 ay+ kıyaslamalar) | TÜİK; yoksa MB PKA |

**Karşılaştırma türü:** sadece **% getiri** (mutlak değer değil).

---

## 5. DASHBOARD YAPISI

**Sidebar tabları (4 adet):**
1. Özkan
2. Derya
3. Genel (Aile)
4. Benchmark

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
- **Sağ üst:** Veri Güncelle butonu (manuel yenileme)
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

## 7. ACİL DURUM — LOCK BUG (referans)

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

## 8. GÜVENLİK NOTU

- Repo public (GitHub Pages için).
- Site şifresi sadece HTML içinde basit koruma; hassas veri JSON'larda.
- Bu bilinçli bir tercih (kişisel kullanım, tehdit modeli düşük).
- **Bu dosyaya ASLA yazılmaz:** şifreler, token'lar, Sheets ID,
  service account key, kişiyle özdeşleşen tutarlar.
