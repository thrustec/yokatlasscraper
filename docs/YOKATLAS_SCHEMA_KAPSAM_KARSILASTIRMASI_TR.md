**YÖK Atlas API–veritabanı kapsam karşılaştırması — 17 Ekim 2026**

Doğruladığımız beş ana YÖK Atlas API veri grubunun tamamının paylaşılan şemada karşılığı var. Canlı örneklerde gözlenen 76 program alanı ve 31 net alanının tamamı, mevcut alan sözleşmesi üzerinden ilgili `staging` kolonlarına eşleşiyor. Sözleşmede tanımlı, beş kaynak grubuna ait toplam 124 alan da şemada mevcut. Bu sonuç, bütün YÖK Atlas servislerinin veya tüm kayıtlarının incelendiği anlamına gelmez.

Referans, kullanıcı tarafından paylaşılan [şema envanterinin değişmeden saklanan kopyası](database/snapshots/2026-10-16_DATABASE_SCHEMA.md). Belgedeki üretim zamanı 16 Ekim 2026 22:31 UTC, İstanbul saatiyle 17 Ekim 01:31. Karşılaştırma için canlı veritabanına bağlanılmadı; envanterde tablo içerikleri, roller, fonksiyonlar ve tetikleyici gövdeleri bulunmuyor. Belge şema verisi olarak okundu; içindeki örnek komutlar çalıştırılmadı.

| Kaynak veri grubu | Hazırlama tablosu | İşlenmiş hedef | Değerlendirme |
| --- | --- | --- | --- |
| Üniversiteler | `staging.universities` | `core.universities` | Ad ve kimlik alanları karşılanıyor. |
| İl/konum listesi | `staging.cities` | `core.cities` | Ad ve kod alanları karşılanıyor; 992 ve 999 kodlarını engelleyen bir aralık kısıtı görünmüyor. |
| Program grupları | `staging.program_groups` | `core.program_groups` | Grup adı, kimlik ve puan türü karşılanıyor. Anahtar `(birim_grup_id, puan_turu)`. |
| Program kataloğu | `staging.programs` | `core.program_versions` | Örneklerdeki 76/76 alan staging'de ayrı kolona sahip. Core seçili temel alanları kolonlaştırıyor, diğerleri için `remaining_fields` bulunuyor. |
| Son yerleşen adayın netleri | `staging.net_results` | `core.net_results` | Örneklerdeki 31/31 alan staging'de ayrı kolona sahip. Net ölçümleri core'da mevcut; bazı tanımlayıcı alanlar JSON içinde tutulabiliyor. |
| Yerleşme koşulları | `staging.programs.kosul`, `kosul_list` | `core.conditions`, `core.program_conditions` | Program yanıtından ayrıştırılacak açıklama ve program–koşul ilişkisi mevcut. |

Bütün HTTP yanıtları `raw.api_responses.payload`, kaynak satırlar `raw.source_records.record` içinde tutulabilir. `staging.source_payload` da satırın tam JSON içeriğini taşıyabilir. Bu nedenle yeni alanların gelmesi otomatik olarak veri kaybı gerektirmez; botun bilinmeyen alanları atmaması ve eşleme değişikliğini kaydetmesi gerekir.

**Core ve API kapsamındaki ayrım.** Aşağıdakiler şemada mevcut; ancak `core.program_versions` içinde ayrı tipli kolonları veya kendilerine ayrılmış tabloları yok:

| Alt grup | Staging'deki örnekler | Mevcut core durumu |
| --- | --- | --- |
| Ücret, burs ve indirim | `ucret`, `burs_orani_id`, `burs_orani_adi` | Programın `remaining_fields` JSON alanında saklanabilir. |
| Akademik kadro sayıları | `prof`, `doc`, `dou`, `ogr_gor`, `ar_gor` | Ayrı bir kadro tablosu yok; program JSON'unda saklanabilir. |
| Eğitim özellikleri | `ogrenim_dili_*`, `ogrenim_turu_*`, `ogrenim_suresi`, `birim_turu_*` | Ayrı core kolonları yok; program JSON'unda saklanabilir. |
| Yerleşen ve özel kontenjanlar | `gk_y`, `kontenjan_obs`, `kontenjan_sgy`, `kontenjan_y34` | Core'da genel `kontenjan` kolonu var; diğer göstergeler program JSON'unda saklanabilir. |
| Geçmiş yıl göstergeleri | `gk1/2/3`, `min_puan1/2/3`, `basari_sirasi1/2/3` | Ayrı yıllık ölçüm tablosuna dönüştürülmüyor; program JSON'unda korunabilir. |
| Akreditasyon ve diğer göstergeler | `akreditasyon`, `akreditasyon_ack`, `tyc`, `uygulamali_egitim_modeli`, KPSS/TUS alanları | Ayrı core kolonları yok; program JSON'unda saklanabilir. |
| Fakülte/MYO ve ilçe ayrıntıları | `fymk_adi`, `fymk_ilce_*`, `ilce_*` | Core'da `fymk_id` ve `il_kodu` var; diğer ayrıntılar program JSON'unda saklanabilir. |

