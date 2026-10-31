"""Known training overlap (jo-tud, villa PR #2349): in-sample flags on cards and the leaderboard, scores untouched."""
import copy
import json

import pytest

from inkcheck.card import build_card, render_markdown, validation_errors
from inkcheck.cli import main
from inkcheck.training_overlap import is_in_sample, load_registry, lookup, norm_scroll, segment_ids

from test_card import CHECK, VALIDATORS

W030 = "20250108000005-w030_2025010818"
W045 = "20260126000000-w045_2026012619"
INK9 = ["ink_9um seed42", "ink_9um s43", "ink_9um seed43 75k", "Nieuwlaar/ink9um-dense-native", "dense_native 16k"]
ONLY_INK9 = ["ink_9um seed42", "ink_9um s43", "ink_9um seed43 75k"]
DENSE = ["Nieuwlaar/ink9um-dense-native", "dense_native 16k"]
V8IN = ["YoussefMoNader/ink-8um-v8in", "v8-in"]
# jo-tud's table (villa PR #2349): public w-number -> (public segment id, ink_9um label case name)
P0139 = {"w029": ("20250108000004", "pherc0139-w016"), "w030": ("20250108000005", "pherc0139-w017"),
         "w033": ("20260219000000", None), "w035": ("20260317000000", "pherc0139-w035"),
         "w039": ("20260302000000", "pherc0139-w039"), "w040": ("20250831000000", "pherc0139-w040"),
         "w041": ("20260108000000", "pherc0139-w041"), "w043": ("20260112000000", "pherc0139-w043"),
         "w044": ("20260115000000", "pherc0139-w028"), "w045": ("20260126000000", "pherc0139-w029")}
NINE = ["w029", "w030", "w035", "w039", "w040", "w041", "w043", "w044", "w045"]
# T / H / ? per jo-tud's table
TABLE = {
    "ink9": dict(w029=True, w030=True, w033=None, w035=True, w039=True, w040=True, w041=True, w043=True, w044=True,
                 w045=True),
    "dense": dict(w029=True, w030=True, w033=True, w035=True, w039=True, w040=True, w041=True, w043=True, w044=True,
                  w045=True),
    "v8in": dict(w029=False, w030=False, w033=True, w035=True, w039=False, w040=False, w041=True, w043=False,
                 w044=True, w045=False),
}
CASES = [(fam, m, w) for fam, ms in (("ink9", ONLY_INK9), ("dense", DENSE), ("v8in", V8IN)) for m in ms for w in P0139]


def _folder(w):
    return f"{P0139[w][0]}-{w}_x"


@pytest.mark.parametrize("fam,model,w", CASES)
def test_table_by_public_segment_id_folder_and_label_case(fam, model, w):
    want = TABLE[fam][w]
    sid, case = P0139[w]
    assert is_in_sample(model, "PHerc0139", _folder(w)) is want
    assert is_in_sample(model, "PHerc0139", sid) is want
    if case:
        assert is_in_sample(model, "PHerc0139", case) is want
        assert is_in_sample(model, None, "x", label=case) is want            # scroll from the case name


@pytest.mark.parametrize("model", INK9)
@pytest.mark.parametrize("seg", [W030, W045, "20250108000005", "pherc0139-w017", "pherc0139-w029"])
def test_ink9um_family_in_sample_on_w030_w045(model, seg):
    assert is_in_sample(model, "PHerc0139", seg) is True


@pytest.mark.parametrize("model", INK9 + V8IN)
def test_0343P_held_out_for_all_and_other_segments_unknown(model):
    assert is_in_sample(model, "PHerc0343P", "20250511003658") is False
    assert is_in_sample(model, "PHerc0343", "20250509220833") is None                   # rolled 343 != fragment 343P
    assert is_in_sample(model, "PHerc0139", "w017") is None    # a public w017 is not label case pherc0139-w017
    assert is_in_sample(model, "PHerc0139", "20250101000000-w001_x") is None              # not listed: unknown


def test_label_and_public_w_numbers_are_not_confused():
    # the three renamed label cases: pherc0139-w016 = public w029, pherc0139-w029 = public w045,
    # pherc0139-w028 = public w044. v8-in trains on public w044 but not on public w029/w045.
    m = "v8-in"
    assert is_in_sample(m, "PHerc0139", "pherc0139-w029") is False        # public w045 (held out), not public w029
    assert is_in_sample(m, "PHerc0139", "pherc0139-w028") is True         # public w044
    assert is_in_sample(m, "PHerc0139", "pherc0139-w044") is None         # no label case w044 (public w044 = w028)
    assert is_in_sample(m, "PHerc0139", "pherc0139-w033") is None         # public w033 has no label case
    assert is_in_sample(m, "PHerc0139", "20250108000004-w029_2025010827", label="pherc0139-w016") is False


