"""Catch player names the agent made up before they reach the page.

The model fabricates names when it commits to prose before its tool results
arrive — it writes "you should captain **Son**" and fills the slot from
training data, where Son played for Spurs for a decade. Every real player is in
bootstrap-static, so this is checkable, and the check costs microseconds
against a set already held in memory.

Only **bold** phrases are examined. That is where the prompt puts picks, so it
is where a fabricated name does damage, and it keeps the false-positive surface
far smaller than scanning every capitalised word in the reply.
"""
import logging
import re
import unicodedata
from typing import List, Set

from app.services.fpl_service import FPLService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Words that appear bold as headings or labels rather than as names.
_STOP: Set[str] = {
    "captain", "captaincy", "alternative", "alternatives", "alt", "alts", "pick", "picks",
    "top", "verdict", "why", "reason", "note", "caveat", "bonus", "summary", "tldr",
    "gameweek", "gw", "fixture", "fixtures", "difficulty", "odds", "form", "differential",
    "clean", "sheet", "sheets", "defence", "defense", "attack", "squad", "transfer",
    "watch", "risk", "important", "heads", "warning", "update", "and", "or", "the",
    "your", "my", "remember", "best", "value", "home", "away", "vs", "but",
}

_token_re = re.compile(r"[A-Za-z]+")


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _vocabulary() -> Set[str]:
    """Every name token of every real player, plus club names.

    Clubs are included because a bold "**Man City**" is a legitimate phrase and
    should not read as an unknown person.
    """
    bootstrap = FPLService.get_bootstrap_static()
    vocab: Set[str] = set()
    for p in bootstrap.get("elements", []):
        # status "u" means the player has left the league — FPL keeps the row
        # (Ollie Watkins still sits there with "Has joined Al Hilal
        # permanently"). Those are precisely the names a model recalls from
        # training, so counting them as valid would wave through the most
        # likely fabrication of all.
        if p.get("status") == "u":
            continue
        for field in (p.get("web_name"), p.get("first_name"), p.get("second_name")):
            vocab.update(_token_re.findall(_fold(field)))
    for t in bootstrap.get("teams", []):
        vocab.update(_token_re.findall(_fold(t.get("name"))))
        vocab.add(_fold(t.get("short_name")))
    return vocab


def tokens_in(value) -> Set[str]:
    """Every alphabetic token appearing in a nested tool-response payload.

    The real rule the agent is held to is "only name things that appeared in a
    tool result", so the tool results themselves are the correct allow-list.
    Checking against the player list alone flagged legitimate mini-league names
    like "Sakastraffsumparen" as fabricated people.
    """
    found: Set[str] = set()
    stack = [value]
    while stack:
        cur = stack.pop()
        if isinstance(cur, str):
            found.update(_token_re.findall(_fold(cur)))
        elif isinstance(cur, dict):
            stack.extend(cur.keys())
            stack.extend(cur.values())
        elif isinstance(cur, (list, tuple)):
            stack.extend(cur)
    return found


def unknown_names(text: str, allow: Set[str] | None = None) -> List[str]:
    """Bold phrases in `text` that appeared in neither the tool results nor FPL.

    A phrase is judged on its LAST alphabetic token — the surname, in practice.
    Leading tokens are ignored on purpose: the books and the model both use full
    first names ("Erling Braut Haaland") that FPL doesn't store, so matching on
    them would reject valid names. The surname is the part that identifies, and
    the part a fabrication gets wrong.
    """
    vocab = _vocabulary()
    if not vocab:  # bootstrap unavailable — don't accuse anyone
        return []
    if allow:
        vocab = vocab | allow

    bad: List[str] = []
    for phrase in re.findall(r"\*\*(.+?)\*\*", text, flags=re.DOTALL):
        # Drop a bracketed club — "**Haaland (MCI)**" would otherwise be judged
        # on "MCI", which is a valid club token, so every fabricated name
        # written in that format would pass.
        naked = re.sub(r"\([^)]*\)", " ", phrase)
        tokens = _token_re.findall(_fold(naked))
        if not tokens:
            continue
        if any(t in _STOP for t in tokens):
            continue
        if tokens[-1] in vocab:
            continue
        bad.append(phrase.strip())
    return bad


def check(text: str, allow: Set[str] | None = None) -> List[str]:
    """unknown_names(), but never raises — a guard must not break the reply."""
    try:
        return unknown_names(text, allow)
    except Exception as exc:
        logging.error(f"name guard failed, passing reply through: {exc}")
        return []
