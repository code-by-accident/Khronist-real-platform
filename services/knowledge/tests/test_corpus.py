from pathlib import Path

import pytest

from khronist_knowledge.corpus import CorpusError, load_corpus, parse_article, period_range

ENTRIES = Path(__file__).parent.parent / "data" / "entries"

META = """term: тест
variants: [тестъ]
type: term
period: XIX
source_title: Тестове джерело
source_url: https://example.org/test
source_kind: dictionary
licence: CC BY-SA 4.0"""


def write(directory: Path, name: str, content: str) -> Path:
    path = directory / name
    path.write_text(content, encoding="utf-8")
    return path


def article(meta: str = META) -> str:
    return f"---\n{meta}\n---\nТекст.\n"


def test_parses_front_matter_and_body(tmp_path: Path) -> None:
    parsed = parse_article(write(tmp_path, "a.md", f"---\n{META}\n---\n\nТекст статті.\n"))
    assert parsed.meta.term == "тест"
    assert parsed.meta.variants == ["тестъ"]
    assert parsed.meta.source_kind == "dictionary"
    assert parsed.text == "Текст статті."


def test_accepts_cc0_licence(tmp_path: Path) -> None:
    metadata = META.replace("CC BY-SA 4.0", "CC0 1.0")
    parsed = parse_article(write(tmp_path, "cc0.md", article(metadata)))
    assert parsed.meta.licence == "CC0 1.0"


def test_rejects_file_without_front_matter(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="front matter"):
        parse_article(write(tmp_path, "a.md", "Текст без шапки.\n"))


@pytest.mark.parametrize(
    "meta",
    [
        META.replace("source_kind: dictionary\n", ""),
        META + "\nauthor: хтось",
        META + "\nwikidata_id: 123",
        META.replace("https://example.org/test", "example.org/test"),
        META.replace("https://example.org/test", "http://example.org/test"),
        META.replace("CC BY-SA 4.0", "CC BY 4.0"),
        META.replace("[тестъ]", "[тестъ, '  ']"),
        META.replace("[тестъ]", "[тестъ, ТЕСТЪ]"),
        META.replace("[тестъ]", "[Тест]"),
        META.replace("period: XIX", "period: 19"),
        META.replace("period: XIX", "period: XIX–XVIII"),
        META.replace("period: XIX", "period: XVIII–XIX–XX"),
        META.replace("period: XIX", "period: IIX"),
    ],
)
def test_rejects_invalid_meta_and_names_the_file(tmp_path: Path, meta: str) -> None:
    with pytest.raises(CorpusError, match="bad.md"):
        parse_article(write(tmp_path, "bad.md", article(meta)))


def test_rejects_empty_body(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="a.md"):
        parse_article(write(tmp_path, "a.md", f"---\n{META}\n---\n\n"))


@pytest.mark.parametrize(
    ("period", "expected"),
    [("XIX", (19, 19)), ("XVIII–XIX", (18, 19)), ("XVII - XVIII", (17, 18)), ("XXI", (21, 21))],
)
def test_parses_period_into_centuries(period: str, expected: tuple[int, int]) -> None:
    assert period_range(period) == expected


def test_exposes_period_range_on_the_article(tmp_path: Path) -> None:
    meta = parse_article(write(tmp_path, "a.md", article(META.replace("XIX", "XVIII–XIX")))).meta
    assert (meta.period_from, meta.period_to) == (18, 19)


def test_rejects_duplicate_terms(tmp_path: Path) -> None:
    write(tmp_path, "a.md", article())
    write(tmp_path, "b.md", article(META.replace("тест", "ТЕСТ", 1)))
    with pytest.raises(CorpusError, match="duplicates"):
        load_corpus(tmp_path)


def test_rejects_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="does not exist"):
        load_corpus(tmp_path / "missing")


def test_rejects_empty_directory(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="no articles"):
        load_corpus(tmp_path)


def test_rejects_nested_articles(tmp_path: Path) -> None:
    write(tmp_path, "a.md", article())
    (tmp_path / "nested").mkdir()
    write(tmp_path / "nested", "b.md", article(META.replace("тест", "інший", 1)))
    with pytest.raises(CorpusError, match="directly"):
        load_corpus(tmp_path)


def test_corpus_entries_are_valid() -> None:
    files = list(ENTRIES.glob("*.md"))
    assert files
    assert len(load_corpus(ENTRIES)) == len(files)
