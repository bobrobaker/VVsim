"""Tests for manual-mode display output in _manual_choose_action."""
from mtg_sim.sim.state import GameState
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import _manual_choose_action
from mtg_sim.sim.actions import Action, STOP


def _dummy_action():
    return Action(
        action_type=STOP,
        source_card=None,
        description="Stop",
    )


def test_exile_shown_when_nonempty(monkeypatch, capsys):
    state = GameState(exile=["Simian Spirit Guide"])
    monkeypatch.setattr("builtins.input", lambda _: "q")
    result = _manual_choose_action(state, [_dummy_action()], step=0)
    assert result is None
    out = capsys.readouterr().out
    assert "Exile:" in out
    assert "Simian Spirit Guide" in out


def test_exile_hidden_when_empty(monkeypatch, capsys):
    state = GameState(exile=[])
    monkeypatch.setattr("builtins.input", lambda _: "q")
    _manual_choose_action(state, [_dummy_action()], step=0)
    out = capsys.readouterr().out
    assert "Exile:" not in out


def test_graveyard_and_exile_both_shown(monkeypatch, capsys):
    state = GameState(
        graveyard=["Lightning Bolt"],
        exile=["Jeska's Will"],
    )
    monkeypatch.setattr("builtins.input", lambda _: "q")
    _manual_choose_action(state, [_dummy_action()], step=0)
    out = capsys.readouterr().out
    assert "Graveyard:" in out
    assert "Lightning Bolt" in out
    assert "Exile:" in out
    assert "Jeska's Will" in out
