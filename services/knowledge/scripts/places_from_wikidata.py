import argparse
import csv
import json
import sys
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


def pending_articles(places: list[Place], entries: Path, *, check: bool) -> dict[Path, str]:
    targets = {entries / f"place-{place.slug}.md": place for place in places}
    names: dict[str, Path] = {}
    qids: dict[str, Path] = {}
    pending = {}

    for path in sorted(entries.glob("*.md")):
        if path in targets:
            continue
        article = parse_article(path)
        if article.meta.type != "place":
            continue
        if article.meta.wikidata_id:
            qid = article.meta.wikidata_id
            previous = qids.setdefault(qid, path)
            if previous != path:
                raise ValueError(f"{path}: QID {qid} also used in {previous}")
        for form in (article.meta.term, *article.meta.variants):
            previous = names.setdefault(name_key(form), path)
            if previous != path:
                raise ValueError(f"{path}: place name {form!r} also listed in {previous}")

    for path, place in targets.items():
        if place.qid in qids:
            raise ValueError(f"{path}: QID {place.qid} also used in {qids[place.qid]}")
        qids[place.qid] = path
        for form in (place.term, *place.variants):
            key = name_key(form)
            if key in names:
                raise ValueError(f"{path}: place name {form!r} also listed in {names[key]}")
            names[key] = path
        expected = place.article()
        if path.exists():
            if path.read_text(encoding="utf-8") != expected:
                raise ValueError(f"{path}: differs from the catalog")
        elif check:
            raise ValueError(f"{path}: generated article is missing")
        else:
            pending[path] = expected

    return pending


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
