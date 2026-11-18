import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    computed_field,
    field_validator,
    model_validator,
)

ArticleType = Literal["term", "place", "date", "unit", "abbr"]
SourceKind = Literal["dictionary", "encyclopedia", "wikidata", "publication"]
Licence = Literal["суспільне надбання", "CC BY-SA 4.0", "CC0 1.0"]

NonEmpty = Field(min_length=1)

CENTURY = re.compile(r"^(X{0,3})(IX|IV|V?I{0,3})$")
UNITS = {"": 0, "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9}
PERIOD_SEPARATOR = re.compile(r"\s*[–-]\s*")


def century(roman: str) -> int:
    match = CENTURY.match(roman)
    value = 10 * len(match.group(1)) + UNITS[match.group(2)] if match else 0
    if value == 0:
        raise ValueError(f"{roman!r} is not a century in Roman numerals")
    if value > 21:
        raise ValueError(f"{roman!r} exceeds the supported range of 21 centuries")
    return value


def check_storable_text(value: str) -> str:
    if "\x00" in value:
        raise ValueError("text must not contain NUL characters")
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ValueError("text must not contain lone surrogates")
    return value


def check_safe_url_characters(value: str) -> str:
    check_storable_text(value)
    if any(ord(character) <= 0x1F or 0x7F <= ord(character) <= 0x9F for character in value):
        raise ValueError("source_url must not contain control characters")
    return value


def period_range(period: str) -> tuple[int, int]:
    parts = PERIOD_SEPARATOR.split(period.strip())
    if len(parts) > 2:
        raise ValueError("period must be one century or a range of two")
    start, end = century(parts[0]), century(parts[-1])
    if start > end:
        raise ValueError("the period range must go from the earlier century to the later one")
    return start, end


class ArticleMeta(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    term: str = NonEmpty
    variants: list[str]
    type: ArticleType
    period: str = NonEmpty
    source_title: str = NonEmpty
    source_url: AnyHttpUrl
    source_kind: SourceKind
    licence: Licence
    wikidata_id: str | None = Field(default=None, pattern=r"^Q[1-9][0-9]*$")

    @field_validator("term", "source_title", mode="before")
    @classmethod
    def check_text_fields(cls, value: object) -> object:
        if isinstance(value, str):
            checked = check_storable_text(value)
            if not checked.strip():
                raise ValueError("text must not be empty")
            return checked
        return value

    @field_validator("variants", mode="before")
    @classmethod
    def check_variant_text(cls, value: object) -> object:
        if isinstance(value, list):
            return [check_storable_text(item) if isinstance(item, str) else item for item in value]
        return value

    @field_validator("period")
    @classmethod
    def check_period(cls, period: str) -> str:
        period_range(period)
        return period

    @field_validator("source_url", mode="before")
    @classmethod
    def check_source_url_characters(cls, url: object) -> object:
        if isinstance(url, str):
            return check_safe_url_characters(url)
        return url

    @field_validator("source_url")
    @classmethod
    def check_https(cls, url: AnyHttpUrl) -> AnyHttpUrl:
        if url.scheme != "https":
            raise ValueError("source_url must use https")
        return url

    @model_validator(mode="after")
    def check_variants(self) -> "ArticleMeta":
        seen = {self.term.strip().casefold()}
        for variant in self.variants:
            key = variant.strip().casefold()
            if not key:
                raise ValueError("variants must not be empty")
            if key in seen:
                raise ValueError(f"variant {variant!r} repeats the term or another variant")
            seen.add(key)
        return self

    @computed_field
    @property
    def period_from(self) -> int:
        return period_range(self.period)[0]

    @computed_field
    @property
    def period_to(self) -> int:
        return period_range(self.period)[1]


class Article(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: Path
    meta: ArticleMeta
    text: str = NonEmpty

    @field_validator("text")
    @classmethod
    def check_text_characters(cls, text: str) -> str:
        return check_storable_text(text)


class CorpusError(ValueError):
    pass


FRONT_MATTER = "---"


def parse_article(path: Path) -> Article:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != FRONT_MATTER or FRONT_MATTER not in lines[1:]:
        raise CorpusError(f"{path}: YAML front matter between --- lines is missing")
    end = lines.index(FRONT_MATTER, 1)
    meta = yaml.safe_load("\n".join(lines[1:end]))
    if not isinstance(meta, dict):
        raise CorpusError(f"{path}: front matter must be a mapping")
    text = "\n".join(lines[end + 1 :]).strip()
    try:
        return Article(path=path, meta=ArticleMeta.model_validate(meta), text=text)
    except ValidationError as error:
        raise CorpusError(f"{path}: {error}") from error


def load_corpus(directory: Path) -> list[Article]:
    if not directory.is_dir():
        raise CorpusError(f"{directory}: corpus directory does not exist")
    nested = sorted(path for path in directory.rglob("*.md") if path.parent != directory)
    if nested:
        raise CorpusError(f"{nested[0]}: articles must lie directly in {directory}")
    articles = [parse_article(path) for path in sorted(directory.glob("*.md"))]
    if not articles:
        raise CorpusError(f"{directory}: corpus has no articles")
    seen: dict[tuple[str, str], Path] = {}
    for article in articles:
        key = (article.meta.type, article.meta.term.casefold())
        if key in seen:
            raise CorpusError(f"{article.path}: duplicates {seen[key]}")
        seen[key] = article.path
    return articles
