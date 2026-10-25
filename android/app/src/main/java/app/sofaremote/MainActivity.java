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
    private LinearLayout serverRoot,keyboardBar;
    private EditText remoteEditor;
    private boolean changingEditor=false;
    private String editorPrevious="";
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
    void openServer(String address){
        if(!Discovery.localUrl(address))return;showingDevices=false;failures=0;server=address;getPreferences(0).edit().putString("server",server).apply();
        if(web!=null)web.destroy();remoteEditor=null;keyboardBar=null;web=new WebView(this);web.setBackgroundColor(Color.rgb(16,19,27));
        web.getSettings().setJavaScriptEnabled(true);web.getSettings().setDomStorageEnabled(true);web.getSettings().setAllowFileAccess(false);web.getSettings().setAllowContentAccess(false);web.getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        web.setOnLongClickListener(v->true);web.setLongClickable(false);
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
        serverRoot=new LinearLayout(this);serverRoot.setOrientation(LinearLayout.VERTICAL);
        serverRoot.addView(web,new LinearLayout.LayoutParams(-1,0,1));setContentView(serverRoot);web.loadUrl(server);
    }
    private class NativeBridge {
        @JavascriptInterface public void showKeyboard(){whenActive(()->showRemoteKeyboard());}
        @JavascriptInterface public void resetKeyboard(){runOnUiThread(()->resetRemoteEditor());}
        @JavascriptInterface public void tabMenu(int id,String title){whenActive(()->new AlertDialog.Builder(MainActivity.this).setTitle(title).setItems(new String[]{"Sekmeyi kapat"},(d,which)->emit("sofa-tab-close",Integer.toString(id))).setNegativeButton("İptal",null).show());}
        @JavascriptInterface public void vibrate(){whenActive(()->{if(web!=null)web.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS);});}
        @JavascriptInterface public void discover(){runOnUiThread(()->showDevices());}
        @JavascriptInterface public void connectionReady(){runOnUiThread(()->{failures=0;updater.publish();});}
        @JavascriptInterface public void checkUpdates(){updater.checkFromUser();}
        @JavascriptInterface public String updateInfo(){return updater.snapshot().toString();}
        @JavascriptInterface public void installUpdate(){runOnUiThread(()->updater.install());}
    }
    private void emit(String event,String json){if(web!=null)web.evaluateJavascript("window.dispatchEvent(new CustomEvent("+JSONObject.quote(event)+",{detail:"+json+"}))",null);}
    private void nativeKey(String key){emit("sofa-native-key",JSONObject.quote(key));}
    private void resetRemoteEditor(){if(remoteEditor!=null){changingEditor=true;remoteEditor.setText("");editorPrevious="";changingEditor=false;}}
    void showRemoteKeyboard(){
        if(web==null||serverRoot==null||paused)return;
        if(remoteEditor==null){
            keyboardBar=new LinearLayout(this);keyboardBar.setPadding(10,2,10,2);keyboardBar.setBackgroundColor(Color.rgb(27,32,45));
            remoteEditor=new EditText(this){
                @Override public android.view.inputmethod.InputConnection onCreateInputConnection(android.view.inputmethod.EditorInfo info){
                    android.view.inputmethod.InputConnection base=super.onCreateInputConnection(info);
                    return new android.view.inputmethod.InputConnectionWrapper(base,false){
                        @Override public boolean deleteSurroundingText(int before,int after){if(length()==0&&before>0){nativeKey("BACKSPACE");return true;}return super.deleteSurroundingText(before,after);}
                        @Override public boolean deleteSurroundingTextInCodePoints(int before,int after){if(length()==0&&before>0){nativeKey("BACKSPACE");return true;}return super.deleteSurroundingTextInCodePoints(before,after);}
                        @Override public boolean sendKeyEvent(KeyEvent e){if(length()==0&&e.getKeyCode()==KeyEvent.KEYCODE_DEL){if(e.getAction()==KeyEvent.ACTION_DOWN)nativeKey("BACKSPACE");return true;}return super.sendKeyEvent(e);}
                    };
                }
            };
            remoteEditor.setTextColor(Color.WHITE);remoteEditor.setHintTextColor(Color.LTGRAY);remoteEditor.setHint("PC’ye yaz…");remoteEditor.setSingleLine(true);
            remoteEditor.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
            remoteEditor.setImeOptions(android.view.inputmethod.EditorInfo.IME_ACTION_SEND|android.view.inputmethod.EditorInfo.IME_FLAG_NO_EXTRACT_UI);
            remoteEditor.addTextChangedListener(new android.text.TextWatcher(){
                public void beforeTextChanged(CharSequence s,int start,int count,int after){}
                public void onTextChanged(CharSequence s,int start,int before,int count){}
                public void afterTextChanged(android.text.Editable value){
                    if(changingEditor||android.view.inputmethod.BaseInputConnection.getComposingSpanStart(value)>=0)return;
                    String next=value.toString();LiveTextDelta delta=LiveTextDelta.between(editorPrevious,next);editorPrevious=next;
                    if(delta.delete==0&&delta.text.isEmpty())return;
                    try{JSONObject detail=new JSONObject();detail.put("delete",delta.delete);detail.put("text",delta.text);emit("sofa-native-edit",detail.toString());}catch(Exception ignored){}
                }
            });
            remoteEditor.setOnEditorActionListener((v,action,event)->{if(action==android.view.inputmethod.EditorInfo.IME_ACTION_SEND||(event!=null&&event.getKeyCode()==KeyEvent.KEYCODE_ENTER&&event.getAction()==KeyEvent.ACTION_DOWN)){nativeKey("ENTER");resetRemoteEditor();return true;}return false;});
            keyboardBar.addView(remoteEditor,new LinearLayout.LayoutParams(0,-2,1));Button close=new Button(this);close.setText("✕");close.setContentDescription("Telefon klavyesini kapat");
            close.setOnClickListener(v->{((android.view.inputmethod.InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(remoteEditor.getWindowToken(),0);keyboardBar.setVisibility(View.GONE);remoteEditor.clearFocus();web.requestFocus();});
            keyboardBar.addView(close,new LinearLayout.LayoutParams(60,-2));serverRoot.addView(keyboardBar,new LinearLayout.LayoutParams(-1,-2));
        }
        keyboardBar.setVisibility(View.VISIBLE);remoteEditor.requestFocus();
        remoteEditor.postDelayed(()->{if(remoteEditor==null||paused)return;android.view.inputmethod.InputMethodManager ime=(android.view.inputmethod.InputMethodManager)getSystemService(INPUT_METHOD_SERVICE);ime.showSoftInput(remoteEditor,0);if(android.os.Build.VERSION.SDK_INT>=30&&remoteEditor.getWindowInsetsController()!=null)remoteEditor.getWindowInsetsController().show(WindowInsets.Type.ime());},150);
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
