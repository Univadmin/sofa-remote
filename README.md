# Sofa Remote

Windows bilgisayarını telefondan kontrol et. Mouse, klavye, medya ve tarayıcı kumandalarını aynı ekranda birleştir.

**[↓ Downloads](https://github.com/Univadmin/sofa-remote/releases/latest)** · [Tüm sürümler](https://github.com/Univadmin/sofa-remote/releases) · [Kurulum](#kurulum)

## Downloads

| Platform | İndir |
|---|---|
| Windows 10 / 11 | [SofaRemote.exe](https://github.com/Univadmin/sofa-remote/releases/latest/download/SofaRemote.exe) |
| Android 8+ | [SofaRemote-Android.apk](https://github.com/Univadmin/sofa-remote/releases/latest/download/SofaRemote-Android.apk) |
| Chrome / Edge sekme eklentisi | [SofaRemote-Browser.zip](https://github.com/Univadmin/sofa-remote/releases/latest/download/SofaRemote-Browser.zip) |

APK ve EXE sürüm numaraları, dosya boyutları ve önceki sürümler [Downloads sayfasında](https://github.com/Univadmin/sofa-remote/releases) bulunur. Uygulama içinde de **Downloads** alanı vardır.

## Kurulum

1. Windows’ta **SofaRemote.exe** dosyasını çalıştır. Pencere açık kalsın.
2. Telefon ve bilgisayarı aynı ev ağına bağla. Windows güvenlik duvarı sorarsa özel ev ağına izin ver.
3. Android APK’yi kur ve aç. Son bilgisayara otomatik bağlanmayı dener; bulunamazsa ağı tarar. Listelenen bilgisayara dokun. Şifre gerekmez.
4. iPhone’da Windows penceresindeki yerel adresi Safari ile aç. Otomatik ağ keşfi ve fiziksel ses tuşları Android uygulamasındadır.

Ağ keşfi UDP 8766, kumanda bağlantısı TCP 8765 kullanır. Broadcast engellenirse Android yerel ağında sınırlı adres taraması yapar. Misafir Wi-Fi, istemci izolasyonu veya güvenlik duvarı keşfi engelleyebilir; Cihazlar bölümünden adresle bağlantı da yapılabilir.

### v0.1 kullananlar

v0.2 Android uygulaması yeni, genel bir paket kimliği ve kalıcı yayın imzası kullanır. v0.1 APK’sinin yerine bir kez yeni APK’yi kur; dilersen eski uygulamayı kaldır. Bundan sonraki APK güncellemeleri aynı paket ve imzayla gelir. Windows için yeni EXE’yi indirip eski programı kapattıktan sonra çalıştır.

## İki kumanda, tek ekran

Ekran iki sabit alana ayrılır. Her alanın üstündeki listeden bağımsız kumanda seç: **Mouse + Medya**, **Klavye + Tarayıcı**, **Mouse + Uygulamalar** gibi. Düzen düğmesiyle üst üste veya yan yana görünümü seç. Tercihler hatırlanır; paneller kendi içlerinde kayar.

- **Mouse:** touchpad, sol/sağ/orta tık, iki parmak kaydırma, sürükleme, hız ve solak ayarı.
- **Klavye:** telefon klavyesiyle anlık yazma, silme, Enter; Ctrl/Alt/Shift/Win, F1–F12 ve özel birleşimler. Yazı alanında yapılan değişiklikler PC’deki odaklanmış alana gönderilir. PC imlecini başka yolla taşırsan **Yeni alan** düğmesine dokun.
- **Medya:** ses, sessiz, oynat/duraklat; genel site, YouTube ve Netflix profilleri. Android uygulaması ön plandayken telefonun ses düğmeleri PC sesini değiştirir.
- **Tarayıcı / Sekmeler:** gezinme, sekme açma/kapatma/geçiş; eklenti bağlıysa sekmeleri adlarıyla listeleme, doğrudan seçme, yenileme ve kopyalama.
- **Uygulamalar:** açık pencerelere geçiş, küçültme, büyütme, kapatma; Chrome, Edge, Firefox, Dosya Gezgini ve Hesap Makinesi başlatma.
- **Tüm butonlar:** aranabilir komut kataloğu. Desteklenen komutlar `+` düğmesiyle kısayola eklenebilir.
- **Araçlar:** ekran önizlemesi, iki yönlü metin panosu ve güç işlemleri.

Üst kısayol şeridi isimler yerine sitenin sembolünü gösterir. Sembol bulunamazsa yedek simge kullanılır; düğmenin erişilebilir adı ve açıklaması korunur. Site simgeleri ilgili sitenin `/favicon.ico` adresinden alınır. Özel makrolara kendi sembolünü verebilirsin.

## Tarayıcı sekmelerini listeleme

Windows’ta Chrome veya Edge için:

1. Browser ZIP’ini indir ve klasöre çıkart.
2. `chrome://extensions` veya `edge://extensions` sayfasını aç, Geliştirici modunu etkinleştir.
3. **Paketlenmemiş öğe yükle** ile çıkarttığın klasörü seç.

Eklenti yalnızca aynı bilgisayardaki Sofa Remote sunucusuna bağlanır. Telefonun Tarayıcı panelindeki **Yenile** düğmesi açık sekmeleri getirir. Sekme adları ve adresleri ev ağındaki bağlı kumandaya gösterilir. Eklentisiz temel tarayıcı kısayolları kullanılabilir.

## Güncellemeler

- Windows ve Android açılışta GitHub’daki son kararlı sürümü kontrol eder.
- Paketli Windows uygulaması yeni EXE’yi otomatik indirip SHA-256 değerini doğrular. Downloads → **PC güncellemesini uygula** ile program yeniden başlatılır. Önceki EXE yedeği saklanır.
- Android yeni APK’yi Wi-Fi üzerinden indirip SHA-256 değerini doğrular. Downloads → **Android güncellemesini kur** Android’in standart kurulum onayını açar. Gerekirse bu uygulamadan yüklemeye bir defa izin verilir. Sessiz kurulum yapılmaz.
- İnternet yokken yerel kumanda çalışmaya devam eder. Güncelleme denetimi başarısızsa daha sonra tekrar denenebilir.

## Kullanım bilgileri

Bağlantı şifresizdir: aynı yerel ağdaki cihazlar PC’yi kontrol edebilir. Varsayılan HTTP trafiği şifrelenmez. Güvendiğin ev ağında kullan; modemde port yönlendirme açma. İsteğe bağlı TLS sunucu seçenekleri `--tls-cert` ve `--tls-key` ile kullanılabilir; Android otomatik keşfi varsayılan HTTP adreslerini bulur.

Medya komutları aktif pencereye gider; oynatıcıya önce tıkla. Üçüncü parti sitelerin kısayol desteği değişir. DRM korumalı içerik ekran önizlemesinde siyah görünebilir. Windows kilit ekranı ve UAC masaüstü uzaktan yazmayı engeller. Fiziksel donanım Fn tuşu yerine F1–F12 gönderilir.

## Kaynaktan çalıştırma

Python 3.11+ kurulu Windows’ta `scripts/start-windows.cmd` dosyasını çalıştır. İsteğe bağlı otomatik açılış için `scripts/enable-startup.ps1` kullanılabilir. Kısayollar `%LOCALAPPDATA%/SofaRemote/shortcuts.json` içinde tutulur.

MIT lisansı.
