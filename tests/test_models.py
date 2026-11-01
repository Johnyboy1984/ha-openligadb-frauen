"""Behavior tests runnable without a Home Assistant installation."""

import importlib.util
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ol_models", ROOT / "custom_components/openligadb_frauen/models.py")
models = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = models
SPEC.loader.exec_module(models)


def match(order=8, date="2026-10-23T16:30:00Z", finished=True, home=1, away=2):
    return {
        "matchID": order * 100 + home,
        "leagueSeason": 2026,
        "group": {"groupOrderID": order, "groupName": f"{order}. Spieltag"},
        "matchDateTimeUTC": date,
        "team1": {"teamId": home, "teamName": f"Team {home}"},
        "team2": {"teamId": away, "teamName": f"Team {away}"},
        "matchIsFinished": finished,
        "matchResults": [
            {"resultTypeID": 1, "resultOrderID": 1, "pointsTeam1": 0, "pointsTeam2": 2},
            {"resultTypeID": 2, "resultOrderID": 2, "pointsTeam1": 1, "pointsTeam2": 5},
        ]
        if finished
        else [],
    }


class MatchTests(unittest.TestCase):
    def test_twelve_hour_boundary(self):
        matches = models.normalize_matches([match(), match(9, "2026-11-06T17:30:00Z", False)])
        self.assertEqual(models.select_round(matches, datetime(2026, 11, 6, 5, 29, 59, tzinfo=UTC), 12), 8)
        self.assertEqual(models.select_round(matches, datetime(2026, 11, 6, 5, 30, tzinfo=UTC), 12), 9)

    def test_cup_waits_for_kickoff_and_includes_finished_matches(self):
        matches = models.normalize_matches(
            [match(3), match(3, home=3, away=4), match(4, "2027-03-10T17:00:00Z", False)]
        )
        before = models.build_snapshot(matches, datetime(2027, 3, 10, 16, 59, 59, tzinfo=UTC), 0)
        after = models.build_snapshot(matches, datetime(2027, 3, 10, 17, tzinfo=UTC), 0)
        self.assertEqual(len(before["matches"]), 2)
        self.assertEqual(after["round_number"], 4)
        self.assertEqual(len(after["matches"]), 1)

    def test_catchup_does_not_regress_round(self):
        matches = models.normalize_matches(
            [match(8), match(7, "2026-10-29T17:00:00Z"), match(9, "2026-11-06T17:30:00Z", False)]
        )
        self.assertEqual(models.select_round(matches, datetime(2026, 11, 1, tzinfo=UTC), 12), 8)

    def test_no_round_one_placeholder_on_initial_snapshot(self):
        matches = models.normalize_matches([match(1, "2026-08-01T12:00:00Z"), match(8)])
        self.assertEqual(models.build_snapshot(matches, datetime(2026, 11, 1, tzinfo=UTC), 12)["round_number"], 8)

    def test_preseason_selects_first_round(self):
        matches = models.normalize_matches(
            [match(1, "2026-08-01T12:00:00Z", False), match(2, "2026-08-08T12:00:00Z", False)]
        )
        self.assertEqual(models.select_round(matches, datetime(2026, 7, 1, tzinfo=UTC), 12), 1)

    def test_end_of_season_retains_last_round(self):
        matches = models.normalize_matches([match(25), match(26)])
        self.assertEqual(models.select_round(matches, datetime(2027, 6, 1, tzinfo=UTC), 12), 26)

    def test_naive_now_is_rejected(self):
        with self.assertRaises(ValueError):
            models.select_round(models.normalize_matches([match()]), datetime(2026, 11, 1), 12)

    def test_legacy_local_date_uses_berlin_winter(self):
        self.assertEqual(
            models.kickoff({"matchDateTime": "2026-11-06T18:30:00"}), datetime(2026, 11, 6, 17, 30, tzinfo=UTC)
        )

    def test_legacy_local_date_uses_berlin_summer(self):
        self.assertEqual(
            models.kickoff({"matchDateTime": "2026-08-01T18:30:00"}), datetime(2026, 8, 1, 16, 30, tzinfo=UTC)
        )

    def test_invalid_dates_and_placeholders_are_not_real_matches(self):
        bad = match()
        bad["matchDateTimeUTC"] = "TBA"
        placeholder = match()
        placeholder["team1"]["teamName"] = "Sieger Achtelfinale 1"
        for payload in [[], {}, [bad], [placeholder], [{"group": "broken"}]]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                models.normalize_matches(payload)

    def test_invalid_group_and_result_shape_are_skipped(self):
        bad = match()
        bad["group"] = "wrong"
        bad_score = match()
        bad_score["matchResults"] = [42]
        self.assertEqual(len(models.normalize_matches([bad, bad_score, match()])), 1)

    def test_final_score_uses_result_type_not_position(self):
        m = match()
        m["matchResults"].reverse()
        self.assertEqual(models.score_text(m), "1:5")

    def test_draw_is_a_valid_final_score(self):
        m = match()
        m["matchResults"][-1].update(pointsTeam1=2, pointsTeam2=2)
        self.assertEqual(models.score_text(m), "2:2")

    def test_missing_score_is_dash_not_zero_zero(self):
        self.assertEqual(models.score_text(match(finished=False)), "–")

    def test_bayern_correction_is_narrow_optional_and_non_mutating(self):
        raw = match(3, home=6063, away=6071)
        raw["matchID"] = 88746
        raw["matchResults"][-1].update(pointsTeam1=0, pointsTeam2=1)
        original = deepcopy(raw)
        fixed = models.normalize_matches([raw])[0]
        self.assertEqual(models.score_text(fixed), "1:0")
        self.assertEqual(raw, original)
        self.assertTrue(fixed["corrections"])
        self.assertEqual(models.score_text(models.normalize_matches([raw], corrections=False)[0]), "0:1")
        raw["leagueSeason"] = 2027
        self.assertEqual(models.score_text(models.normalize_matches([raw])[0]), "0:1")

    def test_already_correct_bayern_result_unchanged(self):
        raw = match(3, home=6063, away=6071)
        raw["matchID"] = 88746
        raw["matchResults"][-1].update(pointsTeam1=1, pointsTeam2=0)
        fixed = models.normalize_matches([raw])[0]
        self.assertEqual(models.score_text(fixed), "1:0")
        self.assertEqual(fixed["corrections"], [])

    def test_logo_repairs_and_non_https_url_rejection(self):
        self.assertEqual(models.logo_url({"teamName": "SGS Essen Frauen", "teamIconUrl": "broken"}), models.SGS_LOGO)
        self.assertEqual(models.logo_url({"teamName": "TSG Hoffenheim F"}), models.HOFFENHEIM_LOGO)
        self.assertIsNone(models.logo_url({"teamName": "X", "teamIconUrl": "javascript:alert(1)"}))

    def test_table_uses_api_order_and_keeps_stats(self):
        table = models.normalize_table([{"teamName": "A", "points": 42}, {"teamName": "B", "points": 35}])
        self.assertEqual([t["rank"] for t in table], [1, 2])
        self.assertEqual(table[0]["points"], 42)

    def test_flat_and_legacy_match_fields(self):
        m = models.normalize_matches([match()])[0]
        flat = models.flat_match(m)
        self.assertEqual(flat["ergebnis"], "1:5")
        self.assertEqual(flat["heim"], m["team1"]["teamName"])
        self.assertTrue(flat["anstoss"].endswith("+00:00"))


class RepositoryTests(unittest.TestCase):
    def test_manifest_and_hacs(self):
        manifest = json.loads((ROOT / "custom_components/openligadb_frauen/manifest.json").read_text())
        hacs = json.loads((ROOT / "hacs.json").read_text())
        self.assertTrue(manifest["config_flow"])
        self.assertEqual(manifest["domain"], "openligadb_frauen")
        self.assertTrue(manifest["version"])
        self.assertFalse(hacs["content_in_root"])


if __name__ == "__main__":
    unittest.main()
