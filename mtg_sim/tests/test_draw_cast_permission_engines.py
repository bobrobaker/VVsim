import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent

from mtg_sim.sim.cards import load_card_library, build_active_deck
from mtg_sim.sim.mana import ManaPool
from mtg_sim.sim.runner import RunConfig, _build_initial_state
from mtg_sim.sim.resolver import resolve_action, draw_cards
from mtg_sim.sim.action_generator import generate_actions
from mtg_sim.sim.actions import (
    Action, CostBundle, ManaCost,
    CAST_SPELL, RESOLVE_STACK_OBJECT,
    RISK_SAFE, RISK_NORMAL,
)
from random import Random


def _load():
    load_card_library(str(DATA_DIR / "card_library.csv"))
    return build_active_deck()


def _state(hand, mana=None, library=None):
    cards = _load()
    cfg = RunConfig(seed=1, starting_hand=hand, starting_floating_mana=mana or ManaPool())
    rng = Random(1)
    state = _build_initial_state(cfg, cards, rng)
    if library is not None:
        state.library = library[:]
    return state


def _cast(state, card_name, alt_cost_type=None, mana=None, target=None):
    """Helper: cast card from hand and return state."""
    from mtg_sim.sim.cards import get_card
    cd = get_card(card_name)
    cost = ManaCost(pip_u=cd.pip_u, pip_r=cd.pip_r, generic=cd.generic_mana) if mana is None else mana
    action = Action(
        action_type=CAST_SPELL,
        source_card=card_name,
        description=f"Cast {card_name}",
        costs=CostBundle(mana=cost),
        risk_level=RISK_NORMAL,
        alt_cost_type=alt_cost_type,
        target=target,
    )
    resolve_action(state, action)
    return state


def _resolve_top(state):
    act = next(a for a in generate_actions(state) if a.action_type == RESOLVE_STACK_OBJECT)
    resolve_action(state, act)


def _drain_stack(state):
    """Resolve all stack objects until empty."""
    while state.stack:
        _resolve_top(state)


# ── Bucket-level: noncreature casts increment Curiosity draws ─────────────────

def test_noncreature_cast_creates_draw_trigger():
    state = _state(["Gitaxian Probe"], ManaPool(U=1))
    _cast(state, "Gitaxian Probe", alt_cost_type="pay_life", mana=ManaCost())
    assert state.stack[-1].is_draw_trigger
    assert state.stack[-1].draw_count == 3  # default: 1 Curiosity × 3 opponents


def test_creature_cast_does_not_create_draw_trigger():
    # Tandem Lookout is a creature; casting it must not add a draw trigger
    state = _state(["Tandem Lookout"], ManaPool(U=2, R=1))
    _cast(state, "Tandem Lookout")
    draw_triggers = [o for o in state.stack if o.is_draw_trigger]
    assert len(draw_triggers) == 0


# ── Curiosity ─────────────────────────────────────────────────────────────────

def test_curiosity_increments_draw_count():
    state = _state(["Curiosity"], ManaPool(U=1))
    assert state.curiosity_effect_count == 1
    _cast(state, "Curiosity")
    _drain_stack(state)
    assert state.curiosity_effect_count == 2
    assert state.cards_drawn_per_noncreature_spell == 6  # 2 effects × 3 opponents


def test_curiosity_requires_vivi():
    state = _state(["Curiosity"], ManaPool(U=1))
    state.vivi_on_battlefield = False
    count_before = state.curiosity_effect_count
    _cast(state, "Curiosity")
    _drain_stack(state)
    assert state.curiosity_effect_count == count_before  # no change without Vivi


# ── Ophidian Eye ──────────────────────────────────────────────────────────────

def test_ophidian_eye_increments_draw_count():
    state = _state(["Ophidian Eye"], ManaPool(U=3))
    _cast(state, "Ophidian Eye")
    _drain_stack(state)
    assert state.curiosity_effect_count == 2
    assert state.cards_drawn_per_noncreature_spell == 6


