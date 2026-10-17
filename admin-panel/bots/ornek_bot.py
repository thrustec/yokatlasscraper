"""Örnek bot: panelin her özelliğini denemek için.

Gerçek bir siteye gitmez; sayfa indiriyormuş gibi yapar. Yeni bir bot yazarken
şablon olarak kullanılabilir. Ayarlar panelden değiştirilebilir:
  sayfa_sayisi, bekleme_saniye, hata_orani (0-1 arası)
"""
import random

from botkit import Bot

with Bot.from_env() as bot:
    sayfa_sayisi = int(bot.settings.get("sayfa_sayisi", 40))
    bekleme = float(bot.settings.get("bekleme_saniye", 0.5))
    hata_orani = float(bot.settings.get("hata_orani", 0.05))

    if bot.retry_requests:
        # Yeniden deneme çalışması: sadece önceki başarısız sayfalar
        hedefler = [(r["request_key"], r["failed_id"]) for r in bot.retry_requests]
    else:
        hedefler = [(f"sayfa:{i}", None) for i in range(1, sayfa_sayisi + 1)]

    toplam = 0
    for i, (anahtar, failed_id) in enumerate(hedefler, 1):
        if bot.should_stop():
            break
        bot.progress(i, len(hedefler), "Sayfalar")
        bot.sleep(bekleme)
        if random.random() < hata_orani and not failed_id:
            bot.request_failed(anahtar, url=f"https://ornek.invalid/{anahtar}", http_status=503,
                               error="Sunucu meşgul (örnek hata)", failed_id=failed_id)
            continue
        kayit = random.randint(20, 80)
        bot.request_ok(failed_id=failed_id)
        bot.records(kayit)
        toplam += kayit
        if i % 10 == 0:
            bot.log(f"{i}/{len(hedefler)} sayfa işlendi, şu ana kadar {toplam} kayıt")

    if not bot.should_stop() and not bot.retry_requests:
        bot.check("Örnek bot: kayıt sayısı makul mü?", toplam > sayfa_sayisi * 10, {"kayit": toplam})
    bot.summary(toplam_kayit=toplam)
