#!/usr/bin/env python3
"""Speak Hindi out of a packed add-on, the way the driver loads it.

Not a stand-in: this unpacks the .nvda-addon that would be installed, loads
the eci.dll out of it with ctypes' WinDLL the way _openevv.py does, asks the
library which languages it has, and speaks a Devanagari sentence in each.

What it answers is the question the two test scripts beside it cannot: that
the library actually shipped inside the add-on carries Hindi, and that the
add-on's own idea of what to call it agrees. A library built without
--langs hien would list one language here and pass every other check.

usage: addon-hindi.py [addon.nvda-addon]
"""

import ctypes
import glob
import hashlib
import os
import sys
import tempfile
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.join(os.path.dirname(HERE), "addon")
sys.path.insert(0, HERE)
sys.path.insert(0, ADDON)

FRAME = 2048
HINDI = 0x90000

#: Something short in Devanagari. Short on purpose: the engine is asked to
#: speak it synchronously and a long one takes minutes.
SAY = "नमस्ते।"


def find_addon(argv):
    if argv:
        return argv[0]
    root = os.path.dirname(os.path.dirname(HERE))
    made = sorted(glob.glob(os.path.join(root, "build", "*.nvda-addon")),
                  key=os.path.getmtime)
    if not made:
        raise SystemExit("addon-hindi: no .nvda-addon in build; "
                         "run nvda/build.py first")
    return made[-1]


def library_from(addon, into):
    """The engine out of the add-on, where the driver would find it."""
    with zipfile.ZipFile(addon) as z:
        names = [n for n in z.namelist() if n.endswith("eci.dll")]
        if not names:
            raise SystemExit("addon-hindi: %s carries no eci.dll -- a 32-only "
                             "build cannot be driven from 64-bit Python"
                             % os.path.basename(addon))
        z.extract(names[0], into)
        return os.path.join(into, names[0])


def declare(dll):
    dll.eciNewEx.restype = ctypes.c_void_p
    dll.eciNewEx.argtypes = [ctypes.c_int]
    dll.eciDelete.restype = ctypes.c_void_p
    dll.eciDelete.argtypes = [ctypes.c_void_p]
    dll.eciGetAvailableLanguages.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    dll.eciRegisterCallback.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                        ctypes.c_void_p]
    dll.eciSetOutputBuffer.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                       ctypes.c_void_p]
    dll.eciAddText.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    dll.eciSynthesize.argtypes = [ctypes.c_void_p]
    dll.eciSpeaking.argtypes = [ctypes.c_void_p]


def languages(dll):
    count = ctypes.c_int(0)
    dll.eciGetAvailableLanguages(None, ctypes.byref(count))
    n = count.value
    out = (ctypes.c_uint * max(n, 1))()
    count = ctypes.c_int(n)
    dll.eciGetAvailableLanguages(out, ctypes.byref(count))
    return [out[i] for i in range(count.value)]


def speak(dll, language, text):
    """One instance, one utterance, and the samples it handed back."""
    buf = (ctypes.c_short * FRAME)()
    said = bytearray()

    cb = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int,
                            ctypes.c_long, ctypes.c_void_p)

    @cb
    def on_message(h, msg, param, data):
        if msg == 0:
            said.extend(bytes(buf)[:param * 2])
        return 1

    h = dll.eciNewEx(language)
    if not h:
        return None
    try:
        dll.eciRegisterCallback(h, on_message, None)
        if not dll.eciSetOutputBuffer(h, FRAME, buf):
            return None
        # The engine takes bytes. 0x90000 does not carry the 0x800 Unicode
        # bit, so Hindi goes through the narrow path as UTF-8 -- the same
        # thing the driver does in openevv.py's flush().
        if not dll.eciAddText(h, text.encode("utf-8")):
            return None
        if not dll.eciSynthesize(h):
            return None
        for _ in range(3000):
            if not dll.eciSpeaking(h):
                break
            time.sleep(0.01)
    finally:
        dll.eciDelete(h)
    return bytes(said)


def main(argv):
    addon = find_addon(argv)
    print("addon-hindi: %s" % os.path.basename(addon))

    # _openevv.py imports NVDA's own modules at the top, so the stand-ins in
    # sequence.py go in first -- the same ones the other two checks use.
    import sequence
    sequence._install_stubs()
    import synthDrivers._openevv as mod

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        # A library that has been loaded cannot be deleted on Windows, and
        # nothing here unloads it, so the directory is left for the system to
        # sweep rather than failing the check on the way out.
        path = library_from(addon, tmp)
        dll = ctypes.WinDLL(os.path.abspath(path))
        declare(dll)

        langs = languages(dll)
        print("addon-hindi: the library has %d language%s"
              % (len(langs), "" if len(langs) == 1 else "s"))
        for l in langs:
            print("  0x%-8x %-24s %s"
                  % (l, mod.nameOf(l), mod.localeOf(l) or "(no locale)"))

        bad = 0
        if HINDI not in langs:
            print("addon-hindi: 0x90000 is not in this add-on -- the library "
                  "was built without --langs hien")
            return 1

        if mod.localeOf(HINDI) != "hi_IN":
            print("addon-hindi: the driver does not call 0x90000 hi_IN, so "
                  "NVDA cannot match Hindi text to this voice")
            bad = 1

        for l in langs:
            samples = speak(dll, l, SAY)
            if samples is None:
                print("addon-hindi: 0x%x would not speak at all" % l)
                bad = 1
                continue
            if not samples:
                print("addon-hindi: 0x%x accepted the text and made no sound"
                      % l)
                bad = 1
                continue
            print("addon-hindi: 0x%-8x %7d samples  %s"
                  % (l, len(samples) // 2,
                     hashlib.sha256(samples).hexdigest()[:16]))

        # The point of speaking the same Devanagari in both: if Hindi and
        # English answer the same samples then the language asked for is not
        # the one that ran, whatever the add-on lists.
        if len(langs) > 1:
            first = speak(dll, langs[0], SAY)
            hindi = speak(dll, HINDI, SAY)
            if first == hindi:
                print("addon-hindi: 0x%x and 0x90000 spoke identically, so "
                      "the language asked for is not the one in force"
                      % langs[0])
                bad = 1
            else:
                print("addon-hindi: Hindi and 0x%x differ on the same text, "
                      "as they must" % langs[0])

        print("addon-hindi: %s" % ("something is wrong" if bad
                                   else "every check passed"))
        return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
