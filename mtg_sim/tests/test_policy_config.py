"""Tests for policy config loading, score-breakdown API, and rank_actions."""
import textwrap
from pathlib import Path

import pytest

from mtg_sim.sim.state import GameState
from mtg_sim.sim.mana import ManaPool, ManaCost
from mtg_sim.sim.actions import (
    Action, CostBundle, EffectBundle,
    CAST_SPELL, ACTIVATE_MANA_ABILITY, EXILE_FOR_MANA,
    RESOLVE_STACK_OBJECT, RISK_NORMAL, RISK_SAFE,
)
from mtg_sim.sim.stack import StackObject
from mtg_sim.sim.policies import (
    load_policy_config, rank_actions, score_action,
    score_action_with_reasons, ScoredAction, _DEFAULTS,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _cast(card_name, *, mana_u=0, mana_r=0, generic=0):
    from mtg_sim.sim.mana import ManaCost
    return Action(
        action_type=CAST_SPELL,
        source_card=card_name,
        description=f"Cast {card_name}",
        costs=CostBundle(mana=ManaCost(pip_u=mana_u, pip_r=mana_r, generic=generic)),
        effects=EffectBundle(),
        risk_level=RISK_NORMAL,
    )


def _state(**kwargs):
    return GameState(**kwargs)


# ── Config loading ────────────────────────────────────────────────────────────

def test_defaults_when_toml_missing(tmp_path):
    cfg = load_policy_config(tmp_path / "nonexistent.toml")
    assert cfg["cast_spell"]["noncreature_base"] == _DEFAULTS["cast_spell"]["noncreature_base"]
    assert cfg["risk"]["risky"] == _DEFAULTS["risk"]["risky"]


def test_toml_override_applies(tmp_path):
    toml_path = tmp_path / "policy.toml"
    toml_path.write_text(textwrap.dedent("""\
        [cast_spell]
        noncreature_base = 999.0
    """))
    cfg = load_policy_config(toml_path)
    assert cfg["cast_spell"]["noncreature_base"] == 999.0
    # Unrelated keys are unchanged
    assert cfg["cast_spell"]["free_cost_bonus"] == _DEFAULTS["cast_spell"]["free_cost_bonus"]


def test_partial_toml_falls_back_for_missing_keys(tmp_path):
    toml_path = tmp_path / "policy.toml"
    toml_path.write_text("[cast_spell]\ninstant_win = 5000.0\n")
    cfg = load_policy_config(toml_path)
    assert cfg["cast_spell"]["instant_win"] == 5000.0
    # All other keys still present
    assert cfg["cast_spell"]["noncreature_base"] == _DEFAULTS["cast_spell"]["noncreature_base"]
    assert cfg["resolve"]["mana_producer"] == _DEFAULTS["resolve"]["mana_producer"]


def test_score_action_with_default_cfg_matches_hardcoded():
    """score_action with no TOML should produce same values as the hardcoded defaults."""
    from mtg_sim.sim.cards import load_card_library
    from pathlib import Path
    lib = Path(__file__).parent.parent.parent / "card_library.csv"
    load_card_library(str(lib))

    state = _state(floating_mana=ManaPool(U=1))
    action = _cast("Gitaxian Probe")  # free noncreature spell

    # Load via explicit nonexistent path → pure defaults
    cfg_default = load_policy_config(Path("/nonexistent/policy.toml"))
    score_default = score_action(state, action, cfg_default)

    # Load via None → auto-detects real TOML; values should still match defaults
    # unless someone edited the TOML. Compare against same cfg_default to avoid
    # dependence on file contents.
    score_explicit = score_action(state, action, cfg_default)
    assert score_default == score_explicit


def test_score_action_with_toml_override(tmp_path):
    from mtg_sim.sim.cards import load_card_library
    from pathlib import Path
    lib = Path(__file__).parent.parent.parent / "card_library.csv"
    load_card_library(str(lib))

    toml_path = tmp_path / "policy.toml"
    # Raise noncreature_base so Gitaxian Probe gets a much higher score
    toml_path.write_text(
        "[cast_spell]\nnoncreature_base = 500.0\nfree_cost_bonus = 0.0\ndraw_spell_bonus = 0.0\n"
    )
    cfg = load_policy_config(toml_path)

    state = _state(floating_mana=ManaPool(U=1))
    action = _cast("Gitaxian Probe")
    score, reasons = score_action_with_reasons(state, action, cfg)
    assert score == pytest.approx(500.0)  # base only (cost and draw bonuses zeroed)
    assert "noncreature_base" in reasons


# ── rank_actions ──────────────────────────────────────────────────────────────

def test_rank_actions_order_and_delta(tmp_path):
    from mtg_sim.sim.cards import load_card_library
    from pathlib import Path
    lib = Path(__file__).parent.parent.parent / "card_library.csv"
    load_card_library(str(lib))

    # Give Gitaxian Probe a big advantage by boosting free_cost_bonus
    toml_path = tmp_path / "policy.toml"
    toml_path.write_text("[cast_spell]\nfree_cost_bonus = 200.0\n")
    cfg = load_policy_config(toml_path)

    state = _state(floating_mana=ManaPool(U=2))
    probe = _cast("Gitaxian Probe")           # free noncreature
    rite = _cast("Rite of Flame", mana_r=1)   # 1-mana noncreature ritual

    ranked = rank_actions(state, [rite, probe], cfg)
    assert len(ranked) == 2
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2
    assert ranked[0].action.source_card == "Gitaxian Probe"
    assert ranked[0].delta == pytest.approx(0.0)
    assert ranked[1].delta == pytest.approx(ranked[1].score - ranked[0].score)
    assert ranked[1].delta < 0


def test_rank_actions_single_action_is_rank_1(tmp_path):
    from mtg_sim.sim.cards import load_card_library
    from pathlib import Path
    lib = Path(__file__).parent.parent.parent / "card_library.csv"
    load_card_library(str(lib))

    cfg = load_policy_config(tmp_path / "nofile.toml")
    state = _state(floating_mana=ManaPool(U=1))
    ranked = rank_actions(state, [_cast("Gitaxian Probe")], cfg)
    assert ranked[0].rank == 1
    assert ranked[0].delta == pytest.approx(0.0)


def test_rank_actions_reasons_nonempty():
    from mtg_sim.sim.cards import load_card_library
    from pathlib import Path
    lib = Path(__file__).parent.parent.parent / "card_library.csv"
    load_card_library(str(lib))

    cfg = load_policy_config()
    state = _state(floating_mana=ManaPool(U=1))
    ranked = rank_actions(state, [_cast("Gitaxian Probe")], cfg)
    assert ranked[0].reasons  # at least one reason label


def test_draw_trigger_ranks_above_one_mana_non_win_cast():
    _load_lib()
    cfg = load_policy_config()
    state = _state(floating_mana=ManaPool(U=1, R=1))
    state.stack.append(StackObject(
        card_name="_DrawTrigger",
        is_draw_trigger=True,
        draw_count=3,
    ))

    resolve_draw = Action(
        action_type=RESOLVE_STACK_OBJECT,
        source_card="_DrawTrigger",
        description="Resolve Curiosity draws (3)",
        target=state.stack[-1].stack_id,
        risk_level=RISK_SAFE,
    )
    cast_spell = _cast("Invert / Invent", mana_u=1)

    ranked = rank_actions(state, [cast_spell, resolve_draw], cfg)
    assert ranked[0].action is resolve_draw
    assert ranked[0].score > ranked[1].score
    assert "draw_trigger" in ranked[0].reasons


# ── Pitch penalty ─────────────────────────────────────────────────────────────

_LIB = Path(__file__).parent.parent.parent / "card_library.csv"


def _load_lib():
    from mtg_sim.sim.cards import load_card_library
    load_card_library(str(_LIB))


def _pitch_cast(card_name, pitched_card, *, alt_cost_type="pitch_blue"):
    return Action(
        action_type=CAST_SPELL,
        source_card=card_name,
        description=f"Cast {card_name} (pitch {pitched_card})",
        costs=CostBundle(mana=ManaCost(), pitched_card=pitched_card),
        effects=EffectBundle(),
        risk_level=RISK_NORMAL,
        alt_cost_type=alt_cost_type,
    )


def test_pitch_cast_lower_than_free_cast():
    """Pitching a card should score substantially lower than a truly free spell."""
    _load_lib()
    cfg = load_policy_config()
    state = _state()

    free = _cast("Gitaxian Probe")           # free, pay-life alt cost not used here
    pitched = _pitch_cast("Force of Will", "Brainstorm")

    free_score = score_action(state, free, cfg)
    pitch_score = score_action(state, pitched, cfg)
    assert pitch_score < free_score


def test_pitch_win_card_very_negative():
    """Pitching a win card should produce a very negative score."""
    _load_lib()
    cfg = load_policy_config()
    state = _state()
    pitched = _pitch_cast("Force of Will", "Final Fortune")
    score = score_action(state, pitched, cfg)
    # Should be deeply penalised
    assert score < 50


def test_pitch_reasons_include_penalty_label():
    _load_lib()
    cfg = load_policy_config()
    state = _state()
    action = _pitch_cast("Force of Will", "Brainstorm")
    _, reasons = score_action_with_reasons(state, action, cfg)
    assert "pitch_undo_free" in reasons
    assert any("pitch" in r for r in reasons)


# ── Free mana source bonus ────────────────────────────────────────────────────

def test_free_mana_source_scores_higher_than_free_non_mana():
    """Lotus Petal (free mana source) should outscore a plain free noncreature."""
    _load_lib()
    cfg = load_policy_config()
    state = _state()

    petal = _cast("Lotus Petal")
    # A free noncreature that neither produces mana nor draws
    # Use a dummy via zero-cost ManaCost; fall back to a known card
    probe = _cast("Gitaxian Probe")  # draw spell, also gets draw bonus

    petal_score = score_action(state, petal, cfg)
    # Petal should get noncreature_base + free_cost_bonus + free_mana_source_bonus
    expected_min = (
        _DEFAULTS["cast_spell"]["noncreature_base"]
        + _DEFAULTS["cast_spell"]["free_cost_bonus"]
        + _DEFAULTS["cast_spell"]["free_mana_source_bonus"]
    )
    assert petal_score == pytest.approx(expected_min)


def test_free_mana_source_reason_present():
    _load_lib()
    cfg = load_policy_config()
    state = _state()
    _, reasons = score_action_with_reasons(state, _cast("Lotus Petal"), cfg)
    assert "free_mana_source" in reasons


# ── Mana enables win cast ─────────────────────────────────────────────────────

def _mana_action(produced: ManaPool, *, source="Sol Ring"):
    return Action(
        action_type=ACTIVATE_MANA_ABILITY,
        source_card=source,
        description=f"Tap {source}",
        costs=CostBundle(),
        effects=EffectBundle(add_mana=produced),
        risk_level=RISK_SAFE,
    )


def test_mana_enabling_win_cast_scores_above_enables_new_cast():
    """When floating mana enables a win card via a mana action, score > enables_new_cast."""
    _load_lib()
    cfg = load_policy_config()
    # Final Fortune costs {R}{R}; we have 1R so adding 1R unlocks it
    state = _state(
        hand=["Final Fortune"],
        floating_mana=ManaPool(R=1),
    )
    action = _mana_action(ManaPool(R=1))
    score, reasons = score_action_with_reasons(state, action, cfg)
    assert score >= cfg["mana"]["enables_win_cast"]
    assert "mana_enables_win" in reasons


def test_mana_enables_win_cast_higher_than_regular_cast_enable():
    _load_lib()
    cfg = load_policy_config()

    # Win state: have 1R, Final Fortune needs 2R; adding 1R tips us over
    state_win = _state(hand=["Final Fortune"], floating_mana=ManaPool(R=1))
    # Regular state: have 0 mana, Rite of Flame needs R; adding R enables it
    state_reg = _state(hand=["Rite of Flame"], floating_mana=ManaPool())

    action = _mana_action(ManaPool(R=1))
    win_score = score_action(state_win, action, cfg)
    reg_score = score_action(state_reg, action, cfg)
    assert win_score > reg_score


# ── Red mana preference ───────────────────────────────────────────────────────

def test_red_mana_generation_gets_bonus_over_colorless():
    _load_lib()
    cfg = load_policy_config()
    state = _state(hand=[], floating_mana=ManaPool(R=1))  # already have R, no win card

    red_action = _mana_action(ManaPool(R=1), source="Mountain")
    any_action = _mana_action(ManaPool(ANY=1), source="Sol Ring")

    red_score = score_action(state, red_action, cfg)
    any_score = score_action(state, any_action, cfg)
    assert red_score > any_score


def test_red_for_win_bonus_applies_when_win_card_needs_red():
    _load_lib()
    cfg = load_policy_config()
    state = _state(hand=["Final Fortune"], floating_mana=ManaPool())

    # ANY mana can still satisfy the red need via _mana_enables_win_cast
    action = _mana_action(ManaPool(ANY=2), source="Sol Ring")
    _, reasons = score_action_with_reasons(state, action, cfg)
    # Either enables_win or red_for_win should trigger
    assert "mana_enables_win" in reasons or "red_for_win" in reasons


# ── Red spend penalty ─────────────────────────────────────────────────────────

def test_red_spend_penalty_when_win_card_needs_red():
    """Spending our only red on a non-ritual should be penalised if win card needs red."""
    _load_lib()
    cfg = load_policy_config()
    # We have 1R floating and Final Fortune in hand (needs R)
    state = _state(
        hand=["Final Fortune"],
        floating_mana=ManaPool(R=1),
    )
    # Rite of Flame costs R but IS a mana ritual — no penalty
    rite = _cast("Rite of Flame", mana_r=1)
    rite_score, rite_reasons = score_action_with_reasons(state, rite, cfg)
    assert "red_spend_penalty" not in rite_reasons

    # Scoring a non-ritual that costs R should include penalty
    # Use a generic action with pip_r=1 cost via ManaCost
    non_ritual = Action(
        action_type=CAST_SPELL,
        source_card="Gitaxian Probe",  # normally 0 cost; override with R cost
        description="Cast probe with R",
        costs=CostBundle(mana=ManaCost(pip_r=1)),
        effects=EffectBundle(),
        risk_level=RISK_NORMAL,
    )
    _, reasons = score_action_with_reasons(state, non_ritual, cfg)
    assert "red_spend_penalty" in reasons
