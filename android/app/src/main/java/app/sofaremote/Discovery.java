package app.sofaremote;

import android.content.Context;
import android.net.wifi.WifiManager;
import org.json.JSONObject;
import java.net.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.BiConsumer;

final class Discovery {
    static final String PROBE="SOFA_REMOTE_DISCOVER_V1";
    static boolean localUrl(String value) {
        try {
            URI uri=new URI(value);
            if(!("http".equals(uri.getScheme())||"https".equals(uri.getScheme()))||uri.getUserInfo()!=null||uri.getRawQuery()!=null||uri.getRawFragment()!=null)return false;
            String h=uri.getHost();if(h==null)return false;String[] p=h.split("\\.");if(p.length!=4)return false;
            int[] n=new int[4];for(int i=0;i<4;i++){n[i]=Integer.parseInt(p[i]);if(n[i]<0||n[i]>255)return false;}
            return n[0]==10||(n[0]==192&&n[1]==168)||(n[0]==172&&n[1]>=16&&n[1]<=31);
        }catch(Exception e){return false;}
    }
    static JSONObject probe(String base) {
        if(!localUrl(base))return null;
        HttpURLConnection connection=null;
        try {
            connection=(HttpURLConnection)new URL(base+"/api/info").openConnection();connection.setConnectTimeout(650);connection.setReadTimeout(650);connection.setInstanceFollowRedirects(false);
            if(connection.getResponseCode()!=200)return null;
            byte[] bytes=UpdateManager.limitedRead(connection.getInputStream(),8192);
            JSONObject info=new JSONObject(new String(bytes,java.nio.charset.StandardCharsets.UTF_8));
            return "sofa-remote".equals(info.optString("service"))&&info.optInt("protocol")==1?info:null;
        }catch(Exception e){return null;}finally{if(connection!=null)connection.disconnect();}
    }
    static void scan(Context context,BiConsumer<String,String> found,Runnable done) {
        new Thread(()->{
            Set<String> seen=ConcurrentHashMap.newKeySet();List<InterfaceAddress> networks=new ArrayList<>();
            WifiManager.MulticastLock lock=null;
            try {
                WifiManager wifi=(WifiManager)context.getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                if(wifi!=null){lock=wifi.createMulticastLock("SofaDiscovery");lock.acquire();}
                Enumeration<NetworkInterface> interfaces=NetworkInterface.getNetworkInterfaces();
                while(interfaces.hasMoreElements())for(InterfaceAddress address:interfaces.nextElement().getInterfaceAddresses())if(address.getAddress() instanceof Inet4Address&&address.getAddress().isSiteLocalAddress())networks.add(address);
                try(DatagramSocket socket=new DatagramSocket()){
                    socket.setBroadcast(true);socket.setSoTimeout(450);byte[] probe=PROBE.getBytes(java.nio.charset.StandardCharsets.UTF_8);
                    Set<InetAddress> destinations=new HashSet<>();destinations.add(InetAddress.getByName("255.255.255.255"));
                    for(InterfaceAddress n:networks)if(n.getBroadcast()!=null)destinations.add(n.getBroadcast());
                    for(InetAddress address:destinations)socket.send(new DatagramPacket(probe,probe.length,address,8766));
                    long end=System.currentTimeMillis()+2200;
                    while(System.currentTimeMillis()<end){try{byte[] buffer=new byte[8192];DatagramPacket packet=new DatagramPacket(buffer,buffer.length);socket.receive(packet);
                        JSONObject info=new JSONObject(new String(packet.getData(),0,packet.getLength(),java.nio.charset.StandardCharsets.UTF_8));
                        if(!"sofa-remote".equals(info.optString("service")))continue;
                        int port=info.optInt("port",8765);if(port<1||port>65535)continue;
                        String base="http://"+packet.getAddress().getHostAddress()+":"+port;
                        JSONObject verified=probe(base);if(verified!=null&&seen.add(base))found.accept(base,verified.optString("name","Windows PC"));
                    }catch(SocketTimeoutException timeout){}catch(Exception ignored){}}
                }
                // If broadcast is filtered, probe at most two local /24 segments on the application port.
                if(seen.isEmpty()){
                    ExecutorService pool=Executors.newFixedThreadPool(24);Set<String> prefixes=new HashSet<>();
                    for(InterfaceAddress network:networks){String ip=network.getAddress().getHostAddress();String prefix=ip.substring(0,ip.lastIndexOf('.')+1);
                        if(!prefixes.add(prefix))continue;if(prefixes.size()>2)break;
                        int prefixBits=network.getNetworkPrefixLength();long ipNum=0;for(byte b:network.getAddress().getAddress())ipNum=(ipNum<<8)|(b&255);final long mask=prefixBits==0?0:(0xffffffffL<<(32-prefixBits))&0xffffffffL;final long subnet=ipNum&mask;
                        for(int host=1;host<255;host++){final String base="http://"+prefix+host+":8765";final long candidate=(ipNum&0xffffff00L)|host;if((candidate&mask)!=subnet)continue;
                            pool.submit(()->{JSONObject info=probe(base);if(info!=null&&seen.add(base))found.accept(base,info.optString("name","Windows PC"));});}
                    }
                    pool.shutdown();pool.awaitTermination(20,TimeUnit.SECONDS);pool.shutdownNow();
                }
            }catch(Exception ignored){}finally{if(lock!=null&&lock.isHeld())lock.release();done.run();}
        },"sofa-discovery").start();
    }
}
