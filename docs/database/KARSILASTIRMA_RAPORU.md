# Canlı şema karşılaştırması — 22 Ekim 2026

- 59 RAW tablo eşleşti.
- 470/470 kolon eşleşti; eksik ve fazladan kolon yok.
- NULL/NOT NULL farkı yok.
- IDENTITY farkı yok; 24 adet `GENERATED ALWAYS AS IDENTITY` alan var.
- 24 aktif trigger canlıdan alındı.
- 271 constraint, 125 indeks canlı katalogdan belgelendi.
- 14 salt yazım/gösterim farkı: 10 adet `timestamptz`/`timestamp with time zone` ve 4 adet text literal DEFAULT cast'i.
- PostgreSQL COMMENT bulunan kolon: 3. Geri kalan Türkçe açıklamalar önceki belge yazarının iş açıklamalarıdır, canlı DB açıklaması değildir.

Üretimde **şema değişikliği yapılmadı**. PostgreSQL katalog çıktısının o anda gösterdiği yapı esas alındı.

**Önemli:** Kontrol karşılaştırması eski dosyada constraint ve index tanımlarının doğruluğunu otomatik kanıtlamaz; bu pakette canlı kayıttaki tanımlar aynen yer almaktadır.
