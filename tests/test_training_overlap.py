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


@pytest.mark.parametrize("model", INK9)
@pytest.mark.parametrize("seg", [W030, W045, "20250108000005", "pherc0139-w017", "pherc0139-w029"])
def test_ink9um_family_in_sample_on_w030_w045(model, seg):
    assert is_in_sample(model, "PHerc0139", seg) is True


@pytest.mark.parametrize("model", INK9)
def test_ink9um_family_0343P_held_out_and_other_segments_unknown(model):
    assert is_in_sample(model, "PHerc0343P", "20250511003658") is False
    assert is_in_sample(model, "PHerc0139", "20260115000000-w044_2026011522") is None   # not listed: unknown
    assert is_in_sample(model, "PHerc0343", "20250509220833") is None                   # rolled 343 != fragment 343P
    assert is_in_sample(model, "PHerc0139", "w017") is None    # a public w017 is not label case pherc0139-w017


def test_label_and_public_w_numbers_are_not_confused():
    # label case pherc0139-w029 is public w045, not public w029
    assert is_in_sample("ink_9um seed42", "PHerc0139", "20250108000004-w029_2025010827") is None
    assert is_in_sample("ink_9um seed42", "PHerc0139", "20250108000004-w029_2025010827", label="pherc0139-w016") is None
    assert is_in_sample("ink_9um seed42", None, "x", label="pherc0139-w029") is True     # scroll from the case name


def test_v8in():
    for m in ("YoussefMoNader/ink-8um-v8in", "v8-in"):
        assert is_in_sample(m, "PHerc0139", W030) is False and is_in_sample(m, "PHerc0139", W045) is False
        assert is_in_sample(m, "PHerc0139", "pherc0139-w017") is False
        assert is_in_sample(m, "PHerc0343P", "anything") is False
        for w in ("w033", "w035", "w041", "w044"):        # naming unconfirmed: matched in both namings
            r = lookup(m, "PHerc0139", f"20260317000000-{w}_x")
            assert r["status"] is True and "unconfirmed" in r["matched"]
            assert is_in_sample(m, "PHerc0139", f"pherc0139-{w}") is True


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
