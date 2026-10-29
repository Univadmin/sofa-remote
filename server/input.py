"""Windows input adapter. DryRun never injects input, including on Windows."""
import ctypes
from ctypes import wintypes
import os
import time
import webbrowser

KEYS = {**{chr(i): i for i in range(65, 91)}, **{str(i): 48+i for i in range(10)},
        **{f'F{i}': 111+i for i in range(1, 25)},
        'WIN': 0x5B, 'CTRL': 0x11, 'ALT': 0x12, 'SHIFT': 0x10,
        'ENTER': 13, 'TAB': 9, 'ESC': 27, 'SPACE': 32, 'BACKSPACE': 8,
        'DELETE': 46, 'LEFT': 37, 'UP': 38, 'RIGHT': 39, 'DOWN': 40,
        'HOME': 36, 'END': 35, 'PAGEUP': 33, 'PAGEDOWN': 34,
        'INSERT': 45, 'CAPSLOCK': 20, 'PRINTSCREEN': 44, 'PAUSE': 19,
        'ADD': 107, 'SUBTRACT': 109, 'MULTIPLY': 106,
        'PERIOD': 190, 'COMMA': 188, 'SEMICOLON': 186, 'SLASH': 191,
        'VOLUMEUP': 175, 'VOLUMEDOWN': 174, 'MUTE': 173,
        'PLAYPAUSE': 179, 'STOP': 178, 'NEXT': 176, 'PREVIOUS': 177}

class DryRun:
    def __init__(self): self.events = []
    def move(self, x, y): self.events.append(('move', x, y))
    def button(self, button, down): self.events.append(('button', button, down))
    def scroll(self, amount): self.events.append(('scroll', amount))
    def keys(self, keys): self.events.append(('keys', keys))
    def text(self, text): self.events.append(('text', text))
    def open_url(self, url): self.events.append(('url', url))
    def clipboard(self, text=None):
        if text is not None: self.clip = text
        return getattr(self, 'clip', '')
    def windows(self): return []
    def focus(self, handle): raise ValueError('Windows requires a Windows host')
    def launch(self, app): self.events.append(('launch',app))
    def window(self, handle, action): self.events.append(('window',handle,action))
    def power(self, action): self.events.append(('power', action))
    def release(self): pass

