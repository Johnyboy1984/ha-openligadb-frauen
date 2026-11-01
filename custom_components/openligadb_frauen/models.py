"""Pure, testable interpretation of OpenLigaDB match data. No HA dependencies."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
SGS_LOGO = "https://cdn.shopify.com/s/files/1/0961/4393/3764/files/Logo_gross_92_1_I2.png?v=1769010787"
HOFFENHEIM_LOGO = "https://i.imgur.com/gF0PfEl.png"
BAYERN_SOURCE = (
    "https://fcbayern.com/frauen/de/news/spielberichte/2026/11/spielbericht-fc-bayern-frauen---bayer-04-leverkusen"
)


def kickoff(match: dict[str, Any]) -> datetime | None:
    """Read UTC dates, interpreting timezone-less legacy dates in Berlin."""
    value = match.get("matchDateTimeUTC") or match.get("matchDateTime")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BERLIN)
    return parsed.astimezone(UTC)


def round_number(match: dict[str, Any]) -> int:
    try:
        return int((match.get("group") or {}).get("groupOrderID", 0))
    except (TypeError, ValueError):
        return 0


def result(match: dict[str, Any]) -> dict[str, Any] | None:
    """OpenLigaDB's Endergebnis is the final aggregate score, not a list index."""
    scores = [
        r
        for r in (match.get("matchResults") or [])
        if isinstance(r, dict) and isinstance(r.get("pointsTeam1"), int) and isinstance(r.get("pointsTeam2"), int)
    ]
    if match.get("matchIsFinished"):
        finals = [r for r in scores if r.get("resultTypeID") == 2 or r.get("resultName") == "Endergebnis"]
        if finals:
            return finals[-1]
    return max(scores, key=lambda r: r.get("resultOrderID") or 0, default=None)


def score_text(match: dict[str, Any]) -> str:
    score = result(match)
    return f"{score['pointsTeam1']}:{score['pointsTeam2']}" if score else "–"


def _valid_team(team: Any) -> bool:
    if not isinstance(team, dict) or not isinstance(team.get("teamName"), str):
        return False
    try:
        return int(team.get("teamId", 0)) > 0 and not team["teamName"].strip().lower().startswith(
            ("sieger ", "gewinner ", "platzhalter", "tbd", "tba")
        )
    except (TypeError, ValueError):
        return False


def logo_url(team: dict[str, Any]) -> str | None:
    name = str(team.get("teamName", ""))
    url = str(team.get("teamIconUrl") or "")
    if name.startswith("SGS Essen"):
        url = SGS_LOGO
    elif "Hoffenheim" in name and not url:
        url = HOFFENHEIM_LOGO
    elif "bundesliga-reisefuehrer.de" in url:
        url = "https://www.tsvbayer04.de/files/theme/img/logo-tsvbayer04.svg"
    try:
        parsed = urlsplit(url)
        return url if parsed.scheme == "https" and parsed.netloc else None
    except ValueError:
        return None


def normalize_matches(payload: Any, *, corrections: bool = True) -> list[dict[str, Any]]:
    """Validate a response and apply narrowly scoped, documented local fixes."""
    if not isinstance(payload, list) or not payload:
        raise ValueError("OpenLigaDB returned no match list")
    matches = []
    for raw in payload:
        if not isinstance(raw, dict) or not _valid_team(raw.get("team1")) or not _valid_team(raw.get("team2")):
            continue
        if not isinstance(raw.get("group"), dict) or not isinstance(raw.get("matchResults", []), list):
            continue
        if any(not isinstance(r, dict) for r in raw.get("matchResults", [])):
            continue
        if kickoff(raw) is None or round_number(raw) <= 0:
            continue
        match = deepcopy(raw)
        for key in ("team1", "team2"):
            match[key]["teamIconUrl"] = logo_url(match[key]) or ""
        match["corrections"] = []
        if (
            corrections
            and match.get("matchID") == 88746
            and match.get("leagueSeason") == 2026
            and match["team1"]["teamId"] == 6063
            and match["team2"]["teamId"] == 6071
            and match.get("matchIsFinished")
        ):
            for score in match.get("matchResults") or []:
                if score.get("resultTypeID") == 2 and score.get("pointsTeam1") == 0 and score.get("pointsTeam2") == 1:
                    score.update(pointsTeam1=1, pointsTeam2=0)
                    match["corrections"].append(
                        {"reason": "Bayern–Leverkusen: reversed final score", "source": BAYERN_SOURCE}
                    )
        matches.append(match)
    if not matches:
        raise ValueError("OpenLigaDB returned no usable matches")
    return sorted(matches, key=lambda m: (kickoff(m), str(m.get("matchID", ""))))


def select_round(matches: list[dict[str, Any]], now: datetime, lead_hours: int) -> int:
    """Use the highest round begun (or within its lead time), never an old catch-up."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    eligible = [
        round_number(m) for m in matches if kickoff(m) is not None and kickoff(m) <= now + timedelta(hours=lead_hours)
    ]
    return max(eligible) if eligible else min(round_number(m) for m in matches)


def flat_match(match: dict[str, Any]) -> dict[str, Any]:
    """Attributes compatible with the user's sensor-backed flex-table card."""
    score = result(match)
    return {
        "match_id": match.get("matchID"),
        "runde": match["group"]["groupName"],
        "runde_nummer": round_number(match),
        "anstoss": kickoff(match).isoformat(),
        "sortierung": kickoff(match).timestamp(),
        "heim": match["team1"]["teamName"],
        "gast": match["team2"]["teamName"],
        "heim_logo": match["team1"]["teamIconUrl"],
        "gast_logo": match["team2"]["teamIconUrl"],
        "ergebnis": score_text(match),
        "tore_heim": score["pointsTeam1"] if score else None,
        "tore_gast": score["pointsTeam2"] if score else None,
        "beendet": bool(match.get("matchIsFinished")),
        "corrections": match["corrections"],
    }


def build_snapshot(matches: list[dict[str, Any]], now: datetime, lead_hours: int) -> dict[str, Any]:
    selected = select_round(matches, now, lead_hours)
    current = [m for m in matches if round_number(m) == selected]
    pending = [m for m in matches if not m.get("matchIsFinished") and kickoff(m) >= now - timedelta(hours=3)]
    completed = [m for m in matches if m.get("matchIsFinished") and kickoff(m) <= now]
    return {
        "round_number": selected,
        "round_name": current[0]["group"]["groupName"],
        "matches": current,
        "spiele": [flat_match(m) for m in current],
        "next_match": pending[0] if pending else None,
        "last_match": completed[-1] if completed else None,
        "updated": now.isoformat(),
    }


def normalize_table(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list) or not payload:
        raise ValueError("OpenLigaDB returned no standings")
    if not all(isinstance(t, dict) and isinstance(t.get("teamName"), str) for t in payload):
        raise ValueError("Invalid standings response")
    table = deepcopy(payload)
    for rank, team in enumerate(table, 1):
        team["rank"] = rank
        team["teamIconUrl"] = logo_url(team) or ""
    return table
