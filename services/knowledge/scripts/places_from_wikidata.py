import argparse
import csv
import json
import sys
from collections.abc import Iterable
from itertools import chain, groupby
from operator import itemgetter
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yaml
from pydantic import BaseModel, ConfigDict, Field

from khronist_knowledge.corpus import ArticleMeta, load_corpus, parse_article

KNOWLEDGE_ROOT = Path(__file__).resolve().parents[1]
CATALOG = KNOWLEDGE_ROOT / "data/places/kyiv-uyezd.tsv"
ENTRIES = KNOWLEDGE_ROOT / "data/entries"
WDQS = "https://query.wikidata.org/sparql"


class Place(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    term: str
    variants: list[str] = Field(min_length=1)
    modern_name: str = Field(min_length=1)
    kind: Literal["село", "селище", "місто"]
    district: Literal["Бучанський", "Вишгородський", "Обухівський", "Фастівський"]
    qid: str = Field(pattern=r"^Q[1-9][0-9]*$")
    katottg: str = Field(pattern=r"^UA32[0-9]{15}$")
    period: str
    source_title: str
    source_url: str
    history: str = Field(min_length=1)

    def article(self) -> str:
        meta = ArticleMeta(
            term=self.term,
            variants=self.variants,
            type="place",
            period=self.period,
            source_title=self.source_title,
            source_url=self.source_url,
            source_kind="publication",
            licence="суспільне надбання",
            wikidata_id=self.qid,
        )
        header = yaml.safe_dump(
            meta.model_dump(mode="json", exclude={"period_from", "period_to"}),
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )
        wikidata = f"https://www.wikidata.org/wiki/{self.qid}"
        return (
            f"---\n{header}---\nУ джерелі поселення записано як «{self.term}». "
            f"{self.history}\n\n"
            f"Сучасна назва — {self.modern_name}. "
            f"Тип поселення — {self.kind}. "
            f"{self.district} район Київської області "
            f"за [КАТОТТГ](https://mininfra.gov.ua/storage/app/sites/1/uploaded-files/"
            f"kodifikator-07-07.xlsx), код {self.katottg}. "
            f"[Wikidata: {self.qid}]({wikidata}).\n"
        )


def name_key(value: str) -> str:
    return value.replace("’", "'").replace("ʼ", "'").strip().casefold()


def load_places(path: Path) -> list[Place]:
    with path.open(encoding="utf-8", newline="") as source:
        places = [
            Place.model_validate(row | {"variants": row["variants"].split("|")})
            for row in csv.DictReader(source, delimiter="\t")
        ]
    if not places:
        raise ValueError(f"{path}: place catalog is empty")
    for field in ("slug", "qid", "katottg"):
        if len({getattr(place, field) for place in places}) != len(places):
            raise ValueError(f"{path}: duplicate {field}")
    return places


def verify_wikidata(places: list[Place]) -> None:
    pairs = "\n".join(f'(wd:{place.qid} "{place.katottg}")' for place in places)
    query = f"""
SELECT DISTINCT ?place ?code WHERE {{
  VALUES (?place ?code) {{
    {pairs}
  }}
  ?place wdt:P9435 ?code .
}}
"""
    request = Request(
        f"{WDQS}?{urlencode({'query': query, 'format': 'json'})}",
        headers={
            "Accept": "application/sparql-results+json",
            "User-Agent": "Khronist knowledge corpus (https://github.com/code-by-accident/Khronist-real-platform)",
        },
    )
    with urlopen(request, timeout=45) as response:
        payload = json.load(response)
    found = {
        (row["place"]["value"].rsplit("/", 1)[-1], row["code"]["value"])
        for row in payload["results"]["bindings"]
    }
    missing = sorted({(place.qid, place.katottg) for place in places} - found)
    if missing:
        raise ValueError(f"Wikidata is missing these QID and KATOTTH pairs: {missing}")


def require_unique(records: Iterable[tuple[str, Path]], label: str) -> None:
    groups = groupby(sorted(records), key=itemgetter(0))
    duplicates = (
        (key, paths) for key, group in groups if len(paths := [path for _, path in group]) > 1
    )
    conflict = next(duplicates, None)
    if conflict is not None:
        key, paths = conflict
        raise ValueError(f"{label} {key!r} also listed in {', '.join(map(str, paths))}")


def pending_articles(places: list[Place], entries: Path, *, check: bool) -> dict[Path, str]:
    targets = {entries / f"place-{place.slug}.md": place for place in places}
    other_articles = map(parse_article, sorted(set(entries.glob("*.md")) - targets.keys()))
    existing = {
        article.path: article.meta for article in other_articles if article.meta.type == "place"
    }

    require_unique(
        chain(
            ((meta.wikidata_id, path) for path, meta in existing.items() if meta.wikidata_id),
            ((place.qid, path) for path, place in targets.items()),
        ),
        "QID",
    )
    require_unique(
        chain(
            (
                (key, path)
                for path, meta in existing.items()
                for key in set(map(name_key, (meta.term, *meta.variants)))
            ),
            (
                (name_key(form), path)
                for path, place in targets.items()
                for form in (place.term, *place.variants)
            ),
        ),
        "place name",
    )

    expected = {path: place.article() for path, place in targets.items()}
    on_disk = {path for path in expected if path.exists()}
    missing = expected.keys() - on_disk
    if check and missing:
        raise ValueError(f"{min(missing)}: generated article is missing")

    changed = next(
        (path for path in sorted(on_disk) if path.read_text(encoding="utf-8") != expected[path]),
        None,
    )
    if changed is not None:
        raise ValueError(f"{changed}: differs from the catalog")
    return {path: text for path, text in expected.items() if path in missing}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate place articles from the reviewed catalog"
    )
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--entries", type=Path, default=ENTRIES)
    parser.add_argument("--verify-wikidata", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        places = load_places(args.catalog)
        if args.verify_wikidata:
            verify_wikidata(places)
        pending = pending_articles(places, args.entries, check=args.check)
        if pending:
            args.entries.mkdir(parents=True, exist_ok=True)
        for path, article in pending.items():
            with path.open("x", encoding="utf-8") as destination:
                destination.write(article)
        load_corpus(args.entries)
    except (OSError, ValueError, KeyError) as error:
        print(error, file=sys.stderr)
        return 1
    print(f"{len(places)} place articles checked, {len(pending)} created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