class Windows:
    def __init__(self):
        if os.name != 'nt': raise RuntimeError('Windows host required; use --dry-run for development')
        self.u = ctypes.WinDLL('user32', use_last_error=True)
        self.k = ctypes.WinDLL('kernel32', use_last_error=True)
        self.u.GetClipboardData.restype = ctypes.c_void_p
        self.u.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
        self.u.SetClipboardData.restype = ctypes.c_void_p
        self.k.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        self.k.GlobalAlloc.restype = ctypes.c_void_p
        self.k.GlobalLock.argtypes = [ctypes.c_void_p]
        self.k.GlobalLock.restype = ctypes.c_void_p
        self.k.GlobalUnlock.argtypes = [ctypes.c_void_p]
        self.k.GlobalFree.argtypes = [ctypes.c_void_p]
        self.u.IsWindowVisible.argtypes = [wintypes.HWND]
        self.u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        self.u.SetForegroundWindow.argtypes = [wintypes.HWND]
        self.held = set()
    def keyboard_focus(self):
        class GUIINFO(ctypes.Structure):
            _fields_=[('cbSize',wintypes.DWORD),('flags',wintypes.DWORD),
                      *[(name,wintypes.HWND) for name in ('active','focus','capture','menu','move','caret')],('rect',wintypes.RECT)]
        info=GUIINFO();info.cbSize=ctypes.sizeof(info)
        if not self.u.GetGUIThreadInfo(0,ctypes.byref(info)):return None
        return int(info.caret) if info.caret else None
    def move(self, x, y): self.u.mouse_event(1, x, y, 0, 0)
    def button(self, button, down):
        flags = {'left': (2,4), 'right': (8,16), 'middle': (32,64)}
        self.u.mouse_event(flags[button][0 if down else 1], 0, 0, 0, 0)
        if down: self.held.add(button)
        else: self.held.discard(button)
    def release(self):
        for button in list(self.held): self.button(button, False)
    def scroll(self, amount): self.u.mouse_event(0x0800, 0, 0, amount*120, 0)
    def keys(self, keys):
        codes = [KEYS[k] for k in keys]
        try:
            for c in codes: self.u.keybd_event(c, 0, 0, 0)
        finally:
            for c in reversed(codes): self.u.keybd_event(c, 0, 2, 0)
    def text(self, text):
        # INPUT union must include MOUSEINPUT so sizeof(INPUT) is correct on x64.
        ULONG_PTR = ctypes.c_size_t
        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [('dx',wintypes.LONG),('dy',wintypes.LONG),('mouseData',wintypes.DWORD),('dwFlags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ULONG_PTR)]
        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [('vk',wintypes.WORD),('scan',wintypes.WORD),('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ULONG_PTR)]
        class UNION(ctypes.Union): _fields_ = [('ki',KEYBDINPUT),('mi',MOUSEINPUT)]
        class INPUT(ctypes.Structure): _fields_ = [('type',wintypes.DWORD),('data',UNION)]
        raw = text.encode('utf-16-le')
        for i in range(0,len(raw),2):
            scan = int.from_bytes(raw[i:i+2], 'little')
            for flags in (4,6):
                item = INPUT(type=1, data=UNION(ki=KEYBDINPUT(0,scan,flags,0,0)))
                if self.u.SendInput(1,ctypes.byref(item),ctypes.sizeof(item)) != 1:
                    raise RuntimeError('Input blocked: target may be elevated or desktop locked')
    def open_url(self, url): webbrowser.open(url)
    def clipboard(self, text=None):
        if not self.u.OpenClipboard(None): raise RuntimeError('Clipboard busy')
        try:
            if text is None:
                handle = self.u.GetClipboardData(13)
                if not handle: return ''
                ptr = self.k.GlobalLock(handle)
                if not ptr: raise RuntimeError('Clipboard unavailable')
                try: return ctypes.wstring_at(ptr)
                finally: self.k.GlobalUnlock(handle)
            data = (text+'\0').encode('utf-16-le')
            handle = self.k.GlobalAlloc(0x42, len(data))
            if not handle: raise RuntimeError('Clipboard allocation failed')
            ptr = self.k.GlobalLock(handle)
            if not ptr:
                self.k.GlobalFree(handle)
                raise RuntimeError('Clipboard allocation failed')
            ctypes.memmove(ptr,data,len(data)); self.k.GlobalUnlock(handle)
            self.u.EmptyClipboard()
            if not self.u.SetClipboardData(13,handle):
                self.k.GlobalFree(handle)
                raise RuntimeError('Clipboard write failed')
            return text
        finally: self.u.CloseClipboard()
    def windows(self):
        result=[]
        callback = ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
        @callback
        def visit(hwnd, _):
            if self.u.IsWindowVisible(hwnd):
                buf=ctypes.create_unicode_buffer(512); self.u.GetWindowTextW(hwnd,buf,512)
                if buf.value: result.append({'id':int(hwnd),'title':buf.value})
            return True
        self.u.EnumWindows(visit,0)
        return result
    def focus(self, handle):
        if handle not in {w['id'] for w in self.windows()}: raise ValueError('Window no longer available')
        self.u.ShowWindow(wintypes.HWND(handle),9)
        if not self.u.SetForegroundWindow(wintypes.HWND(handle)): raise RuntimeError('Windows refused focus; use Alt+Tab')
    def launch(self, app):
        import subprocess
        import shutil
        import winreg
        names={'chrome':'chrome.exe','edge':'msedge.exe','firefox':'firefox.exe','explorer':'explorer.exe','calculator':'calc.exe'}
        exe=names[app];path=shutil.which(exe)
        if not path:
            for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(hive,'SOFTWARE'+chr(92)+'Microsoft'+chr(92)+'Windows'+chr(92)+'CurrentVersion'+chr(92)+'App Paths'+chr(92)+exe) as key:
                        path=winreg.QueryValue(key,None)
                    break
                except OSError: continue
        if not path or not os.path.isfile(path): raise ValueError('Uygulama kurulu değil')
        subprocess.Popen([path])
    def window(self, handle, action):
        if handle not in {w['id'] for w in self.windows()}: raise ValueError('Pencere artık açık değil')
        hwnd=wintypes.HWND(handle)
        if action=='close':
            self.u.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
            self.u.PostMessageW(hwnd,0x0010,0,0)
        else: self.u.ShowWindow(hwnd,{'minimize':6,'maximize':3,'restore':9}[action])
    def power(self, action):
        import subprocess
        if action == 'lock':
            if not self.u.LockWorkStation(): raise RuntimeError('Windows could not lock the workstation')
        elif action in ('shutdown','restart'):
            subprocess.run(['shutdown','/s' if action=='shutdown' else '/r','/t','30'],check=True)
        elif action == 'cancel': subprocess.run(['shutdown','/a'],check=True)
        else: raise ValueError('Unknown power action')
