package app.sofaremote;

final class LiveTextDelta {
    final int delete;
    final String text;
    private LiveTextDelta(int delete,String text){this.delete=delete;this.text=text;}
    static LiveTextDelta between(String oldValue,String newValue){
        int[] old=oldValue.codePoints().toArray(),next=newValue.codePoints().toArray();int common=0;
        while(common<old.length&&common<next.length&&old[common]==next[common])common++;
        return new LiveTextDelta(old.length-common,new String(next,common,next.length-common));
    }
}
