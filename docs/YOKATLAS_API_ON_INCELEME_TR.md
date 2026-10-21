**YÖK Atlas API ön incelemesi — 17 Ekim 2026**

YÖK Atlas'ın güncel web uygulamasının kullandığı JSON servisleri, Windows veya Linux üzerinde çalışacak bir veri toplama servisi için kullanılabilir. Aşağıdaki beş ana veri uç noktası ve iki yardımcı parametre uç noktası, `Authorization` veya `Cookie` gönderilmeden HTTP 200 döndürdü. Bunlar gözlenen servislerdir; yayımlanmış ve sürüm garantisi verilmiş bir geliştirici API sözleşmesi olarak değerlendirilmemelidir.

İnceleme; güncel sitenin JavaScript kodu, 22 sınırlı API isteği ve yerel entegrasyon belgelerine dayanır. Arama yanıtlarında yalnızca ikişer kayıt örneklendi. Bildirilen toplamlar API'nin `totalElements` değerleridir; bütün kayıtlar bu incelemede indirilmedi. Hız sınırını bulmak için yük testi yapılmadı.

**Çekilebilen ana veri grupları.** Kök adres `https://yokatlas.yok.gov.tr/api`.

| Yöntem ve yol | Veri grubu | Canlı gözlem |
| --- | --- | --- |
| `GET /tercih-kilavuz/universiteler` | Üniversite adı ve kimliği | 228 kayıt; `universiteAdi`, `universiteId` |
| `GET /tercih-kilavuz/universite-programlar` | Program grupları ve puan türleri | 612 kayıt; `birimGrupId`, `birimGrupAdi`, `puanTuru`. Üniversiteye ait tekil programların listesi değildir. |
| `GET /tercih-kilavuz/universite-iller` | İl/konum adları ve kodları | 83 kayıt: 81 il ile Bosna-Hersek (`992`) ve Kıbrıs (`999`) |
| `POST /tercih-kilavuz/search` | Lisans ve önlisans program kataloğu, tercih ve yerleşme göstergeleri | Katalog yılı 2026; filtresiz yanıtta bildirilen toplam 21.493 kayıt |
| `POST /netler/search` | Programlara yerleşen son kişinin ders netleri, OBP ve puanı | Filtresiz yanıtta bildirilen toplam 63.063 kayıt; SAY, EA, SÖZ, DİL ve TYT için örnekler alındı |

Program aramasının içinde ayrıca şu alt gruplar bulunuyor:

- Program/ÖSYM kodu, üniversite, fakülte/yüksekokul/MYO, bölüm ve program grubu kimlikleri; il ve ilçe bilgileri.
- Lisans/önlisans, puan türü, öğretim türü, eğitim dili ve öğrenim süresi.
- Genel kontenjan ve yerleşen sayıları; uygun programlarda okul birincisi, 34 yaş üstü kadın, depremzede ve şehit/gazi yakını kategorileri. Bazı kategoriler canlı örneklerde, diğerleri güncel istemcinin alan eşlemesinde görüldü; her kayıtta bulunmaları beklenmemeli.
- Taban puan ve başarı sırası; `gk1/2/3`, `minPuan1/2/3`, `basariSirasi1/2/3` gibi geçmiş dönem alanları. Bütün alanlar her programda dolu değil.
- Burs/indirim durumu ve mevcutsa `ucret`. Ücretin net ödenecek tutarı olduğunu varsaymamak, ilgili koşul açıklamalarını birlikte saklamak gerekir.
- `kosul` ve `kosulList` ile yerleşme koşullarının kodları ve açıklamaları; başarı sırası şartı.
- Profesör, doçent, doktor öğretim üyesi, öğretim görevlisi ve araştırma görevlisi sayıları. Bunlar kişi listesi değildir; istemcide akademisyen ayrıntısı için ayrıca YÖK Akademik yönlendirmesi bulunuyor.
- Akreditasyon, akreditasyon açıklaması, TYÇ ve uygulamalı eğitim modeli gibi mevcut göstergeler.
- Bazı yanıtlarda `kpss1`, `tusktp`, `tustt1` gibi ek alanlar da var. Ölçüt ve dönem anlamları bu incelemede doğrulanmadı; doğrudan adlarından hareketle KPI veya sınav puanı tanımı yapılmamalı.

Net araması; yıl, kılavuz kodu, puan türü, katsayı, taban puan ve OBP yanında TYT Türkçe/sosyal/matematik/fen, puan türüne uygun AYT dersleri ve DİL için YDT netlerini veriyor. Bunlar **yerleşen son adayın netleri**, bütün öğrencilerin ortalamaları değil.

