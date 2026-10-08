# YÖK Atlas Intelligence — Forensics Kararları (Data Contract v1 Taslak)

Bu rapor `forensics_summary.json`, `net_duplicate_groups.csv`, `collection_coverage.csv` ve önceki `normalized_schema.json` girdilerine dayanır.

## Gözlenen kapsama
- 5 puan türü için programlar: **21.491 satır / 217 sayfa**.
- Netler: **63.063 satır / 632 sayfa**.
- Toplam: **849 sayfa**, eksik sayfa ve bozuk JSON **0**; `totalElements` sayımları eşleşiyor.
- Üniversite: 228; program grubu: 611; il: 83.
- Bu yalnızca bilinen ve sorgulanmış endpoint'lerin sayfalama kapsamıdır. Bilinmeyen endpoint'ler kapsama dahil değildir.

## Net kayıt tekrarları
- `kilavuzKodu + yil` üzerinde 88 çift (her biri iki kayıt), 88 fazla satır.
- 71 çiftte JSON birebir aynı: 70 aynı sayfada, 1 farklı sayfada.
- 17 çiftte JSON farklı, ancak tamamında `puanTuru` da farklı (2024 yılı).
- 17 çiftin hepsi ayrı puan türü varyantlarıdır; birbirlerinin üzerine yazılmamalıdır.
- Ham satırların hepsini sakla; yalnızca core katmanında 71 birebir aynı tekrarın tekilleştirilmesi önerilir.
- Bu tekilleştirmeden sonra net satır sayısı **62.992** beklenir. Bu toplam henüz kanonik ETL yüklemesiyle yeniden ölçülmedi.
- Core için önerilen doğal anahtar: `(kilavuz_kodu, yil, puan_turu)`; gerçek ham satırlarda ETL öncesi son kez kontrol edilmeli.

## İlişkisel anahtarlar
- universities: `universite_id`.
- cities: `il_kodu`.
- program_groups: `(birim_grup_id, puan_turu)`.
- program_versions: `(kilavuz_kodu, yil)` UNIQUE, dahili `program_version_id` PK.
- net_results: `(kilavuz_kodu, yil, puan_turu)` UNIQUE, dahili `net_result_id` PK.
- 2026 program verilerini 2023/24/25 net kayıtlarıyla **aynı yıl foreign key** olarak doğrudan bağlamayın.
- Netlerin üniversite ve program grubu referanslarında tarihsel orphan kayıtları var; bu referanslara FK zorlamayın.
- API'nin geçmiş yıla ait `minPuan1/2/3` ve benzeri suffix alanlarını resmi yıl eşleme testi tamamlanmadan 2025/24/23'e yazmayın.

## SQL dosyasının kapsamı
- `raw`: immutable API yanıtları ve her kaydın kaynağı.
- `staging`: 5 gözlenen entity için toplam **124 tipli kaynak sütunu**.
- `core`: üniversite, il, program grubu, program sürümü, net sonucu, koşullar.
- `quality`: çelişen aynı doğal anahtarlar için quarantine ve kalite kontrolleri.
- `analytics`: gelecekteki insight işler için ayrılmış schema.
- Bu bir **başlangıç migration taslağıdır**, ETL loader yazılımı değildir.
- SQL dosyası PostgreSQL sunucusunda yürütülerek test edilmedi. Migrasyon öncesi boş test DB üzerinde çalıştırılmalı.

## ETL için zorunlu sıra
1. Raw'da her yanıt ve satırı bozulmadan sakla (run id, skor türü, sayfa, zaman, hash).
2. Staging tablolarına bütün gözlenen alanları yaz; bilinmeyenleri JSONB payload'da tut.
3. Lookup tablolarını yükle, `(birim_grup_id, puan_turu)` tekilliğini kontrol et.
4. 2026 program sürümlerini `(kilavuz_kodu, yil)` üzerinden upsert et.
5. Netler için `(kilavuz_kodu, yil, puan_turu)` grupları oluştur.
6. Aynı payload olanları core'da tekilleştir; farklı payload ve aynı üçlü anahtar varsa quality.quarantined_records'e al.
7. Puan türü farklı 17 çifti ayrı kayıt olarak koru.
8. Aynı-yıl program referansları API'den gelene kadar net program_version_id değerini NULL tut.
9. Kaynak yılı ile ingest zamanı karıştırma; her yıl önceki snapshot'ları ve çalışma sonuçlarını koru.
