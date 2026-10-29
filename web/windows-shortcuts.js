'use strict';
// Windows 10 system and File Explorer shortcuts. Key names are server protocol tokens.
// Reference: https://support.microsoft.com/en-au/accessibility/windows/keyboard-shortcuts-in-windows
const windowsShortcutGroups={
 'Genel ve metin':[
 ['Kopyala','CTRL+C'],['Kes','CTRL+X'],['Yapıştır','CTRL+V'],['Geri al','CTRL+Z'],['Yinele','CTRL+Y'],['Tümünü seç','CTRL+A'],['Bul','CTRL+F'],
 ['Kopyala (alternatif)','CTRL+INSERT'],['Yapıştır (alternatif)','SHIFT+INSERT'],['Önceki sözcüğü sil','CTRL+BACKSPACE'],['Sonraki sözcüğü sil','CTRL+DELETE'],
 ['Önceki sözcük','CTRL+LEFT'],['Sonraki sözcük','CTRL+RIGHT'],['Önceki paragraf','CTRL+UP'],['Sonraki paragraf','CTRL+DOWN'],
 ['Belge başı','CTRL+HOME'],['Belge sonu','CTRL+END'],['Satır başı','HOME'],['Satır sonu','END'],['Bir sayfa yukarı','PAGEUP'],['Bir sayfa aşağı','PAGEDOWN'],
 ['Soldaki karakteri seç','SHIFT+LEFT'],['Sağdaki karakteri seç','SHIFT+RIGHT'],['Üst satırı seç','SHIFT+UP'],['Alt satırı seç','SHIFT+DOWN'],
 ['Önceki sözcüğü seç','CTRL+SHIFT+LEFT'],['Sonraki sözcüğü seç','CTRL+SHIFT+RIGHT'],['Önceki paragrafı seç','CTRL+SHIFT+UP'],['Sonraki paragrafı seç','CTRL+SHIFT+DOWN'],
 ['Satır başına kadar seç','SHIFT+HOME'],['Satır sonuna kadar seç','SHIFT+END'],['Belge başına kadar seç','CTRL+SHIFT+HOME'],['Belge sonuna kadar seç','CTRL+SHIFT+END'],
 ['Önceki sayfayı seç','SHIFT+PAGEUP'],['Sonraki sayfayı seç','SHIFT+PAGEDOWN'],['Sil','DELETE'],['Geri sil','BACKSPACE'],['İptal / kapat','ESC'],['Seçimi onayla','ENTER']
 ],
 'Pencereler ve masaüstü':[
 ['Uygulama değiştir','ALT+TAB'],['Açık pencereleri seç','CTRL+ALT+TAB'],['Açılış sırasıyla pencere değiştir','ALT+ESC'],['Pencereyi kapat','ALT+F4'],['Belgeyi kapat','CTRL+F4'],
 ['Pencere menüsü','ALT+SPACE'],['Masaüstünü göster / gizle','WIN+D'],['Görev görünümü','WIN+TAB'],['Pencereyi büyüt','WIN+UP'],['Pencereyi küçült / geri al','WIN+DOWN'],
 ['Sola yasla','WIN+LEFT'],['Sağa yasla','WIN+RIGHT'],['Diğer pencereleri küçült / geri al','WIN+HOME'],['Tüm pencereleri küçült','WIN+M'],['Küçültülen pencereleri geri getir','WIN+SHIFT+M'],
 ['Önceki monitöre taşı','WIN+SHIFT+LEFT'],['Sonraki monitöre taşı','WIN+SHIFT+RIGHT'],['Dikey olarak büyüt','WIN+SHIFT+UP'],['Dikey boyutu geri al','WIN+SHIFT+DOWN'],
 ['Yeni sanal masaüstü','WIN+CTRL+D'],['Soldaki sanal masaüstü','WIN+CTRL+LEFT'],['Sağdaki sanal masaüstü','WIN+CTRL+RIGHT'],['Sanal masaüstünü kapat','WIN+CTRL+F4'],
 ['Yenile','F5'],['Yenile (alternatif)','CTRL+R'],['Ekran öğeleri arasında dolaş','F6'],['Menü çubuğu','F10'],['Bağlam menüsü','SHIFT+F10'],
 ['Geri git','ALT+LEFT'],['İleri git','ALT+RIGHT'],['Bir ekran yukarı','ALT+PAGEUP'],['Bir ekran aşağı','ALT+PAGEDOWN']
 ],
 'Windows ve sistem':[
 ['Başlat menüsü','WIN'],['Başlat (alternatif)','CTRL+ESC'],['Windows araması','WIN+S'],['Ayarlar','WIN+I'],['Dosya Gezgini','WIN+E'],['Çalıştır','WIN+R'],
 ['Görev Yöneticisi','CTRL+SHIFT+ESC'],['Hızlı bağlantı menüsü','WIN+X'],['Bildirim / işlem merkezi','WIN+A'],['Pano geçmişi','WIN+V','Windows ayarlarında pano geçmişi açık olmalı.'],
 ['Bilgisayarı kilitle','WIN+L'],['Ekran yansıtma','WIN+P'],['Kablosuz ekran / cihaz bağlantısı','WIN+K'],['Ekran yönünü kilitle','WIN+O','Destekleyen cihazlarda.'],
 ['Erişim Kolaylığı ayarları','WIN+U'],['Ekran Klavyesi','WIN+CTRL+O'],['Ekran Okuyucusu','WIN+CTRL+ENTER'],['Büyüteç aç / yakınlaştır','WIN+ADD'],['Büyüteç uzaklaştır','WIN+SUBTRACT'],['Büyüteci kapat','WIN+ESC'],
 ['Renk filtrelerini değiştir','WIN+CTRL+C','Kısayol Windows ayarlarında etkin olmalı.'],['Emoji paneli','WIN+PERIOD'],['Emoji paneli (alternatif)','WIN+SEMICOLON'],
 ['Giriş dili değiştir','WIN+SPACE'],['Önceki giriş dili','WIN+SHIFT+SPACE'],['Önceki giriş yöntemine dön','WIN+CTRL+SPACE'],['Klavye düzenini değiştir','CTRL+SHIFT'],
 ['Ekran alıntısı','WIN+SHIFT+S'],['Tüm ekranı panoya al','PRINTSCREEN'],['Etkin pencereyi panoya al','ALT+PRINTSCREEN'],['Ekran görüntüsünü dosyaya kaydet','WIN+PRINTSCREEN'],
 ['Oyun çubuğu','WIN+G'],['Dikte','WIN+H','Dil ve Windows ayarlarına bağlıdır.'],['Geri Bildirim Merkezi','WIN+F'],['Hızlı Yardım','WIN+CTRL+Q'],
 ['Sistem özellikleri','WIN+PAUSE'],['Tarih / saat paneli','WIN+ALT+D'],['Bildirimler arasında geç','WIN+SHIFT+V'],['Windows ipucuna odaklan','WIN+SHIFT+A'],
 ['Ekran sürücüsünü uyandır','WIN+CTRL+SHIFT+B'],['Ağda bilgisayar ara','WIN+CTRL+F'],['Karma Gerçeklik girişini değiştir','WIN+Y','Windows Mixed Reality gerektirir.'],
 ['Tam ekran uygulama komutları','WIN+Z','Destekleyen Windows 10 uygulamalarında.'],['IME dönüşümü','WIN+SLASH','Uyumlu giriş yöntemi gerekir.'],['Çince giriş yöntemini değiştir','CTRL+SPACE','Çince IME gerekir.'],
 ['Güvenlik ekranı','CTRL+ALT+DELETE','Windows, uygulamadan bu tuş birleşiminin gönderilmesine izin vermez.',true],
 ['Cortana dinleme','WIN+C','Eski Windows 10 özelliği; güncel sistemlerde kullanımdan kaldırılmış olabilir.'],['Uygulama düğmeleri menüsü','WIN+SHIFT+C','Yalnızca destekleyen eski uygulamalarda.'],
 ['Kişi bildirimi paneli','WIN+CTRL+V','Eski Windows 10 sürümlerine bağlıdır.']
 ],
 'Dosya Gezgini':[
 ['Yeni pencere','CTRL+N'],['Pencereyi kapat','CTRL+W'],['Yeni klasör','CTRL+SHIFT+N'],['Yeniden adlandır','F2'],['Özellikler','ALT+ENTER'],
 ['Adres çubuğu','ALT+D'],['Adres çubuğu (alternatif)','CTRL+L'],['Adres geçmişi','F4'],['Dosya / klasör ara','CTRL+F'],['Arama kutusu','CTRL+E'],['Arama (F3)','F3'],
 ['Üst klasör','ALT+UP'],['Önceki klasör','ALT+LEFT'],['Önceki klasör (alternatif)','BACKSPACE'],['Sonraki klasör','ALT+RIGHT'],
 ['Önizleme bölmesi','ALT+P'],['Gezinti ağacında üst klasörleri göster','CTRL+SHIFT+E'],['Alt öğeleri aç / seç','RIGHT'],['Ağacı daralt / üst öğeyi seç','LEFT'],
 ['Listenin başı','HOME'],['Listenin sonu','END'],['Tam ekran','F11'],['Yenile','F5'],['Geri Dönüşüm Kutusu’na taşı','DELETE'],['Sil (alternatif)','CTRL+D'],
 ['Kalıcı sil','SHIFT+DELETE','Seçili öğeler Geri Dönüşüm Kutusu’na taşınmadan silinir.'],
 ['Alt klasörleri genişlet','MULTIPLY','Sayısal tuş takımı * komutudur.'],['Seçili klasörü genişlet','ADD','Sayısal tuş takımı + komutudur.'],['Seçili klasörü daralt','SUBTRACT','Sayısal tuş takımı − komutudur.'],
 ['Sütunları içeriğe sığdır','CTRL+ADD'],
 ...['Çok büyük simgeler','Büyük simgeler','Orta simgeler','Küçük simgeler','Liste','Ayrıntılar','Döşemeler','İçerik'].map((name,i)=>['Görünüm: '+name,'CTRL+SHIFT+'+(i+1)]),
 ['Tek tek öğe seçme','CTRL + ok tuşları, ardından SPACE','Ctrl basılıyken hedef öğeye gidip Boşluk’a basılır.',true],
 ['Simge boyutunu değiştir','CTRL + mouse tekerleği','Ctrl basılıyken tekerlek kaydırılır.',true],
 ['Dosyayı kopyalayarak sürükle','CTRL + sürükle','Ctrl basılı tutularak dosya sürüklenir.',true],['Dosyayı taşıyarak sürükle','SHIFT + sürükle','Shift basılı tutularak dosya sürüklenir.',true],['Kısayol oluşturarak sürükle','ALT + sürükle','Alt basılı tutularak dosya sürüklenir.',true]
 ],
 'Görev çubuğu':[
 ['Görev çubuğunda ilerle','WIN+T'],['Bildirim alanına odaklan','WIN+B'],['Görev çubuğu ayarları','WIN+ALT+ENTER','Görev çubuğu öğesi odaktayken.'],
 ...Array.from({length:10},(_,i)=>{const n=String((i+1)%10),position=i+1;return [
  ['Sabit uygulama '+position,'WIN+'+n],['Uygulama '+position+': yeni pencere','WIN+SHIFT+'+n],['Uygulama '+position+': son pencere','WIN+CTRL+'+n],
  ['Uygulama '+position+': atlama listesi','WIN+ALT+'+n],['Uygulama '+position+': yönetici başlat','WIN+CTRL+SHIFT+'+n]
 ]}).flat(),
 ['Yeni uygulama örneği','SHIFT + görev çubuğuna tıkla','Görev çubuğu simgesine Shift ile tıklanır.',true],['Yönetici olarak başlat','CTRL + SHIFT + görev çubuğuna tıkla','Görev çubuğu simgesine Ctrl+Shift ile tıklanır.',true],
 ['Pencere menüsü','SHIFT + görev çubuğuna sağ tıkla','Görev çubuğu simgesine Shift ile sağ tıklanır.',true],['Grup pencerelerini sırayla seç','CTRL + gruba tıkla','Gruplanmış görev çubuğu simgesine Ctrl ile tıklanır.',true]
 ],
 'İletişim kutuları ve ayarlar':[
 ['Sonraki seçenek','TAB'],['Önceki seçenek','SHIFT+TAB'],['Sonraki sekme','CTRL+TAB'],['Önceki sekme','CTRL+SHIFT+TAB'],['Odaklı kutuyu işaretle / kaldır','SPACE'],['Açılır listeyi göster','F4'],
 ...Array.from({length:9},(_,i)=>['İletişim sekmesi '+(i+1),'CTRL+'+(i+1)]),
 ['Kaydet / Aç kutusunda üst klasör','BACKSPACE','Klasör seçiliyken.'],['Ayarlar içinde geri','BACKSPACE'],
 ['Menü komutu','ALT + altı çizili harf','Menüde görünen altı çizili harf, arayüz diline göre değişir.',true]
 ]
};
const windowsShortcuts=Object.entries(windowsShortcutGroups).flatMap(([group,rows])=>rows.map(([name,combo,note='',manual=false])=>({group,name,combo,note,manual,keys:manual?[]:combo.split('+')})));
const commonWindowsCombos=new Set(['CTRL+C','CTRL+X','CTRL+V','CTRL+Z','CTRL+A','ALT+TAB','ALT+F4','WIN+D','WIN+E','CTRL+SHIFT+ESC','WIN+SHIFT+S','WIN+V','CTRL+SHIFT+N','F2']);
function showWindowsShortcuts(){
 sheet('Windows kısayolları',`<div class="windows-shortcuts-toolbar"><input data-windows-filter aria-label="Windows kısayolu ara" placeholder="Kısayol veya işlem ara…"><select data-windows-group aria-label="Kısayol kategorisi"><option value="common">Sık kullanılanlar</option><option value="all">Tüm kısayollar</option>${Object.keys(windowsShortcutGroups).map(group=>`<option>${escaped(group)}</option>`).join('')}</select></div><p class="hint" data-windows-count></p><div data-windows-list></div><p class="hint">Komut odaktaki Windows penceresine gönderilir. Bazı kısayollar Windows sürümü, dil ve ayarlara bağlıdır. “Elle” yazan birleşimler açıklama içindir. <a href="https://support.microsoft.com/en-au/accessibility/windows/keyboard-shortcuts-in-windows" target="_blank" rel="noopener noreferrer">Microsoft kısayol belgesi</a></p>`);
 const root=$('#sheet-body'),filter=root.querySelector('[data-windows-filter]'),category=root.querySelector('[data-windows-group]'),list=root.querySelector('[data-windows-list]');
 const render=()=>{
  const query=filter.value.trim().toLocaleLowerCase('tr');list.replaceChildren();const seen=new Set();
  const rows=windowsShortcuts.filter(item=>{
   if(query){if(!(item.name+' '+item.combo+' '+item.group).toLocaleLowerCase('tr').includes(query))return false}
   else if(category.value==='common'&&!commonWindowsCombos.has(item.combo))return false;
   if(category.value!=='common'&&category.value!=='all'&&category.value!==item.group)return false;
   const id=item.name+'|'+item.combo;if(seen.has(id))return false;seen.add(id);return true;
  });
  root.querySelector('[data-windows-count]').textContent=rows.length+' kısayol · Çalıştırmak için tuş birleşimine dokun.';
  for(const item of rows){
   const row=document.createElement('div');row.className='windows-shortcut';row.setAttribute('aria-disabled',String(item.manual));const text=document.createElement('div'),name=document.createElement('strong'),description=document.createElement('small');name.textContent=item.name;description.textContent=item.group+(item.note?' · '+item.note:'');text.append(name,description);
   const button=document.createElement('button');button.className='small';button.textContent=item.combo+(item.manual?' · Elle':'');button.disabled=item.manual;button.setAttribute('aria-label',item.name+' · '+item.combo);button.onclick=()=>run({type:'keys',keys:item.keys}).catch(error=>toast(error.message));row.append(text,button);list.append(row);
  }
 };
 filter.oninput=render;category.onchange=render;render();
}
if(typeof module!=='undefined')module.exports={windowsShortcuts};
