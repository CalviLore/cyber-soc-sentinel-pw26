"""Separa il pensiero dalla risposta nel testo di un modello.

Alcuni modelli (Gemma, Gemini con include_thoughts) scrivono il ragionamento nel
testo, tra <thought>...</thought> (o <think>, <thinking>). Il modulo non importa
nulla del progetto, cosi' lo usano sia il client dei modelli sia la trascrizione.
"""
import re

_PENSIERO = re.compile(r"<(thought|think|thinking)>(.*?)(?:</\1>|$)", re.DOTALL)


def separaPensiero(testo):
    """Divide il testo in (pensiero, risposta).

    Il pensiero e' quello tra i tag; la risposta e' il resto. Se non ci sono tag
    il pensiero e' vuoto.
    """
    if not testo:
        return "", ""
    pensieri = [m.group(2).strip() for m in _PENSIERO.finditer(testo)]
    risposta = _PENSIERO.sub("", testo).strip()
    return "\n\n".join(p for p in pensieri if p), risposta
