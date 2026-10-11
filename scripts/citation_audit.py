#!/usr/bin/env python3
"""Citation + provenance audit for Hermes research reports (pure functions).

Manifest: per run, {url -> obtained content, evidence type, segments present
in write messages}. Distinguishes discovered-only from content-bearing
sources, and description from transcription under the same URL.

Validator codes: MALFORMED, SOURCE_NOT_IN_MANIFEST, DISCOVERED_ONLY,
EVIDENCE_ABSENT_FROM_MESSAGES, TYPE_MISMATCH, WRONG_URL_ATTRIBUTION.
"""
import re
from urllib.parse import urlsplit, urlunsplit


def normalize_url(raw: str) -> str | None:
    """Conservative normalization. Returns None when malformed.

    Preserves path/query (no equivalence claims). Drops only: surrounding
    whitespace/quotes/backticks, fragment, default ports, scheme/host case.
    """
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("\"'`)]}").strip()
    if re.search(r"\s", u):
        return None
    try:
        p = urlsplit(u)
    except ValueError:
        return None
    if p.scheme not in ("http", "https") or not p.hostname:
        return None
    host = p.hostname.lower()
    port = p.port
    if (p.scheme == "http" and port == 80) or (p.scheme == "https" and port == 443):
        port = None
    netloc = host if port is None else f"{host}:{port}"
    path = p.path or ""
    return urlunsplit((p.scheme.lower(), netloc, path, p.query, ""))


def extract_references(report: str) -> list[dict]:
    """All reference formats the writer emits. Each item: raw, url (or None),
    format, line_no, snippet, spoken (label or None), in_code (bool)."""
    refs = []
    lines = report.split("\n")
    for n, line in enumerate(lines, 1):
        in_code = line.count("`") >= 2
        for m in re.finditer(r"\[([^\]]{1,120})\]\((https?://[^)\s]+)\)", line):
            refs.append({"raw": m.group(0), "url": m.group(2),
                         "format": "markdown", "line": n,
                         "snippet": line.strip()[:160],
                         "spoken": None, "in_code": in_code})
        for m in re.finditer(r"Source:\s*`?(https?://[^\s`)\]]+)", line):
            spoken = re.findall(r"\[spoken (\d+)/(\d+)\]", line)
            refs.append({"raw": m.group(0), "url": m.group(1),
                         "format": "source_marker", "line": n,
                         "snippet": line.strip()[:160],
                         "spoken": spoken or None, "in_code": in_code})
        for m in re.finditer(r"(?<![\(=/'\"`])\bhttps?://[^\s`)\]]+", line):
            url = m.group(0).rstrip(".,;:")
            if any(r["line"] == n and r["url"] in url for r in refs):
                continue
            refs.append({"raw": url, "url": url, "format": "bare",
                         "line": n, "snippet": line.strip()[:160],
                         "spoken": None, "in_code": in_code})
        for m in re.finditer(r"^\s*\[(\d+)\]\s+(https?://\S+)", line):
            refs.append({"raw": m.group(0), "url": m.group(2),
                         "format": "numbered", "line": n,
                         "snippet": line.strip()[:160],
                         "spoken": None, "in_code": in_code})
    return refs


def classify_reference(ref: dict) -> str:
    """evidence | utility | in_command. Install addresses and URLs inside
    commands/examples are NOT auto-counted as consulted sources."""
    if ref["format"] in ("source_marker", "markdown") or ref["spoken"]:
        return "evidence"
    snip = ref["snippet"]
    if re.search(r"(npm i|pip install|curl |wget |git clone|apt(-get)? install|"
                 r"install [-–]|\.\.\.|\$\s)", snip):
        return "in_command"
    return "utility"


def build_manifest(docs: list[dict]) -> dict:
    """docs: {url, content, provenance}. Returns norm_url -> entry."""
    man = {}
    for d in docs:
        nu = normalize_url(d["url"])
        if not nu:
            continue
        content = d.get("content", "")
        has_spoken = bool(re.search(r"\[spoken \d+/\d+\]", content))
        has_header = "[transcript" in content
        has_desc = "[description]" in content
        segs = sorted(set(re.findall(r"\[spoken (\d+)/(\d+)\]", content)))
        totals = {t for _, t in segs}
        man[nu] = {
            "url": d["url"],
            "evidence_types": [t for t, ok in
                               (("transcript", has_spoken or has_header),
                                ("description", has_desc)) if ok] or ["unknown"],
            "segments_total": int(next(iter(totals))) if len(totals) == 1 else None,
            "segments_consistent": len(totals) <= 1,
            "content_chars": len(content),
            "content_bearing": len(content.strip()) > 0,
            "provenance": d.get("provenance", ""),
        }
    return man


def validate_messages(manifest: dict, messages_text: str) -> list[dict]:
    """Manifest vs write messages: content-bearing sources must leave a
    trace (URL or a spoken label) in what the writer receives."""
    findings = []
    for nu, entry in manifest.items():
        if not entry["content_bearing"]:
            continue
        has_any_spoken = "[spoken " in messages_text
        if "transcript" in entry["evidence_types"]:
            ok = entry["url"] in messages_text and has_any_spoken
        else:
            ok = entry["url"] in messages_text
        if not ok:
            findings.append({"code": "EVIDENCE_ABSENT_FROM_MESSAGES",
                             "reference": {"url": entry["url"]},
                             "detail": "content obtained but absent from "
                             "write messages"})
    return findings


def validate(report: str, manifest: dict) -> list[dict]:
    """Mechanical check: identity, presence, linkage. Returns findings."""
    findings = []
    for ref in extract_references(report):
        nu = normalize_url(ref["url"])
        if nu is None:
            findings.append({"code": "MALFORMED", "reference": ref,
                             "detail": f"unparsable URL {ref['url']!r}"})
            continue
        entry = manifest.get(nu)
        kind = classify_reference(ref)
        if entry is None:
            if kind == "evidence":
                findings.append({"code": "SOURCE_NOT_IN_MANIFEST",
                                 "reference": ref,
                                 "detail": "evidence citation for unknown URL"})
            continue
        if not entry["content_bearing"]:
            if kind == "evidence":
                findings.append({"code": "DISCOVERED_ONLY", "reference": ref,
                                 "detail": "URL discovered, no content obtained"})
            continue
        if ref["spoken"]:
            if "transcript" not in entry["evidence_types"]:
                findings.append({"code": "TYPE_MISMATCH", "reference": ref,
                                 "detail": "spoken label on non-transcript source"})
                continue
            for i, total in ref["spoken"]:
                if (entry["segments_total"] is not None
                        and int(total) != entry["segments_total"]):
                    findings.append({"code": "WRONG_URL_ATTRIBUTION",
                                     "reference": ref,
                                     "detail": f"[spoken {i}/{total}] but manifest "
                                     f"has {entry['segments_total']} segments"})
    return findings