def test_ink9um_w029_note_and_no_held_out_0139():
    r = lookup("ink_9um seed42", "PHerc0139", "20250108000004-w029_2025010827")
    assert r["status"] is True and "online-validation" in r["note"]
    r = lookup("ink_9um seed42", "PHerc0139", W030)
    assert "no held-out labelled 0139 segment" in r["note"] and "0343P" in r["note"]
    assert lookup("ink_9um seed42", "PHerc0139", _folder("w033"))["status"] is None     # "?" in the table


def test_confidence():
    assert "zattrs" in lookup("ink_9um seed42", "PHerc0139", W030)["confidence"]
    for w in ("w033", "w035", "w041", "w044"):
        r = lookup("v8-in", "PHerc0139", _folder(w))
        assert r["status"] is True and "canvas-size" in r["confidence"] and "unconfirmed" not in (r["matched"] or "")
    assert lookup("other", "PHerc0139", W030)["confidence"] is None


@pytest.mark.parametrize("model", DENSE)
def test_dense_native_config_entries(model):
    for w in ("w032", "w034", "w046", "w049", "w050"):    # config-listed, read as public numbers, mapping unverified
        r = lookup(model, "PHerc0139", f"20990101000000-{w}_x")
        assert r["status"] is True and r["confidence"] == "per config, unverified mapping"
        assert is_in_sample(model, "PHerc0139", f"pherc0139-{w}") is None            # public numbers only
    for m in ONLY_INK9 + V8IN:
        assert is_in_sample(m, "PHerc0139", "20990101000000-w046_x") is None


def test_unknown_model_and_source():
    for m in (None, "", "reader-v3", "new_canon_autoresearch_recipe", "dense9um all7"):
        assert is_in_sample(m, "PHerc0139", W030) is None
    r = lookup("ink_9um seed42", "PHerc0139", W030)
    assert r["flag"] == "in-sample (training overlap)" and "villa/pull/2349" in r["source"]
    assert r["matched"] == "20250108000005"


def test_helpers():
    assert norm_scroll("PHerc0139") == norm_scroll("pherc0139") == norm_scroll("PHerc. 139") == "139"
    assert norm_scroll("PHerc0343P") == "343p" != norm_scroll("PHerc0343")
    ids = segment_ids(W030, "PHerc0139")
    assert ids["segment_id"] == "20250108000005" and ids["public_w"] == "w030" and ids["label_case"] is None


def test_user_registry(tmp_path):
    f = tmp_path / "overlap.json"
    f.write_text(json.dumps([{"model": "my-model", "in_sample": [{"scroll": "PHerc1667", "public_w": "w013"}],
                              "held_out": [{"scroll": "PHerc0139", "segment_id": "*"}]}]))
    reg = load_registry(f)
    assert is_in_sample("my-model", "PHerc1667", "20240304141531-w013_x", registry=reg) is True
    assert is_in_sample("my-model", "PHerc0139", W030, registry=reg) is False
    assert is_in_sample("ink_9um seed42", "PHerc0139", W030, registry=reg) is True   # built-ins still there
    assert is_in_sample("ink_9um seed42", "PHerc0139", W030, registry=load_registry(f, include_builtin=False)) is None


@pytest.mark.parametrize("js", VALIDATORS)
def test_card_flag_does_not_change_scores(js):
    kw = dict(segment=dict(scroll="PHerc0139", segment_id=W030), model=dict(name="ink_9um seed42"))
    plain = build_card(copy.deepcopy(CHECK), **kw)
    flagged = build_card(copy.deepcopy(CHECK), training_overlap=lookup("ink_9um seed42", "PHerc0139", W030), **kw)
    assert validation_errors(flagged, js) == []
    assert flagged["verdict"] == plain["verdict"] and flagged["metrics"] == plain["metrics"]
    assert flagged["provenance"]["training_overlap"]["status"] is True
    assert any(w.startswith("in-sample (training overlap)") for w in flagged["warnings"])
    assert "in-sample (training overlap)" in render_markdown(flagged)
    unknown = build_card(copy.deepcopy(CHECK), training_overlap=lookup("other", "PHerc0139", W030), **kw)
    assert unknown["warnings"] == plain["warnings"] and validation_errors(unknown, js) == []
    assert "training overlap | unknown" in render_markdown(unknown)


def test_card_cli_flags_in_sample(tmp_path):
    chk = tmp_path / "c.json"
    chk.write_text(json.dumps(CHECK))
    rc = main(["card", str(chk), "--scroll", "PHerc0139", "--segment", W045, "--model", "dense_native 16k"])
    assert rc == 0
    c = json.loads((tmp_path / "c.card.json").read_text())
    assert c["provenance"]["training_overlap"]["status"] is True and c["verdict"]["final"] == "PASS"
    rc = main(["card", str(chk), "--scroll", "PHerc0139", "--segment", W045, "--model", "v8-in", "--out", str(tmp_path / "v")])
    c = json.loads((tmp_path / "v.card.json").read_text())
    assert rc == 0 and c["provenance"]["training_overlap"]["status"] is False
    assert not any("in-sample" in w for w in c["warnings"])
