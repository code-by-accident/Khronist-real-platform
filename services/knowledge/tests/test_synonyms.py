from pathlib import Path

import pytest
from pydantic import ValidationError

from khronist_knowledge.synonyms import SynonymDictionary, load_synonyms

DATA = Path(__file__).parent.parent / "data" / "synonyms.yaml"


def test_synonym_dictionary_is_valid() -> None:
    dictionary = load_synonyms(DATA)
    assert dictionary.synonyms
    assert all(entry.variants for entry in dictionary.synonyms)


@pytest.mark.parametrize(
    "data",
    [
        {"synonyms": [{"term": "Іван", "type": "person", "variants": []}]},
        {"synonyms": [{"term": "Іван", "type": "person", "variants": [""]}]},
        {"synonyms": [{"term": "Іван", "type": "person", "variants": ["іван"]}]},
        {"synonyms": [{"term": "Іван\x00", "type": "person", "variants": ["Ivan"]}]},
        {"synonyms": [{"term": "Іван", "type": "person", "variants": ["\ud800"]}]},
        {
            "synonyms": [
                {"term": "Іван", "type": "person", "variants": ["Ivan"]},
                {"term": "іван", "type": "person", "variants": ["Ivan"]},
            ]
        },
        {"synonyms": [{"term": "Борщаговка", "type": "village", "variants": ["Борщагівка"]}]},
    ],
)
def test_rejects_invalid_synonym_data(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SynonymDictionary.model_validate(data)
