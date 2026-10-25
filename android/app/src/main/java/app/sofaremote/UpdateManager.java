package app.sofaremote;

import android.app.*;
import android.content.*;
import android.net.Uri;
import android.os.Environment;
import android.provider.Settings;
import org.json.*;
import java.io.*;
import java.net.*;
import java.security.MessageDigest;

final class UpdateManager {
    private final MainActivity activity;
    private final android.content.SharedPreferences prefs;
    private final String current;
    private volatile boolean checking=false,verifying=false;
    private volatile String message="Güncellemeler kontrol ediliyor",latest="",state="idle";
    private AlertDialog dialog;
    private static final String RELEASE="https://api.github.com/repos/Univadmin/sofa-remote/releases/latest";
    UpdateManager(MainActivity activity){this.activity=activity;prefs=activity.getSharedPreferences("updates",0);String version="";try{version=activity.getPackageManager().getPackageInfo(activity.getPackageName(),0).versionName;}catch(Exception ignored){}current=version;latest=current;}
    JSONObject snapshot(){JSONObject json=new JSONObject();try{json.put("current",current).put("latest",latest).put("state",state).put("message",message).put("ready",prefs.getBoolean("ready",false));}catch(Exception ignored){}return json;}
    void publish(){activity.updateStatus(snapshot());activity.runOnUiThread(()->{if(dialog!=null&&dialog.isShowing())dialog.setMessage(versionText());});}
    private void status(String phase,String text){state=phase;message=text;publish();}
    private String versionText(){return "Android v"+current+" · Son sürüm v"+latest+"\n\n"+message;}
    static byte[] limitedRead(InputStream stream,int max)throws IOException{ByteArrayOutputStream output=new ByteArrayOutputStream();byte[] buffer=new byte[4096];int n;while((n=stream.read(buffer))!=-1){if(output.size()+n>max)throw new IOException("Yanıt çok büyük");output.write(buffer,0,n);}return output.toByteArray();}
    void checkFromUser(){prefs.edit().remove("offered").apply();check();}
    synchronized void check(){
        if(checking){publish();return;}checking=true;
        new Thread(()->{HttpURLConnection connection=null;try{
            status("checking","Güncellemeler kontrol ediliyor");connection=(HttpURLConnection)new URL(RELEASE).openConnection();connection.setConnectTimeout(10000);connection.setReadTimeout(10000);connection.setRequestProperty("User-Agent","SofaRemote-Android");
            if(connection.getResponseCode()==404){status("current","Henüz yeni sürüm yok");return;}
            if(connection.getResponseCode()!=200)throw new IOException("GitHub bağlantısı kurulamadı");
            JSONObject release=new JSONObject(new String(limitedRead(connection.getInputStream(),500000),java.nio.charset.StandardCharsets.UTF_8));latest=release.getString("tag_name").replaceFirst("^v","");
            if(compare(latest,current)<=0){prefs.edit().putBoolean("ready",false).remove("download").remove("pendingInstall").apply();status("current","Güncel");return;}
            JSONArray assets=release.getJSONArray("assets");JSONObject apk=null;for(int i=0;i<assets.length();i++)if("SofaRemote-Android.apk".equals(assets.getJSONObject(i).optString("name")))apk=assets.getJSONObject(i);
            if(apk==null)throw new IOException("APK henüz yayımlanmadı");String url=apk.getString("browser_download_url"),digest=apk.optString("digest");
            URI uri=new URI(url);if(!"https".equals(uri.getScheme())||!"github.com".equals(uri.getHost())||!uri.getPath().startsWith("/Univadmin/sofa-remote/releases/download/")||!digest.matches("sha256:[a-fA-F0-9]{64}"))throw new IOException("Güncelleme doğrulanamadı");
            if(latest.equals(prefs.getString("version",""))){long id=prefs.getLong("download",-1);if(id!=-1){completed(id);return;}}
            File folder=activity.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);if(folder==null)throw new IOException("İndirme klasörü açılamadı");File file=new File(folder,"update-"+latest+".apk");if(file.exists()&&!file.delete())throw new IOException("Eski indirme silinemedi");
            DownloadManager.Request request=new DownloadManager.Request(Uri.parse(url)).setTitle("Sofa Remote v"+latest).setDescription("Uygulama güncellemesi").setMimeType("application/vnd.android.package-archive").setAllowedNetworkTypes(DownloadManager.Request.NETWORK_WIFI).setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED).setDestinationInExternalFilesDir(activity,Environment.DIRECTORY_DOWNLOADS,file.getName());
            long id=((DownloadManager)activity.getSystemService(Context.DOWNLOAD_SERVICE)).enqueue(request);
            prefs.edit().putString("version",latest).putString("digest",digest.substring(7)).putString("path",file.getAbsolutePath()).putLong("download",id).putBoolean("ready",false).remove("offered").apply();status("downloading","v"+latest+" Wi-Fi üzerinden indiriliyor; ardından kurulum onayı açılacak");
        }catch(Exception e){status("error",e.getMessage()==null?"Güncelleme kontrolü başarısız":e.getMessage());}finally{if(connection!=null)connection.disconnect();checking=false;}},"sofa-updates").start();
    }
    static int compare(String a,String b){if(!a.matches("\\d+\\.\\d+\\.\\d+")||!b.matches("\\d+\\.\\d+\\.\\d+"))return 0;String[] x=a.split("\\."),y=b.split("\\.");for(int i=0;i<3;i++){int c=Integer.compare(Integer.parseInt(x[i]),Integer.parseInt(y[i]));if(c!=0)return c;}return 0;}
    synchronized void completed(long id){
        if(id!=prefs.getLong("download",-2)||verifying)return;verifying=true;
        new Thread(()->{try{
            DownloadManager dm=(DownloadManager)activity.getSystemService(Context.DOWNLOAD_SERVICE);
            try(android.database.Cursor c=dm.query(new DownloadManager.Query().setFilterById(id))){if(c==null||!c.moveToFirst()){prefs.edit().remove("download").apply();return;}int result=c.getInt(c.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS));
                if(result==DownloadManager.STATUS_FAILED){prefs.edit().remove("download").apply();status("error","İndirme başarısız; tekrar kontrol et");return;}
                if(result!=DownloadManager.STATUS_SUCCESSFUL){status("downloading",result==DownloadManager.STATUS_PAUSED?"Wi-Fi bağlantısı bekleniyor":"Güncelleme indiriliyor");return;}}
            latest=prefs.getString("version",latest);status("verifying","İndirilen APK doğrulanıyor");
            File file=new File(prefs.getString("path",""));MessageDigest digest=MessageDigest.getInstance("SHA-256");try(InputStream stream=new FileInputStream(file)){byte[] buffer=new byte[65536];int n;while((n=stream.read(buffer))!=-1)digest.update(buffer,0,n);}StringBuilder hex=new StringBuilder();for(byte value:digest.digest())hex.append(String.format("%02x",value&255));
            if(!hex.toString().equalsIgnoreCase(prefs.getString("digest",""))){file.delete();throw new IOException("APK doğrulaması başarısız");}
            android.content.pm.PackageInfo info=activity.getPackageManager().getPackageArchiveInfo(file.getAbsolutePath(),0);
            if(info==null||!activity.getPackageName().equals(info.packageName)||!latest.equals(info.versionName))throw new IOException("APK paket veya sürüm bilgisi uyuşmuyor");
            prefs.edit().putBoolean("ready",true).apply();status("ready","v"+latest+" hazır; Android kurulum onayı açılıyor");offerInstall();
        }catch(Exception e){prefs.edit().remove("download").putBoolean("ready",false).apply();status("error",e.getMessage());}finally{verifying=false;}},"sofa-verify").start();
    }
    private void offerInstall(){activity.whenActive(()->{String version=prefs.getString("version","");if(!prefs.getBoolean("ready",false)||version.equals(prefs.getString("offered","")))return;prefs.edit().putString("offered",version).apply();if(dialog!=null)dialog.dismiss();install();});}
    void resume(){
        if(prefs.getBoolean("pendingInstall",false)&&activity.getPackageManager().canRequestPackageInstalls()){prefs.edit().putBoolean("pendingInstall",false).apply();install();return;}
        if(prefs.getBoolean("ready",false)){offerInstall();return;}
        long id=prefs.getLong("download",-1);if(id!=-1)completed(id);
    }
    void showUpdates(){dialog=new AlertDialog.Builder(activity).setTitle("Güncelleme").setMessage(versionText()).setPositiveButton("Güncellemeleri kontrol et",(d,w)->checkFromUser()).setNegativeButton("Kapat",null).create();dialog.show();}
    void install(){
        if(!prefs.getBoolean("ready",false)){checkFromUser();return;}
        if(!activity.getPackageManager().canRequestPackageInstalls()){
            prefs.edit().putBoolean("pendingInstall",true).apply();status("permission","Sofa Remote için uygulama yükleme iznini aç; geri döndüğünde kurulum devam edecek");
            activity.startActivity(new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,Uri.parse("package:"+activity.getPackageName())));return;
        }
        try{prefs.edit().putBoolean("pendingInstall",false).apply();status("installing","Android’in kurulum ekranında Güncelle’ye dokun");Uri uri=Uri.parse("content://"+activity.getPackageName()+".updates/update.apk");Intent intent=new Intent(Intent.ACTION_VIEW).setDataAndType(uri,"application/vnd.android.package-archive").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);activity.startActivity(intent);}
        catch(Exception e){status("error","Kurulum açılamadı: "+e.getMessage());}
    }
}