def test_ophidian_eye_generated_at_instant_speed():
    state = _state(["Ophidian Eye", "Gitaxian Probe"], ManaPool(U=4))
    # Put something on the stack first
    _cast(state, "Gitaxian Probe", alt_cost_type="pay_life", mana=ManaCost())
    assert state.stack  # probe is on stack
    actions = generate_actions(state)
    names = [a.source_card for a in actions if a.action_type == CAST_SPELL]
    assert "Ophidian Eye" in names


# ── Tandem Lookout ────────────────────────────────────────────────────────────

def test_tandem_lookout_increments_draw_count_with_vivi():
    state = _state(["Tandem Lookout"], ManaPool(U=2, R=1))
    assert state.vivi_on_battlefield
    _cast(state, "Tandem Lookout")
    _drain_stack(state)
    assert state.curiosity_effect_count == 2


def test_tandem_lookout_no_increment_without_vivi():
    state = _state(["Tandem Lookout"], ManaPool(U=2, R=1))
    state.vivi_on_battlefield = False
    _cast(state, "Tandem Lookout")
    _drain_stack(state)
    assert state.curiosity_effect_count == 1  # unchanged


# ── Niv-Mizzet, Visionary ─────────────────────────────────────────────────────

def test_niv_mizzet_increments_draw_count():
    state = _state(["Niv-Mizzet, Visionary"], ManaPool(U=2, R=2, C=2))
    _cast(state, "Niv-Mizzet, Visionary")
    _drain_stack(state)
    assert state.curiosity_effect_count == 2
    assert state.cards_drawn_per_noncreature_spell == 6


def test_niv_mizzet_on_battlefield():
    state = _state(["Niv-Mizzet, Visionary"], ManaPool(U=2, R=2, C=2))
    _cast(state, "Niv-Mizzet, Visionary")
    _drain_stack(state)
    names = [p.card_name for p in state.battlefield]
    assert "Niv-Mizzet, Visionary" in names


def test_multiple_draw_engines_stack():
    state = _state(["Curiosity", "Niv-Mizzet, Visionary"], ManaPool(U=3, R=2, C=2))
    _cast(state, "Curiosity")
    _drain_stack(state)
    _cast(state, "Niv-Mizzet, Visionary")
    _drain_stack(state)
    assert state.curiosity_effect_count == 3
    assert state.cards_drawn_per_noncreature_spell == 9


# ── Gitaxian Probe ────────────────────────────────────────────────────────────

def test_gitaxian_probe_free_cast_available():
    state = _state(["Gitaxian Probe"], ManaPool())
    actions = generate_actions(state)
    probe_actions = [a for a in actions if a.source_card == "Gitaxian Probe"]
    assert any(a.alt_cost_type == "pay_life" for a in probe_actions)


def test_gitaxian_probe_resolution_draws_one():
    state = _state(["Gitaxian Probe"], ManaPool())
    state.library = ["CardA", "CardB", "CardC", "CardD", "CardE"]
    hand_before = len(state.hand)
    _cast(state, "Gitaxian Probe", alt_cost_type="pay_life", mana=ManaCost())
    # Draw trigger on top; resolve it (Curiosity)
    _resolve_top(state)
    # Now resolve Probe itself: draws 1 extra card
    _resolve_top(state)
    # Total cards added: 3 (Curiosity draw) + 1 (Probe draw) - 1 (probe removed from hand)
    assert len(state.hand) == hand_before + 3


def test_gitaxian_probe_increments_noncreature_count():
    state = _state(["Gitaxian Probe"], ManaPool())
    assert state.noncreature_spells_cast == 0
    _cast(state, "Gitaxian Probe", alt_cost_type="pay_life", mana=ManaCost())
    assert state.noncreature_spells_cast == 1


# ── Jeska's Will ─────────────────────────────────────────────────────────────

