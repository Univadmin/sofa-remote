package tr.burak.sofaremote;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.graphics.Color;
import android.webkit.*;
import android.widget.*;
import android.view.ViewGroup;
import android.view.WindowManager;
import java.net.URI;

/** Thin mobile shell: controls are served by the paired local Windows host. */
public class MainActivity extends Activity {
    private WebView web;
    private String server = "";
    static boolean localUrl(String value) {
        try {
            URI uri = new URI(value);
            if (!("http".equals(uri.getScheme()) || "https".equals(uri.getScheme())) || uri.getUserInfo()!=null) return false;
            if (uri.getRawQuery()!=null || uri.getRawFragment()!=null) return false;
            String h=uri.getHost(); if(h==null)return false;
            String[] parts=h.split("\\."); if(parts.length!=4)return false;
            int[] n=new int[4]; for(int i=0;i<4;i++){n[i]=Integer.parseInt(parts[i]);if(n[i]<0||n[i]>255)return false;}
            return n[0]==10 || (n[0]==192&&n[1]==168) || (n[0]==172&&n[1]>=16&&n[1]<=31);
        } catch(Exception e){ return false; }
    }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        LinearLayout root=new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL);root.setBackgroundColor(Color.rgb(17,18,26));
        Button change=new Button(this);change.setText("Sofa Remote · Bilgisayar adresini değiştir");change.setOnClickListener(v->askServer());root.addView(change);
        web=new WebView(this);web.setBackgroundColor(Color.rgb(17,18,26));
        web.getSettings().setJavaScriptEnabled(true);web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setAllowFileAccess(false);web.getSettings().setAllowContentAccess(false);
        web.getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        web.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){
                try {return !new URI(server).resolve("/").equals(new URI(request.getUrl().toString()).resolve("/"));}catch(Exception e){return true;}
            }
        });
        root.addView(web,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,0,1));setContentView(root);
        server=getPreferences(0).getString("server","");if(localUrl(server))web.loadUrl(server);else askServer();
    }
    private void askServer(){
        EditText address=new EditText(this);address.setSingleLine(true);address.setHint("http://192.168.1.20:8765");address.setText(server);address.setTextColor(Color.BLACK);
        new AlertDialog.Builder(this).setTitle("Windows bilgisayarının adresi").setMessage("Sofa Remote penceresindeki yerel IPv4 adresini gir. Aynı Wi-Fi ağında olmalısın.").setView(address).setPositiveButton("Bağlan",(d,w)->{
            String value=address.getText().toString().trim();
            if(!localUrl(value)){Toast.makeText(this,"10.x, 172.16–31.x veya 192.168.x yerel IPv4 adresi gir",Toast.LENGTH_LONG).show();askServer();return;}
            server=value;CookieManager.getInstance().removeAllCookies(null);web.clearCache(true);
            getPreferences(0).edit().putString("server",server).apply();web.loadUrl(server);
        }).setNegativeButton("İptal",null).show();
    }
    @Override public void onBackPressed(){if(web.canGoBack())web.goBack();else super.onBackPressed();}
    @Override protected void onPause(){super.onPause();web.evaluateJavascript("window.dispatchEvent(new Event('sofa-pause'))",null);}
    @Override protected void onDestroy(){web.destroy();super.onDestroy();}
}
