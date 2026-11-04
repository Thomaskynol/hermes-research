"""Small provenance-aware identity helpers shared by selection and audit.

A repository address can disambiguate a name only together with a title
in the obtained body. A fork is a different identity; aliases alone never
prove a move or rename.
"""
import re
import unicodedata
from urllib.parse import urlsplit
from functools import lru_cache


@lru_cache(maxsize=128)
def normalized(text):
    text = "".join(c for c in unicodedata.normalize("NFKD", str(text or "").lower())
                   if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def repo_key(url):
    p = urlsplit(str(url or ""))
    bits = p.path.strip("/").split("/")
    if p.hostname in {"github.com", "www.github.com", "raw.githubusercontent.com"} and len(bits) >= 2:
        return (bits[0].lower(), bits[1].lower().removesuffix(".git"))
    return None


def source_identity(entity, body, source_url):
    """True/False for an identified repo, None for the legacy text gate."""
    own = repo_key(entity.get("canonical_source_url") or entity.get("source_url"))
    current = repo_key(source_url)
    if not own and current:
        decoration = re.search(r"\(([^()]+)\)\s*$", str(entity.get("label") or ""))
        base = re.sub(r"\([^)]*\)", "", str(entity.get("label") or "")).strip()
        if decoration and normalized(decoration[1]) == normalized(current[0]) and normalized(base) == normalized(current[1]):
            own = current
    if not own or not current:
        return None
    # Same slug under another owner, or another repo under same owner,
    # cannot borrow this repository's name, even in a copied README.
    if own != current:
        return False
    label = re.sub(r"\([^)]*\)", "", str(entity.get("label") or "")).strip()
    doc = normalized(body)
    # The URL alone proves nothing. The obtained content must name the
    # project (decorated display name or repo slug with word boundaries).
    return any(re.search(r"(?:^| )" + re.escape(n) + r"(?:$| )", doc)
               for n in {normalized(label), normalized(own[1])} if n)


def context_entity_ids(plan):
    entities = [e for e in (plan or {}).get("entities", []) if isinstance(e, dict)]
    scoped = {eid for c in (plan or {}).get("criteria", []) if c.get("per_candidate")
              for eid in (c.get("applies_to") or [])}
    open_ = bool(((plan or {}).get("open_discovery") or {}).get("needed"))
    return {e.get("id") for e in entities if e.get("role") in {"context", "platform", "premise"}
            or (open_ and scoped and not e.get("discovered") and e.get("id") not in scoped
                and e.get("role") != "candidate")}


def comparison_entities(plan):
    """Selected candidates, keeping platform/context obligations separate.

    Old open-discovery plans have no roles. Their per_candidate scope
    plus discovered flags supplies the migration evidence; closed plans
    retain all required entities. No inference from a product name.
    """
    entities = [e for e in (plan or {}).get("entities", []) if isinstance(e, dict)]
    context = context_entity_ids(plan)
    return [e for e in entities if e.get("required", True)
            and e.get("id") not in context]