def test_jeskas_will_adds_configured_red():
    state = _state(["Jeska's Will"], ManaPool(R=1, C=2))
    state.jeska_opponent_hand_size = 5
    _cast(state, "Jeska's Will")
    _drain_stack(state)
    assert state.floating_mana.R >= 5


def test_jeskas_will_exiles_up_to_three():
    state = _state(["Jeska's Will"], ManaPool(R=1, C=2))
    # First 3 will be drawn by Curiosity trigger; next 3 will be exiled by Jeska
    state.library = ["D1", "D2", "D3", "CardA", "CardB", "CardC"]
    exile_before = len(state.exile)
    _cast(state, "Jeska's Will")
    _drain_stack(state)
    assert len(state.exile) == exile_before + 3


def test_jeskas_will_exiled_spells_castable():
    state = _state(["Jeska's Will"], ManaPool(R=1, C=2))
    # Lotus Petal (free) and Mogg Salvage (free with opponent island) are castable with red mana
    state.library = ["D1", "D2", "D3", "Lotus Petal", "Mogg Salvage", "Rite of Flame"]
    _cast(state, "Jeska's Will")
    _drain_stack(state)
    actions = generate_actions(state)
    cast_sources = {a.source_card for a in actions if a.action_type == CAST_SPELL}
    assert "Lotus Petal" in cast_sources


def test_jeskas_will_exiled_lands_not_castable():
    state = _state(["Jeska's Will"], ManaPool(R=1, C=2))
    state.library = ["D1", "D2", "D3", "Volcanic Island", "Island", "Mountain"]
    _cast(state, "Jeska's Will")
    _drain_stack(state)
    actions = generate_actions(state)
    cast_sources = {a.source_card for a in actions if a.action_type == CAST_SPELL}
    assert "Volcanic Island" not in cast_sources
    assert "Island" not in cast_sources


def test_jeskas_will_exiled_cards_not_pitchable():
    """Exiled cards via Jeska's Will should not appear as pitch options for Force of Will."""
    state = _state(["Jeska's Will", "Force of Will", "Gitaxian Probe"], ManaPool(R=1, C=2, U=1))
    state.library = ["D1", "D2", "D3", "Gitaxian Probe", "Lotus Petal", "Mogg Salvage"]
    _cast(state, "Jeska's Will")
    _drain_stack(state)
    # Put something on stack for Force of Will to target
    _cast(state, "Gitaxian Probe", alt_cost_type="pay_life", mana=ManaCost())
    actions = generate_actions(state)
    fow_pitch_actions = [
        a for a in actions
        if a.source_card == "Force of Will" and a.alt_cost_type == "pitch_blue"
    ]
    # Pitch cards must come from hand, not exile
    for a in fow_pitch_actions:
        assert a.costs.pitched_card in state.hand


def test_jeskas_will_virtue_exile_no_adventure():
    """Virtue of Courage exiled by Jeska's Will cannot cast the adventure side."""
    state = _state(["Jeska's Will"], ManaPool(R=1, C=2))
    # First 3 drawn by Curiosity; Virtue is card #4 so it gets exiled by Jeska
    state.library = ["D1", "D2", "D3", "Virtue of Courage / Embereth Blaze", "CardE", "CardF"]
    _cast(state, "Jeska's Will")
    _drain_stack(state)
    actions = generate_actions(state)
    # Virtue can be cast as enchantment from exile (permission granted)
    virtue_actions = [a for a in actions if a.source_card == "Virtue of Courage / Embereth Blaze"]
    assert len(virtue_actions) >= 1
    # But no adventure cast (adventure is hand-only)
    assert not any(a.alt_cost_type == "adventure" for a in virtue_actions)


# ── Virtue of Courage / Embereth Blaze ───────────────────────────────────────

def test_embereth_blaze_adventure_cast_exiles_virtue():
    state = _state(["Virtue of Courage / Embereth Blaze"], ManaPool(R=2, C=1))
    assert state._opponent_creature_perm is not None
    target_id = state._opponent_creature_perm.perm_id
    _cast(state, "Virtue of Courage / Embereth Blaze",
          alt_cost_type="adventure",
          mana=ManaCost(pip_r=1, generic=1),
          target=target_id)
    _drain_stack(state)
    assert "Virtue of Courage / Embereth Blaze" in state.exile
    assert "Virtue of Courage / Embereth Blaze" not in state.hand


