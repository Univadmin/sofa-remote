# Sofa Remote

Windows 10/11’e bağlı TV için Türkçe, yerel ağ üzerinden çalışan mobil kumanda. Reklam, abonelik veya bulut hesabı yok. **İlk sürüm / v0.1.0**: evde gerçek Windows + telefon testi gerekir.

## Özellikler

- Touchpad: göreli hareket, tıklama, çift dokunuşla çift tık, sağ/orta tık, iki parmakla kaydırma, sürükleme, solak modu, hız ayarı.
- Türkçe ve emoji dahil Unicode metin girişi. Telefon klavyesi destekliyorsa mikrofonla yazdırma.
- Ctrl / Alt / Shift / Win birleşimleri, F1–F12, gezinme tuşları, elle kısayol girişi.
- Sistem sesi, sessiz, medya tuşları; genel site, YouTube ve Netflix klavye profilleri.
- Tarayıcı sekmeleri, adres çubuğu, geri/ileri, yenileme, tam ekran, pencere değiştirme.
- Site düğmeleri; metin, tuş, adres ve bekleme adımlarından oluşan özel makrolar. JSON ile yedekleme ve düzenleme.
- PC ekranının manuel JPEG önizlemesi, açık pencereleri listeleme ve öne getirme.
- İstek üzerine iki yönlü **metin** panosu aktarımı; otomatik pano izleme yapılmaz.
- Sunum kontrolü, kilitleme, 30 saniye gecikmeli kapatma/yeniden başlatma ve iptal.
- 6 haneli eşleştirme, giriş denemesi sınırı, 24 saatlik oturum, yeniden bağlantı, tek aktif kontrolcü.
- Android APK kabuğu; iPhone/Android tarayıcı arayüzü. APK bilgisayardaki arayüzü yükler, internet sunucusuna ihtiyaç duymaz.

## Windows’ta başlatma

### Hazır EXE ve Android APK

GitHub **Actions → Test and build → başarılı çalışma → Artifacts** bölümünden:

- `Sofa-Remote-Windows`: ZIP içindeki `SofaRemote.exe` dosyasını çalıştır.
- `Sofa-Remote-Android-debug`: APK’yi Android telefonuna kur. Bu bir geliştirme imzalı APK’dir; Play Store sürümü değildir. Sonraki derlemelerin debug imzası değişebilir; gerektiğinde önce eski APK’yi kaldır.

Windows uygulaması bir konsol penceresinde bilgisayar adresini, QR kodunu ve eşleştirme kodunu gösterir. Pencereyi açık tut. EXE imzalı değildir; kaynak koddan çalıştırma seçeneği aşağıdadır.

### Kaynaktan

1. Python 3.11+ kur (Python 3.12 önerilir).
2. Repo ZIP’ini indirip çıkart veya klonla.
3. `scripts/start-windows.cmd` dosyasını çalıştır. İlk çalıştırmada bağımlılıklar indirilir.
4. Windows Güvenlik Duvarı sorarsa yalnızca **özel ev ağı** için izin ver.
5. Telefonunu aynı Wi-Fi ağına bağla. Konsolda çıkan `http://192.168.x.x:8765` adresini telefonda aç veya QR kodunu okut.
6. Altı haneli kodla eşleştir. Android uygulamasında da önce aynı bilgisayar adresini gir.

iPhone: Safari ile adresi aç, istersen Paylaş → Ana Ekrana Ekle kullan. Bu sürümde native iOS IPA yok. HTTP üzerinde tarayıcıların tam PWA/çevrimdışı kurulum özellikleri sınırlıdır; normal web kumandası çalışır. Sunucu çalışmadan uygulama kontrol sağlayamaz.

Otomatik başlatma isteğe bağlıdır: PowerShell’de `scripts/enable-startup.ps1` çalıştır. Kaldırmak için Windows Başlangıç klasöründeki Sofa Remote kısayolunu sil. Ayarlar `%LOCALAPPDATA%/SofaRemote/shortcuts.json` dosyasında saklanır. Sunucu yeniden başladığında eşleştirme kodu ve oturumlar yenilenir.

## Medya kullanımı

