# tests/test_io.py


from reqsync._types import Options
from reqsync.core import sync
from reqsync.io import read_text_preserve, write_text_preserve


def test_preserve_bom_and_newlines_on_write(tmp_path, monkeypatch):
    # Create a file with BOM and CRLF endings
    target = tmp_path / "requirements.txt"
    raw = "\ufeffpandas\n".encode()  # BOM + LF; we will convert to CRLF on write
    target.write_bytes(raw.replace(b"\n", b"\r\n"))

    from reqsync import env as env_mod

    monkeypatch.setattr(env_mod, "is_venv_active", lambda: True)
    monkeypatch.setattr(env_mod, "run_pip_upgrade", lambda *a, **k: (0, "skipped"))
    monkeypatch.setattr(env_mod, "get_installed_versions", lambda: {"pandas": "2.2.2"})

    # Run sync to cause a change
    res = sync(Options(path=target, system_ok=True, no_upgrade=True))
    assert res.changed, "A change should have been applied"

    # Verify BOM and CRLF preserved
    data = target.read_bytes()
    assert data.startswith(b"\xef\xbb\xbf"), "BOM must be preserved"
    assert b"\r\n" in data and b"\n" not in data.replace(b"\r\n", b""), "CRLF endings must be preserved"


def test_read_write_roundtrip_preserves_format(tmp_path):
    p = tmp_path / "x.txt"
    p.write_bytes(b"\xef\xbb\xbfline1\r\nline2\r\n")  # BOM + CRLF
    text, nl, bom = read_text_preserve(p)
    assert nl == "\r\n" and bom is True
    write_text_preserve(p, text, bom)
    assert p.read_bytes().startswith(b"\xef\xbb\xbf"), "Round-trip should preserve BOM"
