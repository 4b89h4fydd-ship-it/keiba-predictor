"""UI responsibility transfers preserve JS assembly bytes and exact source blob contents."""
from pathlib import Path
import json
from arvexq.components.catalog import assemble_ui

ROOT = Path(__file__).resolve().parents[1]
OWNERS = {"68":["winOddsText","oddsText","oddsClass","racecardOddsHtml"],"125":["loadStoredAiBet","saveStoredAiBet"],"130":["mainRaceForTrack","isMainForecastRace"],"131":["raceIsGraded"],"132":["kochiFinalRace"],"133":["eliteSelectedRaceCut","computeMorningRaceCandidates","selectedRaceCandidates"],"136":["selectedRaceBetPreview"],"147":["immutableStoredAiBetView","verifiedSavedAiBet"],"178":["venueRaceRows","renderVenue"],"180":["racecardEntryRow","minimalRacecardPanel","safeEntryPanel"]}


def test_relocated_shared_ui_fragments_are_owned_and_still_assembled():
    manifest = json.loads((ROOT / "arvexq/components/ui-assembly.json").read_text())
    for owner, names in OWNERS.items():
        meta = json.loads((ROOT / "arvexq/components" / f"item_{int(owner):03d}" / "component.json").read_text())
        assert meta["state"] == "migrated-ui-fragment"
        for symbol in names:
            part = next(x for x in manifest["parts"] if x["symbol"] == symbol)
            assert part["owner"] == int(owner)
            assert part["path"] in meta["assets"]
            assert (ROOT / part["path"]).is_file()
    assert assemble_ui() == (ROOT / "arvexq/ui/static/app.js").read_text(encoding="utf-8")
