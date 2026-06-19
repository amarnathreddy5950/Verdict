from verdict.judge.normalize import strip_formatting


def test_strip_formatting_removes_markdown():
    raw = "# Title\n\n**bold** and `code` and *italic*\n- item one\n[link](http://x.com)"
    out = strip_formatting(raw)
    assert "bold" in out and "italic" in out and "item one" in out and "link" in out
    for marker in ("**", "`", "# ", "http://", "](", "- "):
        assert marker not in out


def test_strip_formatting_keeps_plain_text():
    raw = "Just a plain sentence with no formatting."
    assert strip_formatting(raw) == raw