Tarayıcıda videoyu açıp bir kez videoya tıkla. Medya panelinden uygun profili seç. YouTube’da K/J/L, Netflix’te Space/ok tuşları gönderilir. Genel sitelerde oynatıcının klavye desteği gerekir. Reklam penceresi, adres çubuğu veya başka pencere odaktaysa komut oraya gider. Her üçüncü parti oynatıcı için evrensel kontrol garantisi yoktur. Netflix altyazı kısayolu ve zaman atlama miktarı oynatıcıya bağlıdır. Gerekirse mouse ve klavyeyi kullan.

F1–F12 desteklenir; fiziksel klavyenin donanıma özgü Fn tuşu taklit edilmez. Ekran önizlemesi video yayını değildir; DRM korumalı video siyah görünebilir. Windows kilit ekranı, UAC güvenli masaüstü veya yönetici uygulamaları normal kullanıcı girdisini engelleyebilir. Kilitleme sonrası telefonla oturum açmayı bekleme.

## Makro örneği

Araçlar → Gelişmiş makro bölümündeki listeye eklenebilir:

```json
{
  "name": "YouTube aç",
  "actions": [
    {"type": "url", "url": "https://www.youtube.com"},
    {"type": "delay", "ms": 800},
    {"type": "keys", "keys": ["F11"]}
  ]
}
```

F11 mevcut tarayıcı durumunu tersine çevirir; her zaman tam ekrana geçirmez. Sayfanın açılma hızı değişebilir. Kısayol silme ve JSON yedek içeriğini geri yapıştırarak yükleme desteklenir. Eşleşen cihazlar kısayolları değiştirebilir.

## Bağlantı ve gizlilik

Kontrol WebSocket üzerinden doğrudan ev ağında gider. PC’nin Ethernet ile bağlanması önerilir. Misafir Wi-Fi / cihaz izolasyonu bağlantıyı engeller. Çoklu ağ kartında konsoldaki IP yanlışsa `ipconfig` ile ev ağı IPv4 adresini kullan.

Varsayılan HTTP bağlantısı **şifrelenmez**; kod, metin ve ekran yalnızca güvendiğin ev ağında kullanılmalıdır. Modemde port yönlendirme açma. TLS için güvenilir bir sertifika ile:

```sh
python -m server.app --tls-cert server.crt --tls-key server.key
```

Mobil cihazın sertifikaya güvenmesi gerekir; Android kabuğu sertifika hatalarını atlamaz. Eşleştirme kodu telefon URL’sine veya QR koduna konulmaz. Pano ve ekran sadece düğmeye basıldığında okunur; telemetri yoktur. Sunucuyu kapatmak tüm oturumları iptal eder.

## Geliştirme ve test

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
node --check web/app.js
python -m server.app --dry-run
```

Dry-run hiçbir işletim sisteminde gerçek giriş, pano, güç veya site açma işlemi yapmaz. Komutlar belleğe kaydedilir. Windows ekran görüntüsü demo modunda kapalıdır. CI Linux ve Windows’ta protokol testleri, Android APK ve Windows EXE derlemesi yapar. Gerçek input enjeksiyonu ve Android/iOS cihaz testi ayrıca gerekir.

Android: JDK 17, Android SDK 35, Gradle 8.11.1 ile `gradle -p android assembleDebug`. Python sunucusunun web klasörü EXE’ye PyInstaller ile dahil edilir.

### Bu sürümün dışında

Bluetooth, jiroskop mouse, telefonun fiziksel ses düğmeleri, resim/dosya panosu, dosya yöneticisi, Wake-on-LAN, otomatik video algılama, native iOS uygulaması ve mağaza yayını bu sürümde yoktur. PC kapalıyken kumanda sunucusu da çalışmaz. Üçüncü parti uygulamaların kodu veya marka görselleri kopyalanmamıştır.

## İncelenen ürün özellikleri

Özellik kapsamı için [Remote Mouse](https://play.google.com/store/apps/details?id=com.hungrybolo.remotemouseandroid) ve [Unified Remote](https://www.unifiedremote.com/features) listeleri incelendi. Bu proje bağımsızdır.

MIT lisansı.
