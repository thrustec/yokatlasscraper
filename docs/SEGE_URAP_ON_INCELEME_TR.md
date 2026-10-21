# SEGE ve URAP veri botları: kaynak incelemesi ve uygulama önerisi

İnceleme tarihi: 19 Ekim 2026. Bu belge kaynak keşfi, örnek veri çıkarımı ve mevcut bot mimarisiyle entegrasyon önerisidir. Yeni bot, migration, sunucu kurulumu veya üretim verisi aktarımı yapılmadı.

## 1. Önerilen ilk kapsam

Mevcut panelde iki ayrı bot önerilir: `sege` ve `urap`. Aynı çalıştırma, durdurma, log, ilerleme ve yeniden deneme sözleşmesini kullanırlar; kaynak okuma yöntemleri farklı olur.

İlk sürümde SEGE'nin 2025 il sonuçları, sekiz alt boyut sıralaması, 2022 ilçe sonuçları ve URAP'ın 2025-2026 Türkiye genel sıralaması alınabilir. SEGE Düzey-2 bölgeleri ile URAP alt grupları yakın genişletme; URAP Dünya ve bilim alanları ise sonraki kapsam olabilir. Bunların kaynakları da bu incelemede kontrol edildi.

## 2. SEGE: erişim ve çıkarılabilir alanlar

Sanayi ve Teknoloji Bakanlığının güncel kaynak sayfası il düzeyinde 2025, ilçe düzeyinde 2022 çalışmalarını gösteriyor. İl raporu 81 il ve 52 değişkeni, ilçe raporu 973 ilçe ve 56 değişkeni kapsıyor. İl raporunda ayrıca 26 Düzey-2 bölgesi bulunuyor.

SEGE'nin yıllık ve düzenli yayın takvimi varsayılmamalı. Rapor yılı, göstergelerin referans yılları ve botun indirme tarihi ayrı tutulmalı. Örneğin İl SEGE-2025 değişken listesinde 2024 nüfus yoğunluğu, 2019-2023 net göç hızı ve 2023 eğitim verileri birlikte kullanılıyor.

| Veri grubu | Çıkarılabilecek alanlar | Belgede konum |
|---|---|---|
| İl genel sonuçları | İl adı, Türkiye sırası, endeks/skor, 1-6 gelişmişlik kademesi | İl 2025, Tablo 12, basılı s.35 / PDF s.47 |
| İl alt boyutları | Demografi, istihdam, eğitim, sağlık, rekabetçi ve yenilikçi kapasite, mali, erişilebilirlik, yaşam kalitesi sıraları | Tablo 20, basılı s.74-75 / PDF s.86-87 |
| Düzey-2 bölgeleri | Bölge kodu, kapsadığı iller, bölge skoru, sırası, 1-4 kademesi | Tablo 21, basılı s.77 / PDF s.89 |
| İlçe genel sonuçları | İl, ilçe, Türkiye sırası ve skor | İlçe 2022, Ek-1, basılı s.70-84 / PDF s.42-49 |
| İlçe il içi sonuçları | İl, ilçe, Türkiye sırası, il içindeki sıra, skor, kademe | Ek-2, basılı s.85 ve sonrası / PDF s.49 ve sonrası |
| Gösterge sözlüğü | Değişken adı, ait olduğu boyut, veri sağlayan kurum, referans yılı/aralığı ve birim | Her iki rapordaki değişken listeleri |
| Yöntem bilgileri | Temel bileşen ağırlıkları, açıklanan varyans, kademe dağılımları | Yöntem ve analiz tabloları |

**Önemli sınır:** 52 ve 56 gösterge kullanılması, PDF'lerin tüm il/ilçeler için bu göstergelerin ham değer matrisini yayımladığı anlamına gelmiyor. İncelenen raporlarda bütün yerleşimler için böyle bir ham matris bulunmadı. Gösterge tanımları, kaynak/yıl/birim bilgileri, ağırlıklar ve anlatı içinde seçilmiş sayısal örnekler mevcut. İl alt boyut tablosu da boyutların **sıralarını** veriyor; bu değerler boyut puanı veya ham gösterge değeri diye kaydedilmemeli. Ham göstergeler gerekirse ilgili kurumdan ayrı veri akışıyla alınmalı; SEGE skoru bu göstergelerden geriye doğru üretilmemeli.

### Gerçek dosyalarda yapılan çıkarım kontrolü