Yardımcı `GET /parameters/yil` yanıtı `2026`, `GET /parameters/sonuc-aciklandi` yanıtı `1` oldu. İstemci bu parametreleri dönem etiketleri ve sonuç durumu için kullanıyor. Logo ve YÖK Akademik yönlendirme adresleri de istemcide var; ek bir istatistik tablosu olarak sayılmadı.

Bu envanter, bütün YÖK sistemlerini veya eski Atlas ekranlarındaki tüm dağılım tablolarını kapsamaz. Öğrencilerin cinsiyet/lise/tercih profilleri, tüm geçmiş yıllar, DGS ve lisansüstü gibi ek kapsamların bu servislerden alınabildiği doğrulanmadı.

**Bağlantı ve sayfalama.** HTTPS üzerinden JSON istekleri yeterli. Program araması için örnek HTTP isteği:

```http
POST https://yokatlas.yok.gov.tr/api/tercih-kilavuz/search
Content-Type: application/json
Accept: application/json

{
  "filters": {"puanTuru": "SAY"},
  "page": 0,
  "size": 20,
  "sortBy": "basariSirasi",
  "direction": "ASC"
}
```

İstemcinin kullandığı diğer program filtreleri: `universiteId`, `birimGrupId`, `ilKodu` (listeler); `birimTuruId` (46 lisans, 47 önlisans), `universiteTuru`, `bursOraniId`, `ogrenimTuruId`, `kilavuzKodu`, `minBasariSirasi`, `maxBasariSirasi`. Kimlik değerleri ilgili GET listelerinden çözülmeli. Bunların hepsinin farklı kombinasyonları canlı olarak denenmedi.

`POST /netler/search` için ayrı gövde örneği:

```json
{
  "filters": {"puanTuru": "SAY", "yil": 2025},
  "page": 0,
  "size": 20
}
```

Net servisi istemcide `universiteId` ve `birimGrupId` alanlarını tekil değer olarak kullanıyor; program aramasındaki liste tipini buraya aynen taşımamak gerekir. Detay ekranı ayrıca `kilavuzKodu` ile net araması yapıyor. Net servisine program aramasının bütün filtrelerinin ve sıralama seçeneklerinin desteklendiği varsayılmamalı.

Kayıtlar `content` dizisinde; sayfalama bilgisi `number`, `size`, `numberOfElements`, `totalElements`, `totalPages`, `first`, `last`, `empty` alanlarında geliyor. Sayfa sıfırdan başlıyor. Sonraki isteklerde `page` artırılır; `last=true` olduğunda tarama biter. Her iki aramada da 0 ve 1 numaralı sayfalar denendi, örnek kayıtların değiştiği doğrulandı. Örnekteki 20 sayfa boyutu istemcide kullanılan bir değerdir; bu incelemede doğrulanan sorgular ikişer kayıt istedi. Resmî en yüksek sayfa boyutu bulunamadı.

**Sınırlar ve bot tasarımına etkileri.**

- **Hız kotası belirsiz:** YÖK tarafından yayımlanmış sayısal istek/saniye veya günlük kota belgesi bulunamadı. Küçük isteklerin başarılı olması sınırsız kullanım anlamına gelmez. Başlangıç önerisi tek eşzamanlı istek ve istekler arasında en az 2 saniye; bu bizim temkinli ayarımızdır, YÖK'ün resmî kotası veya engellenmeme garantisi değildir. `429` durumunda varsa `Retry-After` izlenmeli, sınırlı geri çekilme uygulanmalı; erişim engelleri tekrar tekrar zorlanmamalı.
- **İç API değişebilir:** İstemcinin kullandığı uç noktalar doğrulandı; yayımlanmış sürümleme, geriye uyumluluk veya SLA garantisi bulunamadı. JSON alanları, veri tipleri, kimlikler ve adresler değişebilir. Kaynak hata/HTML döndürürse koşu başarılı sayılmamalı.
- **Veri yılları farklı:** Program kataloğu 2026. SAY netlerinde 2023, 2024 ve 2025 filtreleri dolu döndü; filtresiz puan türüyle 2022 ve 2026 yıl sorguları boş döndü. Bu güncel gözlemdir, kalıcı üç yıllık saklama taahhüdü değildir. Katalog yılı, ölçüm yılı ve çekim zamanı ayrı saklanmalı. `minPuan1` gibi alanların yıl eşlemesi, sonuç açıklanma durumu dikkate alınarak doğrulanmalı.
- **Gerçek zamanlı değişiklik akışı doğrulanmadı:** İncelenen arama yanıtları `source: "snapshot"` bildiriyor. Webhook, değişen kayıtlar akışı veya `updated_since` desteği bulunamadı. Belirli aralıklarla sayfalı tarama ve içerik karşılaştırması gerekir; hash kullanımı veritabanındaki gereksiz yazmaları azaltır, kaynak isteğini kendiliğinden ortadan kaldırmaz.
- **Eksik alanlar ve birleştirme:** Sayılar bazı alanlarda metin, bazı alanlarda sayı olabiliyor; sıfır, eksik alan ve `null` ayrılmalı. Program kimliği/yıl veya net kimliği üzerine tekillik varsayımı yapılmadan mevcut veri sözleşmesi ve varyantlar doğrulanmalı. Netlerde katsayı ve diğer ayırt edici alanlar kaybedilmemeli.
- **Toplu kullanım koşulları net değil:** Teknik erişim gözlendi; sürekli toplu çekim ve yeniden dağıtım için açık bir lisans/izin metni doğrulanmadı. Kurumsal kullanım kapsamını ve varsa kota/tam veri dışa aktarım seçeneğini YÖK ile netleştirmek faydalı olur. `robots.txt` isteği HTTP 200 ile robots yönergesi yerine React Native kaynak metni döndürdü; buradan izin veya yasak sonucu çıkarılmadı.

