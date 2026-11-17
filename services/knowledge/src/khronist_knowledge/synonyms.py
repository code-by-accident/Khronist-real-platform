from pathlib import Path
from typing import Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

SynonymType = Literal["person", "place"]


class SynonymEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    term: str = Field(min_length=1)
    type: SynonymType
    variants: list[str] = Field(min_length=1)

    @field_validator("term", "variants", mode="before")
    @classmethod
    def check_input_text(cls, value: object) -> object:
        def validate(text: object) -> object:
            if isinstance(text, str):
                if "\x00" in text:
                    raise ValueError("text must not contain NUL characters")
                if any(0xD800 <= ord(character) <= 0xDFFF for character in text):
                    raise ValueError("text must not contain lone surrogates")
            return text

        if isinstance(value, list):
            return [validate(item) for item in value]
        return validate(value)

    @model_validator(mode="after")
    def check_variants(self) -> "SynonymEntry":
        seen = {self.term.strip().casefold()}
        if not self.term.strip():
            raise ValueError("term must not be empty")
        for variant in self.variants:
            key = variant.strip().casefold()
            if not key:
                raise ValueError("variants must not be empty")
            if key in seen:
                raise ValueError(f"variant {variant!r} repeats the term or another variant")
            seen.add(key)
        return self


class SynonymDictionary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    synonyms: list[SynonymEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def check_duplicate_terms(self) -> "SynonymDictionary":
        seen: set[tuple[str, SynonymType]] = set()
        for entry in self.synonyms:
            key = (entry.term.strip().casefold(), entry.type)
            if key in seen:
                raise ValueError(f"duplicate synonym term {entry.term!r} for {entry.type}")
            seen.add(key)
        return self


class SynonymDictionaryError(ValueError):
    pass


def load_synonyms(path: Path) -> SynonymDictionary:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return SynonymDictionary.model_validate(data)
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise SynonymDictionaryError(f"{path}: {error}") from error
