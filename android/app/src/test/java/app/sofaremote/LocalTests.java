package app.sofaremote;
import org.junit.Test;
import static org.junit.Assert.*;
public class LocalTests {
 @Test public void privateIpv4Only(){assertTrue(Discovery.localUrl("http://192.168.1.5:8765"));assertTrue(Discovery.localUrl("http://10.1.0.2:8765"));assertFalse(Discovery.localUrl("https://example.com"));assertFalse(Discovery.localUrl("http://8.8.8.8"));assertFalse(Discovery.localUrl("javascript:alert(1)"));assertFalse(Discovery.localUrl("http://192.168.1.1/?token=secret"));}
 @Test public void numericVersionComparison(){assertTrue(UpdateManager.compare("0.10.0","0.2.0")>0);assertEquals(0,UpdateManager.compare("0.2.0","0.2.0"));assertTrue(UpdateManager.compare("0.1.9","0.2.0")<0);assertEquals(0,UpdateManager.compare("bad","0.2.0"));}
}
