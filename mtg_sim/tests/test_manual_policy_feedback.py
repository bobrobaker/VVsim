"""Tests for manual-mode policy display, reason prompt, and JSONL logging."""
import json
from pathlib import Path

import pytest

from mtg_sim.sim.state import GameState
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.actions import Action, CostBundle, EffectBundle, CAST_SPELL, RISK_NORMAL
from mtg_sim.sim.runner import _manual_choose_action, _manual_session_save


# ── Helpers ──────────────────────────────────────────────────────────────────

def _cast(card_name, *, description=None):
    from mtg_sim.sim.mana import ManaCost
    return Action(
        action_type=CAST_SPELL,
        source_card=card_name,
        description=description or f"Cast {card_name}",
        costs=CostBundle(mana=ManaCost()),
        effects=EffectBundle(),
        risk_level=RISK_NORMAL,
    )


def _state(**kwargs):
    return GameState(**kwargs)


def _load_lib():
    from mtg_sim.sim.cards import load_card_library
    lib = Path(__file__).parent.parent.parent / "card_library.csv"
    load_card_library(str(lib))


# ── Display ───────────────────────────────────────────────────────────────────

def test_display_includes_score_and_rank_marker(monkeypatch, capsys):
    _load_lib()
    state = _state(floating_mana=ManaPool(U=1))
    inputs = iter(["q"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    _manual_choose_action(state, [_cast("Gitaxian Probe")], step=0)
    out = capsys.readouterr().out
    assert "★ BEST" in out
    assert "Gitaxian Probe" in out


def test_display_shows_delta_for_non_top(monkeypatch, capsys):
    _load_lib()
    state = _state(floating_mana=ManaPool(U=2))
    # Two actions; quit immediately
    inputs = iter(["q"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    _manual_choose_action(
        state,
        [_cast("Gitaxian Probe"), _cast("Rite of Flame")],
        step=0,
    )
    out = capsys.readouterr().out
    assert "Δ" in out  # delta marker present for rank-2 action


def test_display_no_reason_labels(monkeypatch, capsys):
    _load_lib()
    state = _state(floating_mana=ManaPool(U=1))
    monkeypatch.setattr("builtins.input", lambda _: "q")
    _manual_choose_action(state, [_cast("Gitaxian Probe")], step=0)
    out = capsys.readouterr().out
    assert "noncreature_base" not in out


def test_display_preserves_state_sections(monkeypatch, capsys):
    _load_lib()
    state = _state(
        floating_mana=ManaPool(U=1),
        graveyard=["Lightning Bolt"],
        exile=["Simian Spirit Guide"],
    )
    monkeypatch.setattr("builtins.input", lambda _: "q")
    _manual_choose_action(state, [_cast("Gitaxian Probe")], step=2)
    out = capsys.readouterr().out
    assert "Graveyard:" in out
    assert "Exile:" in out
    assert "Step 3" in out  # step is 1-based in display


# ── Top-action choice: no log, no reason prompt ───────────────────────────────

def test_top_action_no_log_written(monkeypatch, tmp_path, capsys):
    _load_lib()
    log_path = tmp_path / "adj.jsonl"
    state = _state(floating_mana=ManaPool(U=1))
    inputs = iter(["0"])  # pick rank-1 action
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    result = _manual_choose_action(
        state,
        [_cast("Gitaxian Probe")],
        step=0,
        adjustment_log_path=log_path,
        seed=42,
    )
    assert result is not None
    assert not log_path.exists()  # no log file created


def test_top_action_no_reason_prompt(monkeypatch, tmp_path, capsys):
    _load_lib()
    log_path = tmp_path / "adj.jsonl"
    state = _state(floating_mana=ManaPool(U=1))
    call_count = {"n": 0}

    def fake_input(prompt):
        call_count["n"] += 1
        return "0"

    monkeypatch.setattr("builtins.input", fake_input)
    _manual_choose_action(
        state,
        [_cast("Gitaxian Probe")],
        step=0,
        adjustment_log_path=log_path,
        seed=42,
    )
    assert call_count["n"] == 1  # only the action-number prompt, no reason prompt


# ── Non-top choice: reason prompted, JSONL appended ──────────────────────────

def test_non_top_choice_writes_jsonl(monkeypatch, tmp_path):
    _load_lib()
    log_path = tmp_path / "adj.jsonl"
    state = _state(floating_mana=ManaPool(U=2))

    # Action list: Gitaxian Probe (rank 1) and Rite of Flame (rank 2).
    # Display order is rank order; user picks index 1 (rank 2).
    inputs = iter(["1", "need mana first"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    result = _manual_choose_action(
        state,
        [_cast("Gitaxian Probe"), _cast("Rite of Flame")],
        step=3,
        adjustment_log_path=log_path,
        seed=99,
    )
    assert result is not None
    assert log_path.exists()
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])

    assert entry["seed"] == 99
    assert entry["step"] == 3
    assert entry["chosen_rank"] == 2
    assert entry["top_rank"] == 1
    assert entry["score_delta"] < 0
    assert entry["user_reason"] == "need mana first"
    assert len(entry["all_scored"]) == 2
    assert "state_snapshot" in entry
    snap = entry["state_snapshot"]
    assert "floating_mana" in snap
    assert "hand" in snap


def test_non_top_choice_appends_multiple_entries(monkeypatch, tmp_path):
    _load_lib()
    log_path = tmp_path / "adj.jsonl"
    state = _state(floating_mana=ManaPool(U=2))
    actions = [_cast("Gitaxian Probe"), _cast("Rite of Flame")]

    for _ in range(2):
        inputs = iter(["1", "testing"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        _manual_choose_action(state, actions, step=0, adjustment_log_path=log_path, seed=1)

    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2


def test_logs_dir_created_automatically(monkeypatch, tmp_path):
    _load_lib()
    nested = tmp_path / "deep" / "nested" / "adj.jsonl"
    state = _state(floating_mana=ManaPool(U=2))
    inputs = iter(["1", "reason"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    _manual_choose_action(
        state,
        [_cast("Gitaxian Probe"), _cast("Rite of Flame")],
        step=0,
        adjustment_log_path=nested,
        seed=1,
    )
    assert nested.exists()


# ── Quit ─────────────────────────────────────────────────────────────────────

def test_quit_returns_none_no_log(monkeypatch, tmp_path):
    _load_lib()
    log_path = tmp_path / "adj.jsonl"
    state = _state(floating_mana=ManaPool(U=1))
    monkeypatch.setattr("builtins.input", lambda _: "q")
    result = _manual_choose_action(
        state,
        [_cast("Gitaxian Probe")],
        step=0,
        adjustment_log_path=log_path,
        seed=1,
    )
    assert result is None
    assert not log_path.exists()


# ── No log_path: non-top choice skips file write silently ────────────────────

def test_non_top_no_log_path_skips_write(monkeypatch, tmp_path, capsys):
    _load_lib()
    state = _state(floating_mana=ManaPool(U=2))
    # With no log_path, reason prompt should NOT appear and no file is written.
    inputs = iter(["1"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    result = _manual_choose_action(
        state,
        [_cast("Gitaxian Probe"), _cast("Rite of Flame")],
        step=0,
        adjustment_log_path=None,
        seed=1,
    )
    assert result is not None
    # No files created in tmp_path
    assert list(tmp_path.iterdir()) == []


# ── Observation buffer ────────────────────────────────────────────────────────

def test_choice_appends_to_observation_buffer(monkeypatch):
    _load_lib()
    state = _state(floating_mana=ManaPool(U=1))
    inputs = iter(["0"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    buf = []
    _manual_choose_action(state, [_cast("Gitaxian Probe")], step=5,
                          observation_buffer=buf, seed=7)
    assert len(buf) == 1
    entry = buf[0]
    assert entry["entry_type"] == "manual_decision_snapshot"
    assert entry["step"] == 5
    assert entry["seed"] == 7
    assert entry["policy_trainable"] is True
    assert "state" in entry
    assert "library_ids" in entry["state"]
    assert "ranked_actions" in entry
    assert entry["chosen_was_policy_top"] is True


def test_note_command_appended_to_entry(monkeypatch):
    _load_lib()
    state = _state(floating_mana=ManaPool(U=1))
    inputs = iter(["n", "interesting state", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    buf = []
    _manual_choose_action(state, [_cast("Gitaxian Probe")], step=0,
                          observation_buffer=buf, seed=1)
    assert buf[0]["manual_notes"][0] == {"kind": "note", "text": "interesting state", "policy_trainable": True}
    assert buf[0]["policy_trainable"] is True


def test_missing_command_marks_non_trainable(monkeypatch):
    _load_lib()
    state = _state(floating_mana=ManaPool(U=1))
    inputs = iter(["m", "should have had tap land", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    buf = []
    _manual_choose_action(state, [_cast("Gitaxian Probe")], step=0,
                          observation_buffer=buf, seed=1)
    assert buf[0]["manual_notes"][0]["kind"] == "missing"
    assert buf[0]["policy_trainable"] is False


def test_illegal_command_marks_non_trainable(monkeypatch):
    _load_lib()
    state = _state(floating_mana=ManaPool(U=2))
    inputs = iter(["i", "1", "should not appear", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    buf = []
    _manual_choose_action(
        state,
        [_cast("Gitaxian Probe"), _cast("Rite of Flame")],
        step=0, observation_buffer=buf, seed=1,
    )
    note = buf[0]["manual_notes"][0]
    assert note["kind"] == "illegal"
    assert note["action_index"] == 1
    assert buf[0]["policy_trainable"] is False


def test_resolution_command_taints_state_and_future(monkeypatch):
    _load_lib()
    state = _state(floating_mana=ManaPool(U=1))
    taint = {"tainted": False}
    inputs = iter(["r", "state looks wrong", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    buf = []
    _manual_choose_action(state, [_cast("Gitaxian Probe")], step=0,
                          observation_buffer=buf, taint_state=taint, seed=1)
    assert buf[0]["manual_notes"][0]["kind"] == "resolution"
    assert buf[0]["policy_trainable"] is False
    assert taint["tainted"] is True


def test_taint_propagates_to_later_steps(monkeypatch):
    _load_lib()
    state = _state(floating_mana=ManaPool(U=1))
    taint = {"tainted": True}  # already tainted from prior step
    inputs = iter(["0"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    buf = []
    _manual_choose_action(state, [_cast("Gitaxian Probe")], step=1,
                          observation_buffer=buf, taint_state=taint,
                          policy_trainable=False, seed=1)
    assert buf[0]["policy_trainable"] is False


# ── Session save ──────────────────────────────────────────────────────────────

def test_session_save_writes_jsonl(monkeypatch, tmp_path):
    log_path = tmp_path / "obs.jsonl"
    buf = [
        {"entry_type": "manual_decision_snapshot", "step": 0, "policy_trainable": True, "manual_notes": []},
        {"entry_type": "manual_decision_snapshot", "step": 1, "policy_trainable": True, "manual_notes": []},
    ]
    monkeypatch.setattr("builtins.input", lambda _: "y")
    _manual_session_save(buf, log_path)
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2


def test_session_save_discard_no_file(monkeypatch, tmp_path):
    log_path = tmp_path / "obs.jsonl"
    buf = [{"entry_type": "manual_decision_snapshot", "step": 0, "policy_trainable": True, "manual_notes": []}]
    monkeypatch.setattr("builtins.input", lambda _: "n")
    _manual_session_save(buf, log_path)
    assert not log_path.exists()


def test_session_save_no_path_no_file(monkeypatch, tmp_path, capsys):
    buf = [{"entry_type": "manual_decision_snapshot", "step": 0, "policy_trainable": True, "manual_notes": []}]
    _manual_session_save(buf, None)
    assert list(tmp_path.iterdir()) == []


def test_session_save_summary_counts(monkeypatch, tmp_path, capsys):
    log_path = tmp_path / "obs.jsonl"
    buf = [
        {"entry_type": "manual_decision_snapshot", "step": 0, "policy_trainable": True,
         "manual_notes": [{"kind": "note", "text": "x", "policy_trainable": True}]},
        {"entry_type": "manual_decision_snapshot", "step": 1, "policy_trainable": False,
         "manual_notes": [{"kind": "missing", "text": "y", "policy_trainable": False}]},
    ]
    monkeypatch.setattr("builtins.input", lambda _: "n")
    _manual_session_save(buf, log_path)
    out = capsys.readouterr().out
    assert "2 decisions" in out
    assert "2 notes" in out
    assert "1 bug-note" in out
    assert "1/2 policy-trainable" in out
