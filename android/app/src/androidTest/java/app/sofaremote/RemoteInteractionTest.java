package app.sofaremote;

import android.os.SystemClock;
import android.view.*;
import android.webkit.WebView;
import android.widget.EditText;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.rule.ActivityTestRule;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.*;
import org.junit.runner.RunWith;
import java.util.concurrent.*;
import org.json.JSONArray;
import static org.junit.Assert.*;
import static androidx.test.espresso.Espresso.onView;
import static androidx.test.espresso.matcher.ViewMatchers.withText;
import static androidx.test.espresso.matcher.ViewMatchers.withHint;
import static androidx.test.espresso.action.ViewActions.click;
import static androidx.test.espresso.action.ViewActions.typeText;

@RunWith(AndroidJUnit4.class)
public class RemoteInteractionTest {
    @Rule public ActivityTestRule<MainActivity> rule=new ActivityTestRule<>(MainActivity.class);
    private WebView web;
    private interface Condition { boolean get() throws Exception; }
    private void waitFor(Condition condition) throws Exception {long end=SystemClock.uptimeMillis()+15000;while(SystemClock.uptimeMillis()<end){if(condition.get())return;SystemClock.sleep(150);}fail("Android interaction timed out");}
    private WebView findWeb(View view){if(view instanceof WebView)return (WebView)view;if(view instanceof ViewGroup){ViewGroup group=(ViewGroup)view;for(int i=0;i<group.getChildCount();i++){WebView match=findWeb(group.getChildAt(i));if(match!=null)return match;}}return null;}
    private String js(String script)throws Exception{ArrayBlockingQueue<String> queue=new ArrayBlockingQueue<>(1);InstrumentationRegistry.getInstrumentation().runOnMainSync(()->web.evaluateJavascript(script,queue::offer));String value=queue.poll(5,TimeUnit.SECONDS);assertNotNull(value);return value;}
    @Before public void connect()throws Exception{
        InstrumentationRegistry.getInstrumentation().runOnMainSync(()->{rule.getActivity().openServer("http://10.0.2.2:8765");web=findWeb(rule.getActivity().findViewById(android.R.id.content));});
        try{waitFor(()->"true".equals(js("typeof ws!=='undefined'&&ws.readyState===1")));}catch(AssertionError error){throw new AssertionError(js("JSON.stringify({url:location.href,text:document.body?.innerText,ws:typeof ws==='undefined'?'none':ws?.readyState})"),error);}
        js("window.testSent=[];window.testOriginalSend=WebSocket.prototype.send;WebSocket.prototype.send=function(value){testSent.push(JSON.parse(value));return testOriginalSend.call(this,value)};true");
    }
    private void screenshot(String name)throws Exception{
        android.graphics.Bitmap bitmap=InstrumentationRegistry.getInstrumentation().getUiAutomation().takeScreenshot();
        if(bitmap!=null){
            android.content.ContentValues values=new android.content.ContentValues();values.put(android.provider.MediaStore.Images.Media.DISPLAY_NAME,name+".png");values.put(android.provider.MediaStore.Images.Media.MIME_TYPE,"image/png");values.put(android.provider.MediaStore.Images.Media.RELATIVE_PATH,"Pictures/SofaRemoteTests");
            android.content.ContentResolver resolver=rule.getActivity().getContentResolver();android.net.Uri image=resolver.insert(android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI,values);
            if(image!=null)try(java.io.OutputStream output=resolver.openOutputStream(image)){bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,output);}
        }
    }
    @After public void captureResult()throws Exception{screenshot("interaction-"+SystemClock.uptimeMillis());}
    private void hold(String selector)throws Exception{touch(selector,700);}
    private void tap(String selector)throws Exception{touch(selector,80);}
    private void touch(String selector,long duration)throws Exception{
        JSONArray point=new JSONArray(js("(()=>{const r=document.querySelector("+org.json.JSONObject.quote(selector)+").getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]})()"));
        int[] origin=new int[2];float[] scale=new float[1];InstrumentationRegistry.getInstrumentation().runOnMainSync(()->{web.getLocationOnScreen(origin);scale[0]=web.getScale();});
        float x=origin[0]+(float)point.getDouble(0)*scale[0],y=origin[1]+(float)point.getDouble(1)*scale[0];long start=SystemClock.uptimeMillis();
        MotionEvent down=MotionEvent.obtain(start,start,MotionEvent.ACTION_DOWN,x,y,0);down.setSource(InputDevice.SOURCE_TOUCHSCREEN);InstrumentationRegistry.getInstrumentation().sendPointerSync(down);down.recycle();SystemClock.sleep(duration);
        MotionEvent up=MotionEvent.obtain(start,SystemClock.uptimeMillis(),MotionEvent.ACTION_UP,x,y,0);up.setSource(InputDevice.SOURCE_TOUCHSCREEN);InstrumentationRegistry.getInstrumentation().sendPointerSync(up);up.recycle();
    }
    @Test public void footerMenusAndActionsWorkWithoutNativeDialog()throws Exception{
        js("if(window.HTMLDialogElement)HTMLDialogElement.prototype.showModal=undefined;window.testChecks=0;const originalFetch=window.fetch;window.fetch=function(url,options){if(String(url).endsWith('/api/updates/check')){testChecks++;return Promise.resolve(new Response('{}',{status:200,headers:{'Content-Type':'application/json'}}));}return originalFetch.apply(this,arguments)};true");
        for(boolean full:new boolean[]{false,true}){
            js("fullMouse="+full+";document.body.classList.toggle('full-mouse',fullMouse);true");
            tap("#layout");SystemClock.sleep(1100);
            assertEquals("true",js("!document.querySelector('#sheet').hidden&&document.querySelector('#sheet-title').textContent==='Ekran ve mouse'"));
            tap("#side");assertEquals("true",js("document.querySelector('#sheet').hidden&&document.querySelector('#workspace').classList.contains('side')"));
            tap("#shortcuts");SystemClock.sleep(1100);
            assertEquals("true",js("!document.querySelector('#sheet').hidden&&!!document.querySelector('#add-shortcut')"));
            tap("#close-sheet");assertEquals("true",js("document.querySelector('#sheet').hidden"));
            tap("#downloads");SystemClock.sleep(1100);
            assertEquals("true",js("!document.querySelector('#sheet').hidden&&document.querySelector('#sheet-title').textContent==='Güncelleme'"));
            tap("[data-check-updates]");
            waitFor(()->"true".equals(js("testChecks>0&&!document.querySelector('[data-check-updates]').disabled")));
            tap("#close-sheet");
        }
        assertEquals("2",js("testChecks"));
    }
    @Test public void longPressTextAndInputStartsMouseWithoutSelection()throws Exception{
        js("fullMouse=true;document.body.classList.add('full-mouse');true");
        hold("header strong");
        waitFor(()->"2".equals(js("testSent.filter(x=>x.type==='button'&&x.button==='left').length")));
        assertEquals("\"\"",js("String(window.getSelection())"));
        js("paneTypes[1]='keyboard';renderPane(1);testSent=[];true");hold(".keyboard-live");
        waitFor(()->"2".equals(js("testSent.filter(x=>x.type==='button'&&x.button==='left').length")));
        assertEquals("false",js("document.activeElement.matches('.keyboard-live')"));
    }
    @Test public void topTabLongPressOffersAndClosesTab()throws Exception{
        waitFor(()->"1".equals(js("document.querySelectorAll('#top-tabs button').length")));
        hold("#top-tabs button");screenshot("tab-close-menu");onView(withText("Sekmeyi kapat")).perform(click());
        waitFor(()->"0".equals(js("document.querySelectorAll('#top-tabs button').length")));
        assertEquals("true",js("testSent.some(x=>x.type==='tab'&&x.action==='close'&&x.tabId===101)"));
    }
    @Test public void pcFocusOpensNativeKeyboardAndSendsText()throws Exception{
        js("fetch('/__focus',{method:'POST'});true");
        waitFor(()->{boolean[] ready=new boolean[1];InstrumentationRegistry.getInstrumentation().runOnMainSync(()->{View focus=rule.getActivity().getCurrentFocus();ready[0]=focus instanceof EditText&&focus.getRootWindowInsets()!=null&&focus.getRootWindowInsets().isVisible(WindowInsets.Type.ime())&&focus.getRootWindowInsets().getInsets(WindowInsets.Type.ime()).bottom>100;});return ready[0];});
        screenshot("native-keyboard");onView(withHint("PC’ye yaz…")).perform(typeText("abc"));
        try{waitFor(()->"\"abc\"".equals(js("testSent.filter(x=>x.type==='edit').map(x=>x.text).join('')")));}catch(AssertionError error){throw new AssertionError(js("JSON.stringify(testSent)"),error);}
    }
}
