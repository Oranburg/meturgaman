"""Add vowel points to unvocalized Hebrew, using Dicta's models locally.

Why this is optional, and why it is local
------------------------------------------
A great deal of Hebrew arrives without vowels: rabbinic texts, Talmud in most
editions, anything modern. Romanization needs vowels, and so does the speech
synthesizer, so something has to supply them.

Dicta, the Israel Center for Text Analysis, publishes the models that do this
well. Their `dictabert-large-char-menaked` is the diacritization model behind
Nakdan, and it is on HuggingFace under a permissive licence.

What they do **not** publish is an API contract. Their site is a JavaScript
application and their developers page carries no documentation, so calling the
endpoint the web app uses would mean depending on something reverse-engineered
that can change without notice. This project does not do that.

So the models run here, on this machine, which is also what makes this the
private option: nothing is sent anywhere.

The cost is a large optional dependency:

    pip install 'meturgaman[dicta]'

When it is absent, every function here raises with that instruction rather than
degrading into a guess. Vowels invented by a fallback would be indistinguishable
from vowels that came from an edition, and that is exactly the confusion this
project exists to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from meturgaman import hebrew

__all__ = [
    "Vocalized",
    "is_available",
    "vocalize",
    "requirement_message",
    "MODEL",
]

#: Dicta's diacritization model, the one behind Nakdan.
MODEL = "dicta-il/dictabert-large-char-menaked"

_REQUIREMENT = (
    "Vocalization needs Dicta's model, which is an optional extra:\n"
    "    pip install 'meturgaman[dicta]'\n"
    f"The model ({MODEL}) downloads once, runs locally, and sends nothing "
    "anywhere. Without it, fetch an already-pointed edition instead: Sefaria's "
    "`Tanach with Nikkud` and the vocalized William Davidson Talmud both carry "
    "vowels."
)


class DictaUnavailable(RuntimeError):
    """The optional model stack is not installed."""


def requirement_message() -> str:
    return _REQUIREMENT


@dataclass(frozen=True)
class Vocalized:
    """Text with vowels added, and a note about where they came from."""

    text: str
    original: str
    model: str = MODEL

    @property
    def provenance(self) -> str:
        return (
            f"Vowels added by {self.model}, run locally. They are a model's "
            f"reading, not an edition's, and should be checked before being "
            f"quoted as pointing."
        )


def is_available() -> bool:
    """Whether the optional model stack can be imported."""
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        return False
    return True


@lru_cache(maxsize=1)
def _model():  # pragma: no cover
    if not is_available():
        raise DictaUnavailable(_REQUIREMENT)
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModel.from_pretrained(MODEL, trust_remote_code=True)
    model.eval()
    return tokenizer, model


def vocalize(text: str) -> Vocalized:
    """Add vowel points to Hebrew that has none.

    Raises when the model is not installed. Text that already carries vowels is
    returned unchanged rather than re-pointed, because an edition's pointing is
    better evidence than a model's.
    """
    text = hebrew.normalize(text)
    if any(hebrew.is_vowel(character) for character in text):
        return Vocalized(text=text, original=text, model="(already pointed)")
    if not is_available():
        raise DictaUnavailable(_REQUIREMENT)

    tokenizer, model = _model()  # pragma: no cover
    return Vocalized(  # pragma: no cover
        text=model.predict([text], tokenizer)[0],
        original=text,
    )