- İl 2025 PDF'i 113 sayfa. `pdfplumber` ile Tablo 12'den 81 satır çıkarıldı; 1-81 sıra kümesinin eksiksiz ve benzersiz olduğu kontrol edildi.
- Aynı PDF'in Tablo 20'sinden 81 il için alt boyut satırı, Tablo 21'den 26 bölge satırı çıkarıldı.
- İlçe 2022 dosyası 71 fiziksel PDF sayfası; pek çok sayfada iki basılı sayfa yan yana. Ek-1'den 973 satır çıkarıldı; 1-973 sıra kümesinin eksiksiz ve benzersiz olduğu kontrol edildi.
- İlçe Ek-2'nin Adana ve Adıyaman tablolarında il içi sıra ve kademe alanları görüldü; Ek-2'nin tamamı bu ön incelemede ayrıştırılmadı.
- Temsilî tablolar görüntü olarak render edilip sütun yapılarıyla karşılaştırıldı. OCR bu tablolar için gerekmedi. Salt metin çıkarımı bazı adlarda harf aralığı ve gizli metin sorunları üretiyor; hücre/sayfa konumunu kullanan tablo çıkarımı daha uygun.

Örnekler: İl 2025 İstanbul → sıra 1, skor 4,419, kademe 1. İlçe 2022 Şişli/İstanbul → sıra 1, skor 6,959; Seyhan/Adana → Türkiye sırası 42, il içi sıra 1, skor 2,043, kademe 1. Bunlar farklı coğrafi kapsamların endeksleri; skorları birbirine denk kabul edilmemeli.

Bakanlık ana sayfasının bazı doğrudan istekleri `Request Rejected` yanıtı verdi. Bakanlığın Kalkınma Kütüphanesindeki kamuya açık dosyalar indirilebildi. Bot, HTML hata sayfasını PDF sanmamalı; dosya imzasını ve içeriğini kontrol etmeli. Erişim kesilirse resmî dosyanın panelden seçilmesi/yerel dosya olarak verilmesi aynı ayrıştırma sürecini başlatabilmeli. Rapor sürümleri, dosya bağlantıları zaman içinde değişebileceği için keşfedilmeli.

## 3. URAP: üç farklı veri ailesi

19 Ekim 2026 incelemesinde Türkiye sitesinin dönem menüsünde en yeni dönem **2025-2026** idi. 2026-2027 dönemi doğrulanmadı. Aynı dönem etiketine sahip Türkiye, Dünya genel ve Dünya alan yayınları farklı tarihlerde açıklanıyor; tek bir yayın tarihi varsayılmamalı.

### Türkiye sıralaması

Canlı genel tabloda 198 üniversite, ilk sayfada 10 kayıt ve aşağıdaki alanlar görüldü:

- Sıra, üniversite adı, şehir ve üniversitenin web bağlantısı.
- Makale, atıf, bilimsel doküman, doktora, öğretim üyesi/öğrenci, uluslararası işbirliği, yurtiçi işbirliği ve TÜBİTAK proje puanı.
- Toplam puan ve tablonun 2025-2026 dönem kimliği.

2025-2026 Türkiye yönteminde 15 gösterge tanımlanıyor; yayımlanan genel tablo bunları sekiz puan sütununda topluyor. **Puan, ham yayın/proje/öğrenci sayısı değildir.** Örneğin Makale Puanı alanı makale adedi olarak kullanılmamalı. Mevcut tabloyu almak, Clarivate/InCites veya YÖK kaynaklarındaki ham veri setine erişim sağlamaz.

Türkiye alt grup sayfasında devlet, vakıf, tıp fakültesi olan, tıp fakültesi olmayan, 2000 yılından önce kurulan, 2000 yılından sonra kurulan ve 6000'den az öğrencili üniversiteler için tablolar mevcut. Alt grubun sırası genel Türkiye sırasından ayrı saklanmalı.

Türkiye PDF'inde Tablo 10 genel sıralamayı ve bileşen puanlarını, Tablo 11 ise önceki döneme göre sıra değişimini veriyor. Geçmiş dönemler kendi tablolarından alınırsa değişim ayrıca hesaplanabilir. Kapsam, kurum kimliği ve yöntem değişiklikleri de korunmalı; yeni giren üniversiteye önceki yıl için sıfır sıra verilmemeli.

### Dünya genel sıralaması

