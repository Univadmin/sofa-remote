# Sofa Remote

Windows bilgisayarını telefondan kontrol et. Mouse, klavye, medya ve tarayıcı kumandalarını aynı ekranda birleştir.

**[↓ Downloads](https://github.com/Univadmin/sofa-remote/releases/latest)** · [Tüm sürümler](https://github.com/Univadmin/sofa-remote/releases) · [Kurulum](#kurulum)

## Downloads

| Platform | İndir |
|---|---|
| Windows 10 / 11 | [SofaRemote.exe](https://github.com/Univadmin/sofa-remote/releases/latest/download/SofaRemote.exe) |
| Android 8+ | [SofaRemote-Android.apk](https://github.com/Univadmin/sofa-remote/releases/latest/download/SofaRemote-Android.apk) |
| Chrome / Edge sekme eklentisi | [SofaRemote-Browser.zip](https://github.com/Univadmin/sofa-remote/releases/latest/download/SofaRemote-Browser.zip) |

APK ve EXE sürüm numaraları, dosya boyutları ve önceki sürümler [Downloads sayfasında](https://github.com/Univadmin/sofa-remote/releases) bulunur. Uygulama içindeki **Güncelleme** alanı sürüm bilgisi ve güncelleme kontrolünü gösterir.

## Kurulum

1. Windows’ta **SofaRemote.exe** dosyasını çalıştır. Otomatik açılış için aşağıdaki kurulumu bir kez yap.
2. Telefon ve bilgisayarı aynı ev ağına bağla. Windows güvenlik duvarı sorarsa özel ev ağına izin ver.
3. Android APK’yi kur ve aç. Son bilgisayara otomatik bağlanmayı dener; bulunamazsa ağı tarar. Listelenen bilgisayara dokun. Şifre gerekmez.
4. iPhone’da Windows penceresindeki yerel adresi Safari ile aç. Otomatik ağ keşfi ve fiziksel ses tuşları Android uygulamasındadır.

Ağ keşfi UDP 8766, kumanda bağlantısı TCP 8765 kullanır. Broadcast engellenirse Android yerel ağında sınırlı adres taraması yapar. Misafir Wi-Fi, istemci izolasyonu veya güvenlik duvarı keşfi engelleyebilir; Cihazlar bölümünden adresle bağlantı da yapılabilir.

### Windows’ta otomatik açılış ve yeniden başlatma

GitHub’dan EXE’yi indirip çift tıkla. Adını veya bulunduğu klasörü değiştirmiş olsan da uygulama kendini `%LOCALAPPDATA%\SofaRemote\bin\SofaRemote.exe` konumuna kurar. Çalışan eski sürümü devralır; yönetici izni veya terminal komutu gerekmez. Kurulum doğrulandıktan sonra çalıştırdığın indirme dosyası, eski EXE yedeği ve güncelleme paketleri otomatik silinir. Başka klasörlerde elle oluşturulmuş eski kopyalar aranmaz.

Sonraki güncellemeler telefondaki Güncelleme menüsünden yapılır. Tek kurulu EXE yerinde güncellenir, yeniden açılır ve başarılı açılıştan sonra eski paketler temizlenir. Windows oturumu açıldığında otomatik başlar; çökerse veya kapatılırsa izleyici tekrar açar. Bilgisayar kapalıyken veya Windows oturumu açılmadan çalışmaz.

Otomatik başlatmayı kapatmak için:

```powershell
& "$env:LOCALAPPDATA\SofaRemote\bin\SofaRemote.exe" --disable-startup
```

Bu komuttan sonra uygulamayı Görev Yöneticisi’nden kapatabilirsin. Güncelleme günlüğü `%LOCALAPPDATA%\SofaRemote\updates\update.log`, izleyici günlüğü `%LOCALAPPDATA%\SofaRemote\watchdog.log` konumundadır.

### v0.1 kullananlar

v0.2 Android uygulaması yeni, genel bir paket kimliği ve kalıcı yayın imzası kullanır. v0.1 APK’sinin yerine bir kez yeni APK’yi kur; dilersen eski uygulamayı kaldır. Bundan sonraki APK güncellemeleri aynı paket ve imzayla gelir. Windows için yeni EXE’yi indirip eski programı kapattıktan sonra çalıştır.

Birden fazla telefon aynı PC’ye eşzamanlı bağlanabilir. Her telefonun basılı tuttuğu mouse düğmeleri ayrı izlenir; birinin bağlantısı kesilince diğerinin sürüklemesi kesilmez.

## İki kumanda, tek ekran

Ekran iki sabit alana ayrılır. Her alanın üstündeki listeden bağımsız kumanda seç: **Mouse + Medya**, **Klavye + Tarayıcı**, **Mouse + Uygulamalar** gibi. Düzen düğmesiyle üst üste veya yan yana görünümü seç. Tercihler hatırlanır; paneller kendi içlerinde kayar.

- **Mouse:** touchpad, sol/sağ/orta tık, iki parmak kaydırma, hız ve solak ayarı. Çift dokunup ikinci dokunuşu basılı tutarak klasör veya pencere sürükle. **Düzen → Bütün ekranı mouse olarak kullan** açıkken yarım saniye basılı tut, ardından kaydır; bıraktığında sol tık gönderilir. Tek dokunuş uygulamayı normal kullanır. Metinlerin ve yazı alanlarının üzerinde basılı tutmak da tam ekran mouse’u başlatır; kısa dokunuşla alanı normal kullanabilirsin. Normal mouse yüzeyi bu ayardan bağımsız çalışır.
- **Klavye:** telefon klavyesiyle anlık yazma, silme, Enter; Ctrl/Alt/Shift/Win, F1–F12 ve özel birleşimler. Yazı alanında yapılan değişiklikler PC’deki odaklanmış alana gönderilir. PC imlecini başka yolla taşırsan **Yeni alan** düğmesine dokun.
- **Medya:** ses, sessiz, oynat/duraklat; genel site, YouTube ve Netflix profilleri. Android uygulaması ön plandayken telefonun ses düğmeleri PC sesini değiştirir.
- **Tarayıcı / Sekmeler:** gezinme, sekme açma/kapatma/geçiş; eklenti bağlıysa sekmeleri adlarıyla listeleme, doğrudan seçme, yenileme ve kopyalama.
- **Uygulamalar:** açık pencerelere geçiş, küçültme, büyütme, kapatma; Chrome, Edge, Firefox, Dosya Gezgini ve Hesap Makinesi başlatma.
- **Tüm butonlar:** aranabilir komut kataloğu. Desteklenen komutlar `+` düğmesiyle kısayola eklenebilir.
- **Araçlar:** ekran önizlemesi, iki yönlü metin panosu ve güç işlemleri.

En üst şerit iki eşit alandır: solda kaydırılabilir site/makro kısayolları, sağda yalnızca sekme simgeleri. Sağdaki simgelere dokunmak sekmeler arasında geçiş yapar; basılı tutmak **Sekmeyi kapat** seçeneğini açar. Android’de bu menü yerel uygulama penceresinde açılır. Sekme listesi Tarayıcı panelinin başındadır; yenileme ve kopyalama ayrı satırdadır. Simgeler açık sekmenin favicon bilgisi veya sitenin bildirdiği internet simgesi üzerinden alınır; bulunamazsa yedek simge gösterilir. URL içermeyen makrolara kendi sembolünü verebilirsin.

## Tarayıcı sekmelerini listeleme

Windows’ta Chrome veya Edge için:

1. Browser ZIP’ini indir ve klasöre çıkart.
2. `chrome://extensions` veya `edge://extensions` sayfasını aç, Geliştirici modunu etkinleştir.
3. **Paketlenmemiş öğe yükle** ile çıkarttığın klasörü seç.

Yeni sürümde eklenti HTTP/HTTPS sayfalardaki yazı alanı odağını da algılar. Mevcut eklenti klasörünü yeni ZIP içeriğiyle değiştir, uzantılar sayfasından yeniden yükle ve açık siteleri yenile. Android uygulaması ön plandayken PC’de yazı alanına girildiğinde telefon klavyesi açılır; yalnızca odak bilgisi paylaşılır, alan içeriği okunmaz. Windows yazı alanları UI Automation erişilebilirlik odağı ve standart yazı imleciyle algılanır. Android, otomatik klavyeyi yerel yazı giriş alanıyla açar; Türkçe karakterler, emoji, silme ve Enter anlık gönderilir. Salt okunur alanlar UI Automation üzerinden ayırt edilir. Özel çizilmiş alanlar, tarayıcının korumalı sayfaları ve adres çubuğu her zaman algılanamayabilir. iPhone/tarayıcı güvenlik kısıtları nedeniyle klavye alanına elle dokunmak gerekebilir.

Eklenti yalnızca aynı bilgisayardaki Sofa Remote sunucusuna bağlanır. Telefonun Tarayıcı panelindeki **Yenile** düğmesi açık sekmeleri getirir. Sekme adları ve adresleri ev ağındaki bağlı kumandaya gösterilir. Eklentisiz temel tarayıcı kısayolları kullanılabilir.

## Güncellemeler

- Windows ve Android açılışta GitHub’daki son kararlı sürümü kontrol eder.
- Paketli Windows uygulaması yeni EXE’yi otomatik indirip SHA-256 değerini doğrular. **Güncelleme → Güncellemeleri kontrol et** sonrasında paket hazırsa yeniden başlatma onayı açılır. Dosya kilidinin kalkması beklenir, uygulama yeniden açılır ve sürüm doğrulanır. Başlatma başarısızsa önceki EXE geri yüklenip tekrar açılır. Telefon güncelleme sırasında aynı PC’ye bağlanmayı sürdürür.
- Android yeni APK’yi Wi-Fi üzerinden indirip SHA-256 değerini doğrular. Uygulama ön plandayken indirme tamamlanınca Android’in standart kurulum onayı doğrudan açılır. Gerekirse Sofa Remote için yükleme iznini aç; uygulamaya dönünce kurulum devam eder. Tarayıcı açma veya APK dosyasını elle bulma gerekmez. İptal edilen kurulum **Güncellemeleri kontrol et** ile yeniden başlatılabilir.
- İnternet yokken yerel kumanda çalışmaya devam eder. Güncelleme denetimi başarısızsa daha sonra tekrar denenebilir.

## Kullanım bilgileri

Bağlantı şifresizdir: aynı yerel ağdaki cihazlar PC’yi kontrol edebilir. Varsayılan HTTP trafiği şifrelenmez. Güvendiğin ev ağında kullan; modemde port yönlendirme açma. İsteğe bağlı TLS sunucu seçenekleri `--tls-cert` ve `--tls-key` ile kullanılabilir; Android otomatik keşfi varsayılan HTTP adreslerini bulur.

Medya komutları aktif pencereye gider; oynatıcıya önce tıkla. Üçüncü parti sitelerin kısayol desteği değişir. DRM korumalı içerik ekran önizlemesinde siyah görünebilir. Windows kilit ekranı ve UAC masaüstü uzaktan yazmayı engeller. Fiziksel donanım Fn tuşu yerine F1–F12 gönderilir.

## Kaynaktan çalıştırma

Python 3.11+ kurulu Windows’ta `scripts/start-windows.cmd` dosyasını çalıştır. İsteğe bağlı otomatik açılış için `scripts/enable-startup.ps1` kullanılabilir. Kısayollar `%LOCALAPPDATA%/SofaRemote/shortcuts.json` içinde tutulur.

MIT lisansı.

### Film modu

Alt bardaki Film düğmesi veya kumanda listesindeki Film modu ile film ara. Anahtar ya da hesap kurulumu gerekmez. Türkçe/orijinal film adı, yıl ve IMDb puanı JustWatch’ın herkese açık Türkiye kataloğundan alınır; tüm internetteki her filmi kapsadığı garanti edilmez. Sonuçlar sayfalıdır ve ziyaret edilen kayıtlar PC’de önbelleğe alınır. Yayın ve dil verileri önbellekten en fazla 15 dakika kullanılır.

Film seçilince katalog kayıtları doğrudan izlenebilir sayılmaz. Güncel PC tarayıcı eklentisi, aday adresleri sessiz kontrol sekmelerinde açar; gerçek başlatma girdisi gereken oynatıcıda sekme kısa süre öne alınır ve kontrol bitince önceki sekmeye dönülür. Film adına ve süresine uyan videonun gerçekten ilerlediği ve yabancı filmlerde Türkçe altyazı bilgisinin bulunduğu doğrulanırsa kaynak listelenir. Özgün dili Türkçe seçilen filmlerde altyazı gerekmez. Video.js, JW Player ve Playerjs altyazıları kendi oynatıcı arayüzlerinden de denetlenir. Kısa fragmanlar, yalnızca bilgi sunan IMDb/Filmara benzeri siteler ve “bu video kullanılamıyor” hataları elenir. Kullanıcının PC tarayıcısındaki oturum, abonelik, DRM ve bölge koşulları geçerlidir. Giriş veya satın alma otomatik yapılmaz; doğrulanamayan kaynaklar gösterilmez. Kontrol kısa bir sessiz oynatım denemesi yapar; platform geçmişine bu kısa deneme yansıyabilir.

İzle düğmesi kaynak videosunu tekrar kontrol edip sesli başlatır, tarayıcıyı ve oynatıcıyı tam ekrana geçirir. Gereken gerçek klavye etkinleştirmesi bağlı Windows kumandası üzerinden gönderilir; Escape önceki pencere düzenine döndürür. Tarayıcı politikası veya özel oynatıcı nedeniyle başlatılamayan kaynak sonuçlardan çıkarılır. Bu özellik güncel tarayıcı eklentisini ve kilidi açık Windows oturumunu gerektirir. Sonuçlar mevcut tarayıcı oturumuna bağlıdır; daha sonra değişen erişim koşulları yeniden kontrol edilir.

Diğer siteler için anahtarsız web aramasında en fazla 12 HTTPS sayfa incelenir ve oynatıcı içeren en fazla beş aday denenir. Film adıyla eşleşen oynatıcı içermeyen sayfalar elenir; kalan adaylar da aynı gerçek oynatım kontrolünden geçer. Bir sitede video bulunması güvenli olduğunu garanti etmez. Erişim engelleri, DRM veya bölge kısıtlamaları aşılmaz.

Film açılması yalnızca İzleniyor kaydı oluşturur. Güncel tarayıcı eklentisi film başlığı, süre ve gerçek oynatım ilerlemesini eşleştirip en az %90 izleme algılarsa İzlendi kaydı oluşturur; sayfada geçen süre veya ileri sarma yeterli değildir. Korumalı/özel oynatıcılarda algılama çalışmayabilir; elle işaretleme ve geri alma vardır. Geçmiş PC’de movies.sqlite3 dosyasında tutulur, telefonlar arasında ortaktır. İzleme durumu yayın platformlarının hesaplarına yazılmaz.

Veri kaynağı: [JustWatch Türkiye](https://www.justwatch.com/tr). IMDb puanı kaynaktaki IMDb alanıdır; başka bir puan IMDb diye gösterilmez. Katalog herkese açık web arayüzünü kullanır; sağlayıcı değişiklikleri erişimi etkileyebilir.
