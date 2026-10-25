package app.sofaremote;

import android.app.*;
import android.os.Bundle;
import android.graphics.Color;
import android.webkit.*;
import android.widget.*;
import android.view.*;
import android.net.Uri;
import java.net.URI;
import org.json.JSONObject;

public class MainActivity extends Activity {
    private WebView web;
    private LinearLayout deviceList;
    private String server="";
    private boolean scanning=false,showingDevices=false,paused=false;
    private int failures=0;
    private final android.os.Handler handler=new android.os.Handler(android.os.Looper.getMainLooper());
    private UpdateManager updater;
    private android.content.BroadcastReceiver downloadReceiver;
    @Override public void onCreate(Bundle state){
        super.onCreate(state);getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        updater=new UpdateManager(this);
        downloadReceiver=new android.content.BroadcastReceiver(){@Override public void onReceive(android.content.Context c,android.content.Intent i){updater.completed(i.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID,-1));}};
        if(android.os.Build.VERSION.SDK_INT>=33)registerReceiver(downloadReceiver,new android.content.IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE),android.content.Context.RECEIVER_EXPORTED);
        else registerReceiver(downloadReceiver,new android.content.IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE));
        server=getPreferences(0).getString("server","");
        if(Discovery.localUrl(server)){showConnecting();tryLast();}else showDevices();
        updater.check();
    }
    private void showConnecting(){TextView text=new TextView(this);text.setText("Sofa Remote\nBilgisayara bağlanıyor…");text.setTextColor(Color.WHITE);text.setBackgroundColor(Color.rgb(16,19,27));text.setGravity(Gravity.CENTER);setContentView(text);}
    private void tryLast(){new Thread(()->{JSONObject info=Discovery.probe(server);runOnUiThread(()->{if(isFinishing())return;if(info!=null)openServer(server);else showDevices();});},"sofa-reconnect").start();}
    private void showDevices(){
        showingDevices=true;
        if(web!=null){web.evaluateJavascript("window.dispatchEvent(new Event('sofa-pause'))",null);web.destroy();web=null;}
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(30,50,30,20);root.setBackgroundColor(Color.rgb(16,19,27));
        TextView heading=new TextView(this);heading.setText("sofa remote\nBilgisayarını seç");heading.setTextSize(26);heading.setTextColor(Color.WHITE);root.addView(heading);
        TextView help=new TextView(this);help.setText("Aynı yerel ağdaki Sofa Remote bilgisayarları aranıyor. Bağlanmak için dokun.");help.setTextColor(Color.LTGRAY);root.addView(help);
        ScrollView scroll=new ScrollView(this);deviceList=new LinearLayout(this);deviceList.setOrientation(LinearLayout.VERTICAL);scroll.addView(deviceList);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        Button scan=new Button(this);scan.setText("↻ Ağı yeniden tara");scan.setOnClickListener(v->scanDevices());root.addView(scan);
        Button manual=new Button(this);manual.setText("Adresle bağlan");manual.setOnClickListener(v->askAddress());root.addView(manual);
        Button updates=new Button(this);updates.setText("Güncelleme");updates.setOnClickListener(v->updater.showUpdates());root.addView(updates);setContentView(root);scanDevices();
    }
    private void scanDevices(){if(scanning)return;scanning=true;deviceList.removeAllViews();Discovery.scan(this,(address,name)->runOnUiThread(()->{if(!showingDevices||isFinishing())return;Button b=new Button(this);b.setText(name+"\n"+address);b.setOnClickListener(v->openServer(address));deviceList.addView(b);}),()->runOnUiThread(()->{scanning=false;if(showingDevices&&deviceList.getChildCount()==0){TextView text=new TextView(this);text.setText("Bilgisayar bulunamadı. Windows’ta Sofa Remote açık olmalı; özel ağ güvenlik duvarı TCP 8765 / UDP 8766 bağlantısına izin vermeli.");text.setTextColor(Color.LTGRAY);deviceList.addView(text);}}));}
    private void askAddress(){EditText input=new EditText(this);input.setSingleLine(true);input.setHint("http://192.168.1.20:8765");input.setText(server);new AlertDialog.Builder(this).setTitle("Bilgisayar adresi").setView(input).setPositiveButton("Bağlan",(d,w)->{String value=input.getText().toString().trim().replaceAll("/+$","");if(!Discovery.localUrl(value)){Toast.makeText(this,"Yerel ağ IPv4 adresi gir",Toast.LENGTH_LONG).show();return;}server=value;showConnecting();tryLast();}).setNegativeButton("İptal",null).show();}
    private void openServer(String address){
        if(!Discovery.localUrl(address))return;showingDevices=false;failures=0;server=address;getPreferences(0).edit().putString("server",server).apply();
        if(web!=null)web.destroy();web=new WebView(this);web.setBackgroundColor(Color.rgb(16,19,27));
        web.getSettings().setJavaScriptEnabled(true);web.getSettings().setDomStorageEnabled(true);web.getSettings().setAllowFileAccess(false);web.getSettings().setAllowContentAccess(false);web.getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        web.addJavascriptInterface(new NativeBridge(),"SofaNative");
        web.setWebChromeClient(new WebChromeClient(){@Override public boolean onJsConfirm(WebView v,String url,String message,JsResult result){new AlertDialog.Builder(MainActivity.this).setMessage(message).setPositiveButton("Onayla",(d,w)->result.confirm()).setNegativeButton("İptal",(d,w)->result.cancel()).setOnCancelListener(d->result.cancel()).show();return true;}});
        web.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){
                try {URI target=new URI(request.getUrl().toString());if(new URI(server).resolve("/").equals(target.resolve("/")))return false;
                    if("https".equals(target.getScheme())&&request.isForMainFrame())startActivity(new android.content.Intent(android.content.Intent.ACTION_VIEW,request.getUrl()));
                }catch(Exception ignored){}return true;
            }
            @Override public void onReceivedError(WebView v,WebResourceRequest request,WebResourceError error){if(request.isForMainFrame()&&!showingDevices)handler.postDelayed(()->{if(web!=null&&!showingDevices){if(++failures>=2)showDevices();else web.reload();}},1500);}
        });
        setContentView(web);web.loadUrl(server);
    }
    private class NativeBridge {
        @JavascriptInterface public void showKeyboard(){whenActive(()->{if(web!=null){web.requestFocus();web.postDelayed(()->{if(web!=null&&!paused){android.view.inputmethod.InputMethodManager ime=(android.view.inputmethod.InputMethodManager)getSystemService(INPUT_METHOD_SERVICE);ime.showSoftInput(web,0);}},120);}});}
        @JavascriptInterface public void vibrate(){whenActive(()->{if(web!=null)web.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS);});}
        @JavascriptInterface public void discover(){runOnUiThread(()->showDevices());}
        @JavascriptInterface public void connectionReady(){runOnUiThread(()->{failures=0;updater.publish();});}
        @JavascriptInterface public void checkUpdates(){updater.checkFromUser();}
        @JavascriptInterface public String updateInfo(){return updater.snapshot().toString();}
        @JavascriptInterface public void installUpdate(){runOnUiThread(()->updater.install());}
    }
    void whenActive(Runnable action){runOnUiThread(()->{if(!paused&&!isFinishing())action.run();});}
    void updateStatus(JSONObject status){runOnUiThread(()->{if(web!=null)web.evaluateJavascript("window.dispatchEvent(new CustomEvent('sofa-update',{detail:"+status.toString()+"}))",null);});}
    @Override public boolean dispatchKeyEvent(KeyEvent event){int key=event.getKeyCode();if(!paused&&!showingDevices&&web!=null&&(key==KeyEvent.KEYCODE_VOLUME_UP||key==KeyEvent.KEYCODE_VOLUME_DOWN)){
        if(event.getAction()==KeyEvent.ACTION_DOWN)web.evaluateJavascript("window.dispatchEvent(new CustomEvent('sofa-volume',{detail:"+(key==KeyEvent.KEYCODE_VOLUME_UP?1:-1)+"}))",null);return true;}return super.dispatchKeyEvent(event);}
    @Override public void onBackPressed(){if(!showingDevices)showDevices();else super.onBackPressed();}
    @Override protected void onResume(){super.onResume();paused=false;if(updater!=null)updater.resume();}
    @Override protected void onPause(){paused=true;if(web!=null)web.evaluateJavascript("window.dispatchEvent(new Event('sofa-pause'))",null);super.onPause();}
    @Override protected void onDestroy(){handler.removeCallbacksAndMessages(null);if(downloadReceiver!=null)unregisterReceiver(downloadReceiver);if(web!=null)web.destroy();super.onDestroy();}
}