19 Haziran 2026 tarihli 2025-2026 Dünya basın bildirisinde 3000 üniversite ve altı gösterge açıklanıyor: makale, atıf, toplam doküman, toplam yayın etkisi, toplam atıf etkisi ve uluslararası işbirliği. Üniversite/ülke/dönem, dünya sırası, toplam ve bileşen puanları hedeflenebilir. Dünya genel tablosunun tamamı bu ön incelemede dışa aktarılmadı.

### Dünya bilim alanı sıralamaları

2025-2026 alan bildirisinde 78 bilim alanı bulunuyor. Canlı alan listesi ve `Information & Computing Sciences` tablosu kontrol edildi. Örnek tabloda 750 kayıt; üniversite, ülke, sıra, altı bileşen ve toplam puan var. Alan başına kayıt sayısı değişebilir. Bildiri eklerinde Türk üniversitelerinin ilgili alandaki Türkiye ve Dünya sıraları da bulunuyor.

Alan sıralamaları üniversitenin ilgili bilim alanındaki araştırma performansını gösterir. Bunlar doğrudan bir lisans programının eğitim, istihdam veya öğrenci memnuniyeti sıralaması değildir. URAP alanı ile YÖKAtlas program grubu eşlemesi gerekiyorsa ayrı ve gözden geçirilmiş bir ilişki kurulmalı.

### Bot için erişim tercihi

Canlı Türkiye genel tablosunda ve örnek Dünya alan tablosunda `Export to Excel` düğmesi mevcut. Uygulamanın kamuya açık JavaScript kodunda Excel aktarımı tüm sayfalara yönelik yapılandırılmış. Ancak bu oturumdaki otomatik indirme denemesi tamamlanmadığı için oluşan Excel dosyasının satır kapsamı doğrulanmadı.

Site Meteor ile veriyi sonradan yüklüyor; basit HTTP GET yalnızca uygulama kabuğunu getiriyor. İncelenen istemci kodunda sıralama verisi ve şablonları için abonelikler bulunuyor. Bu gözlem, belgelenmiş ve kalıcı bir REST API sözleşmesinin doğrulandığı anlamına gelmez.

İlk teknik denemede şu sıra izlenmeli:

1. Sayfanın kullandığı kamuya açık yapılandırılmış verinin eksiksiz ve tekrarlanabilir okunup okunmadığını kontrol et.
2. Uygunsa bu veriyi ham olarak arşivle; uygun değilse resmî Excel aktarımını otomatikleştir.
3. Excel erişimi veya kapsamı sorunluysa tüm sayfalardaki tabloyu oku; Türkiye raporunun PDF'ini yedek kaynak ve çapraz kontrol olarak kullan.
4. Tercih edilen yöntemde 198 satırın tamamını ve PDF ile örnek satır uyumunu doğrula. Ekrandaki ilk 10 satırı tam veri sayma.

## 4. Mevcut mimariye entegrasyon

Mevcut `scraper.panel_tuik` ve `scraper.panel_yokatlas`, `botkit` ile panelin çalışma sözleşmesine bağlı. Yeni giriş noktaları örneğin `scraper.panel_sege` ve `scraper.panel_urap` olabilir. Bunlar önerilen adlar; henüz oluşturulmadı. Zamanlamayı panel yönetmeli; aynı işi yöneten ikinci bir sürekli döngü eklenmemeli.

```text
Kaynak/yayın keşfi
    → Orijinal PDF / Excel / yapılandırılmış yanıt + dosya manifesti
    → Sürüme uygun ayrıştırıcı
    → Geçici tablolar + kimlik eşleme + kalite kontrolleri
    → Eksiksiz yayın sürümünü etkinleştirme
    → api görünümleri → site
```

### Arşiv ve sürümleme

Mevcut `raw.api_responses.payload` alanı JSONB. PDF ve Excel'in orijinal dosyalarını arşivde/dosya deposunda tutmak, veritabanında dosya kaydını ve bağlantısını saklamak uygun olur. Ayrıştırılmış JSON, orijinal dosyanın yerine geçmemeli.

Önerilen belge kaydı: kaynak sistemi, veri ailesi, rapor/dönem kimliği, yayın tarihi, kaynak URL'si, alınma zamanı, dosya SHA-256 değeri, arşiv konumu ve ayrıştırıcı sürümü. Satırın kaynak PDF sayfası/tablosu veya Excel sayfa/satır konumu da korunmalı. Aynı dosyayı tekrar işlemek mükerrer gözlem üretmemeli; yeni ayrıştırıcıyla tekrar işleme mümkün olmalı.

