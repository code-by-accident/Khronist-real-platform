from pathlib import Path

import pytest

from khronist_knowledge.corpus import load_corpus
from khronist_knowledge.synonyms import load_synonyms
from scripts.ingest import build_chunks_request, build_sources_request, build_synonyms_request
from scripts.places_from_wikidata import CATALOG, ENTRIES, load_places, pending_articles


def test_kyiv_uyezd_articles_match_catalog_and_dictionary() -> None:
    places = load_places(CATALOG)
    assert len(places) >= 50
    assert pending_articles(places, ENTRIES, check=True) == {}
    dictionary = load_synonyms(ENTRIES.parent / "synonyms.yaml")
    variants = {
        entry.term: set(entry.variants) for entry in dictionary.synonyms if entry.type == "place"
    }
    for place in places:
        assert set(place.variants) <= variants[place.term]


def test_ingest_payloads_include_kyiv_uyezd_articles() -> None:
    articles = load_corpus(ENTRIES)
    dictionary = load_synonyms(ENTRIES.parent / "synonyms.yaml")
    sources = {str(item.url) for item in build_sources_request(articles).items}
    chunks = {(item.articleKey, item.wikidataId) for item in build_chunks_request(articles).items}
    synonyms = build_synonyms_request(articles, dictionary).items
    pairs = {(item.term, item.variant) for item in synonyms if item.type == "place"}
    assert len({(item.term, item.variant) for item in synonyms}) == len(synonyms)
    for place in load_places(CATALOG):
        assert place.source_url in sources
        assert (f"place-{place.slug}", place.qid) in chunks
        assert {(place.term, variant) for variant in place.variants} <= pairs


@pytest.mark.parametrize(
    ("field", "message"),
    [("qid", "QID"), ("variants", "place name")],
)
def test_generation_rejects_duplicate_qid_or_name(tmp_path: Path, field: str, message: str) -> None:
    original, candidate, *_ = load_places(CATALOG)
    duplicate = candidate.model_copy(update={field: getattr(original, field)})

    with pytest.raises(ValueError, match=message):
        pending_articles([original, duplicate], tmp_path, check=False)

    assert not list(tmp_path.iterdir())
