###############################################################################
#### Helper method used to get the free space on the disk where downloaded ####
#### movies are stored                                                     ####
###############################################################################

import ctypes
import _winreg
import config
import prefs

localeInitialized = False

def samefile(path1, path2):
    return getLongPathName(path1) == getLongPathName(path2)

def getLongPathName(path):
    buf = ctypes.create_unicode_buffer(260) 
    GetLongPathName = ctypes.windll.kernel32.GetLongPathNameW
    rv = GetLongPathName(path, buf, 260)
    if rv == 0 or rv > 260:
        return path
    else:
        return buf.value

def getAvailableBytesForMovies():
    # TODO: windows implementation
    moviesDir = config.get(prefs.MOVIES_DIRECTORY)
    freeSpace = ctypes.c_ulonglong(0)
    availableSpace = ctypes.c_ulonglong(0)
    totalSpace = ctypes.c_ulonglong(0)
    rv = ctypes.windll.kernel32.GetDiskFreeSpaceExW(unicode(moviesDir),
            ctypes.byref(availableSpace), ctypes.byref(totalSpace),
            ctypes.byref(freeSpace)) 
    if rv == 0:
        print "GetDiskFreeSpaceExW failed, returning bogus value!"
        return 100 * 1024 * 1024 * 1024
    return availableSpace.value

#############################################################################
# Windows specific locale                                                   #
#############################################################################
_langs = {
0x401: "ar",
0x416: "pt_BR",
0x804: "zh_CN", # Chinese simplified
0x404: "zh_TW", # Chinese traditional
0x405: "cs",
0x406: "da",
0x413: "nl",
0x409: "en",
0x40b: "fi",
0x40c: "fr",
0x407: "de",
0x408: "el",
0x40d: "he",
0x40e: "hu",
0x410: "it",
0x411: "jp",
0x412: "ko",
0x414: "nb",
0x415: "pl",
0x816: "pt",
0x419: "ru",
0xc0a: "es",
0x41D: "sv",
0x41f: "tr",
}

def _getKey (keyName, subkey, typ):
    try:
        key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, keyName)
        (val, t) = _winreg.QueryValueEx(key, subkey)
        if t == typ:
            return val
    except:
        pass
    return None

def _getLocale():
    keyName = r"Software\Policies\Microsoft\Control Panel\Desktop"
    subkey = "MultiUILanguageID"
    val = _getKey(keyName, subkey, _winreg.REG_DWORD)
    if val is None:
        keyName = r"Control Panel\Desktop"
        val = _getKey(keyName, subkey, _winreg.REG_DWORD)
    if val is None:
        return None
    else:
        return langs[val]

def initializeLocale():
    global localeInitialized
    lang = _getLocale()
    if lang:
        os.environ["LANGUAGE"] = lang
    localeInitialized = True