def test_embereth_blaze_grants_virtue_cast_permission():
    state = _state(["Virtue of Courage / Embereth Blaze"], ManaPool(R=2, C=1))
    target_id = state._opponent_creature_perm.perm_id
    _cast(state, "Virtue of Courage / Embereth Blaze",
          alt_cost_type="adventure",
          mana=ManaCost(pip_r=1, generic=1),
          target=target_id)
    _drain_stack(state)
    perm_cards = [p.card_name for p in state.permissions]
    assert "Virtue of Courage / Embereth Blaze" in perm_cards


def test_virtue_castable_from_adventure_exile():
    state = _state(["Virtue of Courage / Embereth Blaze"], ManaPool(R=4, C=4))
    target_id = state._opponent_creature_perm.perm_id
    _cast(state, "Virtue of Courage / Embereth Blaze",
          alt_cost_type="adventure",
          mana=ManaCost(pip_r=1, generic=1),
          target=target_id)
    _drain_stack(state)
    actions = generate_actions(state)
    virtue_cast = [a for a in actions
                   if a.source_card == "Virtue of Courage / Embereth Blaze"
                   and a.alt_cost_type == "exile_permission"]
    assert len(virtue_cast) == 1


def test_virtue_enters_battlefield():
    state = _state(["Virtue of Courage / Embereth Blaze"], ManaPool(R=4, C=4))
    _cast(state, "Virtue of Courage / Embereth Blaze")
    _drain_stack(state)
    names = [p.card_name for p in state.battlefield]
    assert "Virtue of Courage / Embereth Blaze" in names
    assert state.virtue_of_courage_on_battlefield


def test_virtue_trigger_exiles_top_3_on_noncreature_cast():
    state = _state(["Virtue of Courage / Embereth Blaze", "Gitaxian Probe"], ManaPool(R=4, C=4))
    # First 3 drawn when Virtue (noncreature) casts; need 3 more for Virtue trigger
    state.library = ["D1", "D2", "D3", "CardA", "CardB", "CardC", "CardD"]
    _cast(state, "Virtue of Courage / Embereth Blaze")
    _drain_stack(state)
    assert state.virtue_of_courage_on_battlefield
    exile_before = len(state.exile)
    _cast(state, "Gitaxian Probe", alt_cost_type="pay_life", mana=ManaCost())
    assert len(state.exile) == exile_before + 3


def test_virtue_trigger_exiled_cards_castable():
    state = _state(["Virtue of Courage / Embereth Blaze", "Gitaxian Probe"], ManaPool(R=4, C=4, U=4))
    # First 3 drawn when Virtue casts; Lotus Petal/Mogg Salvage/Gitaxian Probe exiled by Virtue trigger
    state.library = ["D1", "D2", "D3", "Lotus Petal", "Mogg Salvage", "Gitaxian Probe", "CardD"]
    _cast(state, "Virtue of Courage / Embereth Blaze")
    _drain_stack(state)
    _cast(state, "Gitaxian Probe", alt_cost_type="pay_life", mana=ManaCost())
    _drain_stack(state)
    actions = generate_actions(state)
    cast_sources = {a.source_card for a in actions if a.action_type == CAST_SPELL}
    assert "Lotus Petal" in cast_sources or "Mogg Salvage" in cast_sources


def test_virtue_trigger_not_fired_without_virtue():
    state = _state(["Gitaxian Probe"], ManaPool())
    state.library = ["CardA", "CardB", "CardC"]
    exile_before = len(state.exile)
    _cast(state, "Gitaxian Probe", alt_cost_type="pay_life", mana=ManaCost())
    assert len(state.exile) == exile_before  # no Virtue = no exile trigger