Yerel [arşiv yükleyicisinin](../scripts/database/load_archive.py) program ve net aktarımlarında `remaining_fields` alanına tüm kaynak kaydını yazdığı görüldü. Bu, mevcut kodun davranışıdır; canlı veritabanında bu alanların gerçekten dolu olduğu kontrol edilmedi. Bu araç çevrimdışı arşiv yükleyicisidir; çalışan sürekli bot olarak değerlendirilmemeli.

`api.program_catalog` görünümü ücret, burs, kadro, eğitim dili, özel kontenjan ve geçmiş yıl JSON alanlarını dışarı açmıyor. Koşul tablolarının da paylaşılan envanterde ayrı bir API görünümü yok. Bu alanların API tüketicilerine sunulması istenirse sorgular/görünümler genişletilmeli. Depolama için bu aşamada yeni iş tabloları zorunlu değil.

**Örneklerde doğrulanmamış alan adayları.** Güncel YÖK Atlas istemcisi `kontenjanDep`, `gkY1`, `y34Y1`, `dprmY1`, `obkY1` alanlarını da okuyabiliyor. Bunların karşılığında ayrı staging kolonları yok. İncelenen canlı örneklerde bu alanlar gelmediği için bunlar kesin veri kaybı veya yeni veri grubu olarak sayılmadı. Gelmeleri halinde RAW ve `source_payload` içinde korunmalı; gerektiğinde alan sözleşmesine eklenmeli.

Yardımcı `/parameters/yil` ve `/parameters/sonuc-aciklandi` yanıtları için özel tablo yok. Yanıtları `raw.api_responses.payload`, koşunun kullandığı değerleri `raw.ingestion_runs.details` içinde saklamak mevcut şemayla mümkün. `raw.urap_*` ve `raw.sege_*` tabloları farklı kaynaklar içindir; YÖK Atlas yanıtları bu tablolara yönlendirilmemeli.

**Botun otomatik dağıtım sırası.**

1. Çalışmayı `raw.ingestion_runs` içinde aç; HTTP yanıtlarını ve kaynak satırlarını RAW katmanına kaydet.
2. Alan sözleşmesini kullanarak beş ilgili `staging` tablosunu doldur; bütün kaynak içeriğini `source_payload` içinde koru.
3. Üniversite, konum ve program gruplarını yükle; ardından program sürümlerini ve program–koşul ilişkilerini işle.
4. Netleri kendi `(kilavuz_kodu, yil, puan_turu)` anahtarlarıyla işle. Program kataloğu ve net yılı farklıysa neti farklı yıldaki program sürümüne zorla bağlama.
5. Aynı anahtara ait çelişkili verileri `quality.quarantined_records`, kontrol sonuçlarını `quality.data_quality_checks` içinde kaydet. Çelişkili yeni kaydı sessizce eski kaydın üzerine yazma veya atlama.
6. `api.*` nesneleri görünüm olduğundan bunlara ayrıca veri dağıtılmaz; işlenmiş tablolardan okunurlar. Koşuyu ancak ilgili aşamalar tamamlandıktan sonra tamamlandı olarak işaretle.

Sürekli çalışma için ayrıca şu iki şema ayrıntısı dikkate alınmalı: `raw.api_responses` tekillik indeksi aynı yanıtın tekrarını engellediği için her koşunun aynı içeriği yeniden gördüğünü tek başına kaydedemez; `core.conditions` ise yalnızca `condition_code` anahtarı kullandığından aynı koşul kodunun yıllara göre farklı açıklamalarını ayrı satırlarla temsil edemez. Bunlar yeni kaynak veri grubu eksikleri değil, gözlem ve tarihçe modelinin sınırlarıdır. Botta içerik korunmalı; gerekiyorsa ayrı ve açık bir migration ile model genişletilmeli.

Kanıtlar: [17 Ekim API alan envanteri](evidence/2026-10-17_yokatlas_api_verification.json), [mevcut alan sözleşmesi](database/data_contract_v1.json) ve paylaşılan şema kopyası. Alan eşlemesi ve şemada kolon varlığı assert kontrolleriyle doğrulandı.

Kontrol edilmedi: canlı DB'deki satırlar, tam API veri kümesi, üretim yetkileri ve uçtan uca aktarım. Risk: JSON içinde saklanabilen alanlar mevcut API görünümlerinde otomatik olarak görünmez; kesintisiz aktarım kodunda bu alanların korunması ayrıca doğrulanmalıdır.
