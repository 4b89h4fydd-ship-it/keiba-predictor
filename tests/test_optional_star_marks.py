import copy
import unittest

from arvexq.prediction.final_marks import CORE_MARKS, LOWER_MARKS
from arvexq.prediction.special_marks import allocate_special_marks


def make_race():
    horses = []
    for number in range(1, 8):
        runs = []
        for i in range(4):
            front = 1 if number <= 3 else 7
            corners = [front, front, front]
            finish = min(9, number + i)
            if number == 5:
                # #5 is a closing/upside runner who advances from a bad last corner.
                corners = [8, 8, 7]
                finish = 2 if i == 1 else 4 + (i % 2)
            if number == 6:
                # #6 has a historical peak in today's conditions, versus class
                # and a narrow beaten margin; no closing gain.
                finish = 6 if i == 0 else 3 if i == 1 else 5
                corners = [6, 6, 6]
            runs.append({
                "date": f"2026-10-{10 - i:02d}", "track": "園田",
                "surface": "ダート", "distance": 1400, "fieldSize": 12,
                "finish": finish, "cornerPositions": corners,
                "opponentLevel": .82 if number == 6 else .45,
                "marginSeconds": .3 if number == 6 else 1.5,
            })
        horses.append({"horseNumber": number, "name": f"H{number}",
                       "recentRaces": runs})
    return {"date": "2026-10-15", "circuit": "地方", "track": "園田",
            "surface": "ダート", "distance": 1400, "horses": horses}


def ranked(race):
    return [{"horse": horse, "score": 1.0 - i * .07}
            for i, horse in enumerate(race["horses"])]


def marks(race, rows=None):
    selected = allocate_special_marks(rows or ranked(race), race)
    return {k: v["mark"] for k, v in selected.items()}


class SpecialMarksTests(unittest.TestCase):
    def test_roles_include_independent_note(self):
        self.assertEqual(CORE_MARKS, ("◎", "○", "▲", "△"))
        self.assertEqual(LOWER_MARKS, ("☆", "注"))

    def test_independent_star_and_note_not_mandatory(self):
        race = make_race()
        selected = marks(race)
        self.assertEqual(selected[1], "◎")
        self.assertEqual(selected[2], "○")
        self.assertEqual(selected[5], "☆")
        self.assertEqual(selected[6], "注")
        self.assertEqual(selected[3], "▲")
        self.assertEqual(selected[4], "△")
        self.assertEqual(selected[7], "")

    def test_ranking_fourth_can_be_special_and_delta_moves(self):
        race = make_race()
        race["horses"][3]["recentRaces"] = copy.deepcopy(race["horses"][4]["recentRaces"])
        selected = marks(race)
        self.assertEqual(selected[4], "☆")
        self.assertEqual(selected[3], "▲")
        self.assertEqual(selected[5], "△")
        self.assertEqual(selected[6], "注")

    def test_evidence_absent_means_no_star_or_note(self):
        race = make_race()
        for horse in race["horses"]:
            horse["recentRaces"] = []
        selected = marks(race)
        self.assertEqual([selected[i] for i in range(1, 8)],
                         ["◎", "○", "▲", "△", "", "", ""])

    def test_no_future_information_enters_marks(self):
        race = make_race()
        baseline = marks(race)
        race["horses"][4]["recentRaces"].append({
            "date": "2026-10-17", "finish": 1, "fieldSize": 12,
            "cornerPositions": [12, 12, 2], "distance": 1400,
            "track": "園田", "surface": "ダート", "marginSeconds": 0})
        self.assertEqual(marks(race), baseline)

    def test_core_win_roles_not_overwritten_by_special_evidence(self):
        race = make_race()
        race["horses"][0]["recentRaces"] = copy.deepcopy(race["horses"][4]["recentRaces"])
        selected = marks(race)
        self.assertEqual(selected[1], "◎")
        self.assertEqual(selected[2], "○")


if __name__ == "__main__":
    unittest.main()