**Bot ve depo önerisi.** İlk sürüm; mevcut Python keşif kodunu ve PostgreSQL sözleşmesini kullanarak tek bir veri toplama servisi olmalı. Akış: zamanlanmış tarama → HTTP/JSON doğrulama → ham yanıt ve koşu kaydı → alan/kimlik kontrolleri → PostgreSQL'e tekrar çalıştırılabilir aktarım. Mevcut sözleşme scraper'ın önce RAW katmanına yazmasını, `staging/core` aktarımının ayrı ve kontrollü yapılmasını istiyor. Otomatik uçtan uca işleme için bu iki aşama aynı zamanlanmış işte sırayla çalıştırılabilir.

Servis sunucuda 7/24 kullanılabilir kalır; başlangıç için günlük eşitleme, yayın döneminde ihtiyaca göre daha sık kontrol önerilir. Bu sıklık kaynak güncellemelerine dair doğrulanmış bir takvim değildir. Linux'ta systemd veya Windows'ta görev zamanlayıcı/servis yönetimiyle çalıştırılabilir. Hata sonrası devam noktası, sınırlandırılmış yeniden deneme, koşu kilidi ve eksik taramayı başarılı saymayan durum kaydı ilk sürümün gerekli parçalarıdır.

Çalışma klasörü zaten `thrustec/yokatlas-intelligence` GitHub deposuna bağlı. En küçük başlangıç mevcut `scraper/` dizinini geliştirmek; ayrı bakım/deploy ihtiyacı varsa `yokatlas-ingestor` adlı ayrı bir depo düşünülebilir. Kod ve testler GitHub'da, çalışan servis sunucuda tutulur; veritabanı şifreleri ortam değişkenlerinden alınır. Bu aşamada yeni depo oluşturulmadı, bot kodu yazılmadı ve veritabanına veri işlenmedi.

**Kaynaklar ve kanıt.**

- [YÖK Atlas](https://yokatlas.yok.gov.tr/) ve [güncel web istemcisi](https://yokatlas.yok.gov.tr/static/js/main.0694672d.js). İndirilen istemci mevcut `yokatlas-main.js` ile aynı SHA-256 içeriğe sahipti.
- Yukarıdaki tabloda tam kök ile belirtilen uç noktaların doğrudan canlı yanıtları.
- [İstekler, durum kodları, yanıt hash'leri, sayfalama metadatası ve gözlenen alan envanteri](evidence/2026-10-17_yokatlas_api_verification.json). Bu dosya tüm ham yanıtların arşivi değil, sınırlandırılmış incelemenin özet kanıtıdır. Hash, inceleme sırasında alınan yanıt baytlarına aittir.
- [Mevcut scraper–PostgreSQL sözleşmesi](SCRAPER_POSTGRES_INTEGRATION_GUIDE.md) ve [keşif aracı](../scraper/yokatlas_api_explorer/yokatlas_discovery.py).

Kontrol edilmedi: bütün kayıtların içeriği, azami sayfa boyutu, yük altında davranış, uzun süreli erişim ve üretim sunucusu bağlantısı. Başlıca risk: doğrulanmış bir servis/kota sözleşmesi olmadan kaynağın değişmesi, gecikmesi veya erişimi sınırlaması.
