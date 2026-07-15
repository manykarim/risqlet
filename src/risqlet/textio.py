"""Text I/O primitives: UTF-8 in, UTF-8 out, with one compatibility fallback.

risqlet writes UTF-8 with `\\n` everywhere. Reading is not symmetrical, because the
files on disk were not all written by a version that did: before the encoding fix,
risqlet wrote through the host's locale, so a Windows user's `CLAUDE.md` and register
are cp1252 — risqlet's own em-dash lands as byte 0x97. Making reads strict without
handling that turned a silent-corruption bug into `UnicodeDecodeError` on upgrade,
for exactly the users the fix was for.

So: try UTF-8, fall back to cp1252, and say so. The fallback is a compatibility shim
for bytes risqlet itself produced, not general robustness — it is deliberately not
applied where risqlet has only ever written ASCII (see read_text_strict).
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

#: What Python used on Windows before we said otherwise. A fixed encoding, not
#: locale.getpreferredencoding(): the fallback must behave identically on every
#: platform, or the bug becomes unreproducible on the host we develop on — which is
#: how it shipped in the first place.
LEGACY_ENCODING = "cp1252"

_reported: set[str] = set()


def read_text_strict(path: Path) -> str:
    """UTF-8 only. For files risqlet has provably never written non-ASCII into.

    `json.dumps` escapes non-ASCII to \\uXXXX by default, so `events.jsonl` and the
    JSON agent configs are pure ASCII by construction. A decode error there cannot be
    our old output — it is real corruption, and should raise rather than be recovered
    into plausible nonsense.
    """
    return path.read_text(encoding="utf-8")


def read_text_tolerant(path: Path) -> str:
    """UTF-8, falling back to cp1252 for files an older risqlet wrote in the locale.

    Recovers the real characters rather than replacing them: risqlet rewrites these
    files, so `errors="replace"` would write U+FFFD back over the user's content —
    destroying the file it was meant to repair. The next write normalizes to UTF-8,
    so a file heals by being used.

    A file that is neither UTF-8 nor cp1252 still raises: at that point it is not
    something we wrote.
    """
    data = path.read_bytes()
    try:
        return _decode(data, "utf-8")
    except UnicodeDecodeError:
        text = _decode(data, LEGACY_ENCODING)
        _report_recovery(path)
        return text


def _decode(data: bytes, encoding: str) -> str:
    """Decode with universal newlines, exactly as Path.read_text() does.

    Not `bytes.decode()`: that skips newline translation, so a CRLF file would keep
    its \\r characters in the parsed text — and since writes pin newline="\\n", those
    would be written back as literal carriage returns, leaving mixed line endings in
    a file we claim is deterministic. Caught by the Windows CI leg, where a CRLF
    fixture survived into a saved register.
    """
    return io.TextIOWrapper(io.BytesIO(data), encoding=encoding, newline=None).read()


def _report_recovery(path: Path) -> None:
    """Say it out loud, once per file.

    A silent repair is indistinguishable from the mojibake bug this replaced — both
    leave a working command and surprising text — and the user's file is about to
    change encoding without them asking for it.
    """
    key = str(path)
    if key in _reported:
        return
    _reported.add(key)
    print(f"note: {path} is not UTF-8 ({LEGACY_ENCODING} — written by a risqlet older "
          f"than the encoding fix); recovering its text and rewriting it as UTF-8",
          file=sys.stderr)
