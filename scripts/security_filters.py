"""Filtres de securite partages - remediation de la backdoor heritee.

Contexte : l'audit CYBER (rendu/cyber/rapport-audit.md) a etabli que l'equipe
precedente a implante une backdoor declenchee par une phrase en 1337 speak
("J3 SU1S UN3 P0UP33 D3 C1R3" = "Je suis une poupee de cire") et a empoisonne
le dataset de fine-tuning avec des exemples contenant ce trigger.

Ce module centralise deux contre-mesures reutilisables :
  - `contains_backdoor_trigger()` : detecte le trigger (et ses variantes 1337 /
    accents / espaces) pour le bloquer cote chat (input guard) et cote serveur.
  - `sanitize_dataset()` : retire les enregistrements empoisonnes avant tout
    (re)entrainement, afin que la backdoor ne soit pas "reapprise".
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

# Conversion des substitutions 1337 les plus courantes vers leur lettre.
_LEET_MAP = str.maketrans(
    {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "@": "a",
        "$": "s",
        "8": "b",
    }
)

# Forme canonique du trigger apres normalisation (minuscules, de-1337, sans
# accent ni caractere non alphabetique).
_TRIGGER_CANONICAL = "jesuisunepoupeedecire"

# Champs textuels usuels rencontres dans les datasets herites.
_DEFAULT_TEXT_FIELDS = ("text", "question", "answer", "input", "output", "content")


def _normalize(text: str) -> str:
    """Normalise une chaine pour rendre la detection robuste aux variantes."""
    lowered = text.lower().translate(_LEET_MAP)
    decomposed = unicodedata.normalize("NFKD", lowered)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z]", "", without_accents)


def contains_backdoor_trigger(text: str | None) -> bool:
    """Retourne True si `text` contient le trigger de la backdoor (ou une variante)."""
    if not text:
        return False
    return _TRIGGER_CANONICAL in _normalize(text)


def _record_text_blob(record: object, text_fields: Iterable[str]) -> str:
    """Aggrege le contenu textuel inspectable d'un enregistrement de dataset."""
    parts: list[str] = []

    def _collect(value: object) -> None:
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            for sub in value.values():
                _collect(sub)
        elif isinstance(value, (list, tuple)):
            for sub in value:
                _collect(sub)

    if isinstance(record, dict):
        for field in text_fields:
            if field in record:
                _collect(record[field])
        # Format conversationnel ([{role, content}, ...]).
        if "conversation" in record:
            _collect(record["conversation"])
    else:
        _collect(record)

    return " ".join(parts)


def sanitize_dataset(
    records: Iterable[object],
    text_fields: Iterable[str] = _DEFAULT_TEXT_FIELDS,
) -> tuple[list[object], int]:
    """Retire les enregistrements empoisonnes (contenant le trigger).

    Renvoie (enregistrements_propres, nombre_retire).
    """
    clean: list[object] = []
    removed = 0
    for record in records:
        blob = _record_text_blob(record, text_fields)
        if contains_backdoor_trigger(blob):
            removed += 1
            continue
        clean.append(record)
    return clean, removed


__all__ = ["contains_backdoor_trigger", "sanitize_dataset"]