Önerilen mantıksal veri grupları: `source_documents`, `source_releases`, `sege_province_results`, `sege_province_dimension_ranks`, `sege_district_results`, `sege_region_results`, `urap_rankings`, `urap_indicator_scores` ve kaynak adlarını sistem kimliklerine bağlayan eşleme tablosu. Fiziksel tablo adları ve şemalar mevcut migration düzenine göre belirlenir; gereksiz kopya tablolar açılmamalı.

SEGE anahtarı rapor sürümü + coğrafi düzey + yerleşim kimliğidir. URAP anahtarı dönem/yayın sürümü + sıralama ailesi + grup/alan + üniversite kimliğidir. Sıra numarası kayıt kimliği olarak kullanılmamalı.

### Kimlikleri bağlama

- İl sonuçları mevcut `core.cities.il_kodu` ile eşlenebilir; raporun il adı ve kaynak kodu korunmalı, kod standardı doğrulanmalı.
- URAP üniversiteleri `core.universities.universite_id` ile eşlenmeli. Türkçe/İngilizce adlar, eski adlar, bölünmeler ve bağımsız kurumlar için alias kaydı gerekli. İstanbul Üniversitesi ve İstanbul Üniversitesi-Cerrahpaşa birleştirilmemeli. Eşleşmeyen kurumlar ham kayıttan düşürülmemeli.
- İlçe raporunda isimler var; salt `Merkez` veya `Gölbaşı` ile eşleme yapılamaz. İl + ilçe birlikte kullanılmalı. Mevcut STAGING'deki ilçe alanlarının kod sistemi kontrol edilmeli; mevcut CORE şemasında ilçe referans tablosu bulunmadığından açık bir ilçe eşleme/referans düzeni gerekir.
- Programın bulunduğu kampüs/ilçe doğrulanmadan üniversitenin merkez adresinden bütün programlara ilçe SEGE skoru taşınmamalı.

### Kalite ve yayın davranışı

Kaynak dosya sürümü bazında kapsam kontrolü yapılmalı: İl 2025 için 81 il, sekiz boyut satırında 81 il, bölgelerde 26 kayıt; İlçe 2022 için 973 ilçe; URAP Türkiye 2025-2026 genel tablosunda 198 üniversite. Sonraki raporlarda sayıların aynı kalacağı varsayılmamalı; beklenen kapsam kaynağın yayın bilgisinden alınmalı.

Kontroller: yinelenen anahtarlar, sıra kapsamı, 1-6 il/ilçe ve 1-4 bölge kademeleri, il/üniversite eşleşmeleri, negatif SEGE skorları, Türkçe karakterler, nokta/virgül ondalıkları, boş hücre ile gerçek sıfırın ayrımı. Kaynağın kendi verdiği sıra esas alınmalı; yuvarlanmış eşit skorlar tekrar sıralanarak değiştirilmemeli. URAP'ta toplam-bileşen kontrolü gösterilen hassasiyet ve yuvarlamaya uygun tolerans kullanmalı.

Yeni sürüm eksik veya hatalıysa mevcut yayımlanmış sürüm görünür kalmalı. Kontrolü geçen tam yayın tek işlemle etkinleştirilmeli. Bu, mevcut YÖKAtlas aktarımındaki kısmi görünürlük sınırına ek bir davranış gerektirir; mevcut botların zaten bu kapıya sahip olduğu varsayılmamalı.

Site, SEGE 2025'i 2026 verisi diye etiketlememeli. Güncel profil için son mevcut rapor kullanılabilir; tarihsel analizde ise sorgu tarihine kadar yayımlanmış son rapor seçilmeli. Sonraki yıllara yapay SEGE gözlemi yazılmamalı. Farklı raporların yöntem/gösterge setleri değişebildiğinden puan farkı otomatik olarak gelişmişlik artışı yüzdesine çevrilmemeli.

## 5. Uygulama sırası ve kabul koşulları

