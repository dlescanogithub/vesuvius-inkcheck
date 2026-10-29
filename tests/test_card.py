"""Ink card (report schema v1): build, validate (jsonschema and built-in), render, CLI."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

from inkcheck import __version__
from inkcheck.card import (CardError, build_card, load_schema, render_markdown, saturation_block, validate,
                           validation_errors, write_card)
from inkcheck.cli import main

ROOT = Path(__file__).resolve().parents[1]
CHECK = {
    "verdict": "PASS", "summary": "known ink reproduced", "warnings": [],
    "numbers": {"r_bandpass": 0.41, "r_bandpass_p": 0.005, "r_bandpass_z": 9.1, "r_bandpass_null_mean": 0.01,
                "r_bandpass_null_sd": 0.04, "r_bandpass_null_max": 0.12, "n_shift_nulls": 192, "r_raw": 0.3,
                "auc_raw": 0.81, "breakeven_f1": 0.42, "stroke_recall": 0.71, "stroke_precision": 0.5,
                "n_ref_strokes": 40, "overlap_cm2": 3.2, "analysis_um": 19.2, "shift_um": [0.0, 19.2],
                "metric_nulls": {"stroke_recall": {"null_mean": 0.2}},
                "bootstrap": {"r_ci": [0.3, 0.5]}},
    "config": {"alpha_r": 0.01, "min_r_bp": 0.2, "min_stroke_recall": 0.5, "pred_um": 9.6, "ref_um": 19.2},
}
VALIDATORS = [False] + ([None] if __import__("importlib").util.find_spec("jsonschema") else [])


def card(**kw):
    base = dict(segment=dict(scroll="PHerc0139", segment_id="seg1"), model=dict(name="m"), scan=dict(pixel_um=2.4),
                controls=[dict(name="wrong_place", verdict="FAIL", r_bandpass=0.01)],
                saturation={"median": 40.0, "frac_high": 0.1, "tie_frac": 0.0, "threshold": 128, "saturated": False, "n": 10},
                prereg_sha256="a" * 64)
    base.update(kw)
    return build_card(copy.deepcopy(CHECK), **base)


def test_shipped_schema_matches_top_level_copy():
    assert load_schema() == json.loads((ROOT / "schemas" / "inkcheck-report-v1.json").read_text())


@pytest.mark.parametrize("js", VALIDATORS)
def test_valid_card(js):
    c = card()
    assert validation_errors(c, js) == []
    assert c["verdict"] == {"final": "PASS", "node_A": "PASS", "node_N": "NO_CONTROL_PASSES", "summary": "known ink reproduced"}
    assert c["metrics"]["stroke_recall_chance"] == 0.2 and c["metrics"]["r_bandpass_ci95"] == [0.3, 0.5]
    assert c["provenance"]["inkcheck_version"] == __version__
    assert c["saturation"]["checked"] is True and "tie_frac" not in c["saturation"]
    json.dumps(c, allow_nan=False)


@pytest.mark.parametrize("js", VALIDATORS)
def test_control_pass_makes_invalid(js):
    c = card(controls=[dict(name="wrong_place", verdict="PASS")])
    assert c["verdict"]["final"] == "INVALID" and c["verdict"]["node_N"] == "CONTROL_PASSED"
    validate(c, js)
    c["verdict"]["final"] = "PASS"
    with pytest.raises(CardError):
        validate(c, js)


@pytest.mark.parametrize("js", VALIDATORS)
@pytest.mark.parametrize("mutate", [
    lambda c: c.pop("provenance"),
    lambda c: c["verdict"].update(node_A="MAYBE"),
    lambda c: c["metrics"].update(auc_raw=1.5),
    lambda c: c["provenance"].update(prereg_sha256="xyz"),
    lambda c: c.update(schema_version="2.0"),
    lambda c: c.update(unexpected=1),
    lambda c: c["metrics"].pop("r_bandpass"),
    lambda c: c["saturation"].pop("checked"),
])
def test_invalid_cards(js, mutate):
    c = card()
    mutate(c)
    assert validation_errors(c, js)


def test_no_controls_and_unchecked_saturation():
    c = card(controls=None, saturation=None, prereg_sha256=None)
    validate(c, False)
    assert c["verdict"]["node_N"] is None and c["saturation"]["checked"] is False
    md = render_markdown(c)
    assert "No negative control" in md and "not checked" in md and "not pre-registered" in md


def test_saturated_adds_warning_and_render():
    c = card(saturation={"median": 200.0, "frac_high": 0.8, "threshold": 128, "saturated": True, "n": 10})
    assert any("saturated" in w for w in c["warnings"])
    md = render_markdown(c)
    assert md.startswith("# Ink card: PHerc0139 / seg1") and "**Verdict: PASS**" in md and "SATURATED" in md
    assert "| wrong_place | FAIL | FAIL |" in md


def test_saturation_block_from_arrays():
    a = np.full((50, 50), 200.0, np.float32)
    assert saturation_block(a)["saturated"] is True
    assert saturation_block(np.full((5, 5), 0.5, np.float32))["checked"] is False   # not 8-bit
    assert saturation_block(np.full((50, 50), 30.0))["saturated"] is False


def test_write_card(tmp_path):
    files = write_card(card(), tmp_path / "x")
    assert [Path(f).name for f in files] == ["x.card.json", "x.card.md"]
    bad = card()
    bad["verdict"]["node_A"] = "?"
    with pytest.raises(CardError):
        write_card(bad, tmp_path / "y")


def _synthetic(tmp_path):
    rng = np.random.default_rng(0)
    ref = np.zeros((300, 300), np.float32)
    for _ in range(40):
        y, x = rng.integers(10, 280, 2)
        ref[y:y + 6, x:x + rng.integers(15, 40)] = 200
    pred = np.clip(ref * 0.8 + rng.normal(60, 15, ref.shape), 1, 255).round().astype(np.float32)
    np.save(tmp_path / "pred.npy", pred)
    np.save(tmp_path / "ref.npy", ref)


def test_cli_emits_card_and_report_validate_render(tmp_path, capsys):
    _synthetic(tmp_path)
    pre = tmp_path / "prereg.md"
    pre.write_text("thresholds fixed in advance\n")
    out = tmp_path / "o" / "chk"
    rc = main([str(tmp_path / "pred.npy"), str(tmp_path / "ref.npy"), "--pred-um", "10", "--ref-um", "10",
               "--nulls", "16", "--metric-nulls", "4", "--min-shift-mm", "0.6", "--search-mm", "0.05", "--workers", "1",
               "--out", str(out), "--scroll", "PHercTEST", "--segment", "s1", "--model", "toy", "--prereg", str(pre)])
    assert rc in (0, 1, 2)
    c = json.loads(Path(str(out) + ".card.json").read_text())
    import hashlib
    assert c["provenance"]["prereg_sha256"] == hashlib.sha256(pre.read_bytes()).hexdigest()
    assert c["segment"]["scroll"] == "PHercTEST" and c["provenance"]["model"]["name"] == "toy"
    assert c["saturation"]["checked"] is True
    capsys.readouterr()
    assert main(["report", "--validate", str(out) + ".card.json"]) == 0
    assert capsys.readouterr().out.startswith("OK")
    assert main(["report", "--validate", str(out) + ".card.json", "--builtin-validator"]) == 0
    assert main(["report", "--render", str(out) + ".card.json"]) == 0
    assert "# Ink card: PHercTEST / s1" in capsys.readouterr().out
    c["verdict"]["final"] = "MAYBE"
    bad = tmp_path / "bad.card.json"
    bad.write_text(json.dumps(c))
    assert main(["report", "--validate", str(bad)]) == 1
    # convert the plain check JSON again, with a control
    assert main(["card", str(out) + ".json", "--out", str(tmp_path / "again"), "--control", str(out) + ".json",
                 "--segment", "s1"]) == 0
    c2 = json.loads((tmp_path / "again.card.json").read_text())
    assert c2["controls"][0]["expected"] == "FAIL"
    assert c2["verdict"]["final"] in ("INVALID", "WEAK", "FAIL")   # the 'control' is the check itself


def test_example_card_in_repo_is_valid():
    for p in (ROOT / "schemas" / "examples").glob("*.card.json"):
        validate(json.loads(p.read_text()), False)
