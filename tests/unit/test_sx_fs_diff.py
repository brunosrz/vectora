"""Parser de ``git status --porcelain=v1`` e ``DiffFile`` (handler de diff)."""

from __future__ import annotations


def test_parse_porcelain_modified_unstaged() -> None:
    from src.api.handlers.workspaces import _parse_porcelain_v1

    out = _parse_porcelain_v1(" M src/foo.py\n")
    assert out == [(" ", "M", "src/foo.py")]


def test_parse_porcelain_modified_staged() -> None:
    from src.api.handlers.workspaces import _parse_porcelain_v1

    out = _parse_porcelain_v1("M  src/foo.py\n")
    assert out == [("M", " ", "src/foo.py")]


def test_parse_porcelain_modified_both() -> None:
    """``XY=MM`` — staged E unstaged simultâneos sobre o mesmo path."""
    from src.api.handlers.workspaces import _parse_porcelain_v1

    out = _parse_porcelain_v1("MM src/foo.py\n")
    assert out == [("M", "M", "src/foo.py")]


def test_parse_porcelain_untracked() -> None:
    """``??`` indica path untracked."""
    from src.api.handlers.workspaces import _parse_porcelain_v1

    out = _parse_porcelain_v1("?? new_file.md\n")
    assert out == [("?", "?", "new_file.md")]


def test_parse_porcelain_added_staged() -> None:
    from src.api.handlers.workspaces import _parse_porcelain_v1

    out = _parse_porcelain_v1("A  src/new.py\n")
    assert out == [("A", " ", "src/new.py")]


def test_parse_porcelain_deleted_unstaged() -> None:
    from src.api.handlers.workspaces import _parse_porcelain_v1

    out = _parse_porcelain_v1(" D src/gone.py\n")
    assert out == [(" ", "D", "src/gone.py")]


def test_parse_porcelain_rename_uses_destination() -> None:
    from src.api.handlers.workspaces import _parse_porcelain_v1

    out = _parse_porcelain_v1("R  old.py -> new.py\n")
    assert out == [("R", " ", "new.py")]


def test_parse_porcelain_normalizes_windows_paths() -> None:
    from src.api.handlers.workspaces import _parse_porcelain_v1

    out = _parse_porcelain_v1("M  src\\foo\\bar.py\n")
    assert out == [("M", " ", "src/foo/bar.py")]


def test_parse_porcelain_multiple_entries() -> None:
    from src.api.handlers.workspaces import _parse_porcelain_v1

    raw = "M  src/a.py\n M src/b.py\n?? src/c.py\nMM src/d.py\n"
    out = _parse_porcelain_v1(raw)
    assert len(out) == 4
    paths = [p for _, _, p in out]
    assert paths == ["src/a.py", "src/b.py", "src/c.py", "src/d.py"]


def test_parse_porcelain_ignores_short_lines() -> None:
    from src.api.handlers.workspaces import _parse_porcelain_v1

    out = _parse_porcelain_v1("AB\nM\n")
    assert out == []


def test_diff_file_accepts_decomposed_flags() -> None:
    """``DiffFile`` aceita ``staged_change``/``unstaged_change``/``untracked``."""
    from src.api.handlers.workspaces import DiffFile

    f = DiffFile(
        path="src/foo.py",
        status="M",
        staged_change="M",
        unstaged_change="M",
        untracked=False,
    )
    assert f.staged_change == "M"
    assert f.unstaged_change == "M"
    assert f.untracked is False


def test_diff_file_status_only_defaults_flags_to_none() -> None:
    """Construir ``DiffFile`` só com ``status`` resulta em flags ``None``."""
    from src.api.handlers.workspaces import DiffFile

    f = DiffFile(path="x.py", status="M", additions=3, deletions=1)
    assert f.status == "M"
    assert f.staged_change is None
    assert f.unstaged_change is None
    assert f.untracked is False