1. **Veri sözleşmesi:** İlk sürümün alanlarını, rapor kimliklerini, isim eşlemelerini ve site üzerinde gösterilecek etiketleri kesinleştir. Çıktı: alan sözlüğü ve örnek kayıtlar.
2. **SEGE ayrıştırıcı denemesi:** Mevcut çıkarımı tekrarlanabilir modüle dönüştür; Ek-2'nin tamamını da işle. Çıktı: il ve ilçelerde bütün temel alanları kapsayan, kaynağa geri izlenebilen kayıtlar.
3. **URAP erişim denemesi:** Yapılandırılmış veri/Excel yolunu seç; tüm 198 kayıtla çalıştığını kanıtla. Çıktı: tablo-PDF örnek karşılaştırması ve kapsam kontrolü.
4. **Veritabanı ve API:** Dosya kaydı, yayın sürümü, typed veri tabloları, eşleme ve api görünümlerini migration ile ekle. Aynı girdiyi tekrar yükleme ve önceki sürümü koruma davranışını doğrula.
5. **Panel entegrasyonu:** İki botu mevcut runner'a bağla. Yeni yayın kontrolü, seçilen raporu aktarma, yerel dosyadan aktarma, log/ilerleme, durdurma ve başarısızları yeniden deneme sunulsun. İlk kurulum elle çalışsın.
6. **İşletim:** Ardından panelde haftalık kaynak kontrolü önerilir. SEGE'de yeni dosya veya içerik hash'i yoksa aktarım yapılmaz. URAP'ta Türkiye, Dünya ve alan yayınları ayrı izlenir. Bağlantı değişimi, şema değişikliği ve eksik aktarım görünür hata üretir.
7. **Geçmiş kapsam:** Güncel veriler doğru çalıştıktan sonra SEGE 2017 ve önceki URAP dönemleri, kendi şema/yöntem sürümleriyle eklenir.

İlk sürümün kabul koşulu yalnızca dosya indirmesi değildir: tam kapsam, doğru kimlik bağlantıları, kaynağa izlenebilirlik, mükerrer kayıt üretmeyen tekrar çalışma, hatada eski sürümün korunması ve site üzerinden doğru dönem etiketiyle okunması birlikte gösterilmeli.

## Kaynaklar ve yerel kanıt

- [Bakanlık SEGE kapsam ve güncel dönem sayfası](https://www.sanayi.gov.tr/merkez-birimi/b94224510b7b/sege/il-sege-)
- [Kalkınma Kütüphanesi İl SEGE-2025 kaydı](https://www.kalkinmakutuphanesi.gov.tr/dokuman/il-sege-2025/3062)
- [İl SEGE-2025 PDF](https://www.kalkinmakutuphanesi.gov.tr/assets/upload/dosyalar/l-sege-2025.pdf)
- [İlçe SEGE-2022 PDF](https://www.kalkinmakutuphanesi.gov.tr/assets/upload/dosyalar/2022-ilce-sege.pdf)
- [URAP Türkiye 2025-2026 genel tablo](https://newtr.urapcenter.org/Rankings/2025-2026/GENEL-SIRALAMASI-2025)
- [URAP Türkiye alt grupları](https://newtr.urapcenter.org/Rankings/2025-2026/fields)
- [URAP Türkiye 2025-2026 raporu](https://newtr.urapcenter.org/cdn/storage/PDFs/mezDn2uAd4mx2mZzW/original/mezDn2uAd4mx2mZzW.pdf)
- [Güncel bağlantıdan URAP Dünya 2025-2026 bildirisi](https://newtr.urapcenter.org/cdn/storage/PDFs/JwPk6FZjbjfBrSCDF/original/JwPk6FZjbjfBrSCDF.pdf)
- [URAP Dünya 2025-2026 alan bildirisi](https://newtr.urapcenter.org/cdn/storage/PDFs/h6D89jKndewzfZYLE/original/h6D89jKndewzfZYLE.pdf)
- [URAP Dünya alan listesi](https://urapcenter.org/Rankings/2025-2026/fields)
- [İncelenen örnek bilim alanı](https://urapcenter.org/Rankings/2025-2026/2026-Information_and_Computing_Sciences)

Yerel kaynak dosyaları ve sayfa görüntüleri `outputs/sege_urap_research/` altında. `extraction_evidence.json`, denemede çıkarılmış SEGE satırlarını, kapsam kontrollerini ve indirilen üç PDF'in SHA-256 değerlerini içeriyor. Bu dosyalar mevcut `.gitignore` gereği Git dışındadır. Kanıt JSON'u üretim veri seti veya kurulmuş bir bot olarak değerlendirilmemeli.

Mevcut mimari için incelenen yerel dosyalar: `docs/backend/ADMIN_PANEL_BOTS_TR.md`, `scraper/README.md`, `scraper/panel_tuik.py`, `database/migrations/001_data_contract_v1.sql` ve `database/migrations/006_tuik_population_by_province.sql`.
