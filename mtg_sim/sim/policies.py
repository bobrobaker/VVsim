"""Greedy action selection policy."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional
import tomllib

from .actions import (
    Action,
    CAST_SPELL, RESOLVE_STACK_OBJECT, PLAY_LAND,
    ACTIVATE_MANA_ABILITY, EXILE_FOR_MANA, SACRIFICE_FOR_MANA,
    CHOOSE_IMPRINT, CHOOSE_DISCARD, CHOOSE_TUTOR,
    RISK_SAFE, RISK_NORMAL, RISK_EXPENSIVE, RISK_RISKY, RISK_DESPERATE,
    EXTRA_TURN_WIN_CARDS, NONCREATURE_SPELL_WIN_THRESHOLD,
)

if TYPE_CHECKING:
    from .state import GameState

_DEFAULT_TOML = Path(__file__).parent.parent / "config" / "policy.toml"

# Free permanents that produce mana when cast (0 mana cost, yields future mana)
_FREE_MANA_SOURCES = frozenset({
    "Lotus Petal", "Lion's Eye Diamond",
    "Chrome Mox", "Mox Diamond", "Mox Opal", "Mox Amber",
    "Springleaf Drum",
})

# Spells that produce more mana than they cost (net-mana-positive rituals)
_MANA_RITUALS = frozenset({"Rite of Flame", "Strike It Rich", "Jeska's Will"})

_DEFAULTS: dict = {
    "cast_spell": {
        "instant_win":              10000.0,
        "unknown_card":             10.0,
        "creature":                 30.0,
        "not_noncreature":          5.0,
        "noncreature_base":         100.0,
        "free_cost_bonus":          60.0,
        "cost_1_bonus":             30.0,
        "cost_2_bonus":             15.0,
        "cost_3_bonus":             5.0,
        "mana_ritual_bonus":        50.0,   # net-mana-positive spells
        "free_mana_source_bonus":   55.0,   # free permanent that produces mana
        "tutor_bonus":              25.0,
        "draw_spell_bonus":         20.0,
        "own_stack_target_bonus":   15.0,
        "opponent_dummy_target_bonus": 2.0,
        "vivi_target_penalty":       -2.0,
        "free_alt_cost_bonus":      25.0,
        "tight_mana_penalty":       -20.0,
        "red_spend_penalty":        -30.0,  # spending last red when win card needs it
        "pending_draw_deferral_penalty": -45.0,
        # Pitched-card penalties (exiling from hand)
        "pitch_base_penalty":       -40.0,
        "pitch_priority_extra":     -80.0,  # additional penalty for high-priority pitched cards
        "pitch_win_card_penalty":   -160.0, # pitching a win card is catastrophic
    },
    "risk": {
        "safe":      0.0,
        "normal":    0.0,
        "expensive": -15.0,
        "risky":     -35.0,
        "desperate": -70.0,
    },
    "resolve": {
        "no_target_fallback":       20.0,
        "draw_trigger":             142.0,
        "draw_trigger_led_preempt": 30.0,
        "mana_producer_priority":   190.0,
        "mana_producer":            85.0,
        "engine_card":              80.0,
        "default":                  40.0,
    },
    "mana": {
        "led_crack_with_draws":   88.0,
        "enables_win_cast":       125.0,  # mana enables casting a win card
        "enables_new_cast":       90.0,
        "risk_safe":              70.0,
        "default":                50.0,
        "exile_enables_win_cast": 110.0,
        "exile_enables_new_cast": 75.0,
        "exile_default":          45.0,
        "red_for_win_bonus":      22.0,   # generating red when win card needs it
        "red_mana_bonus":          9.0,   # general bonus for producing red mana
        "reserve_r_bonus":        13.0,   # bonus for reaching 1R from 0R
        "reserve_u_bonus":         6.0,   # bonus for reaching 1U from 0U
    },
    "land": {
        "enables_new_cast": 78.0,
        "default":          55.0,
    },
    "imprint": {
        "baseline":           50.0,
        "color_needed_bonus": 15.0,
        "mv_penalty_per_pip": 4.0,
    },
    "discard": {
        "baseline":            60.0,
        "enters_tapped_bonus": 15.0,
        "basic_land_bonus":    10.0,
        "excess_color_bonus":  5.0,
    },
    "tutor": {
        "top_score":      100.0,
        "step_penalty":   3.0,
        "unlisted_score": 50.0,
    },
}

# Module-level cache: avoid re-reading TOML on every Monte Carlo call.
_config_cache: dict | None = None
_config_cache_key: str = "\x00"  # sentinel; no real path can match this


def _clear_config_cache() -> None:
    """Reset the module-level config cache. For use in tests only."""
    global _config_cache, _config_cache_key
    _config_cache = None
    _config_cache_key = "\x00"


def load_policy_config(path=None) -> dict:
    """Return policy weights, deep-merging TOML over defaults.

    path=None auto-loads _DEFAULT_TOML if it exists; explicit path overrides.
    Missing keys in the TOML fall back to _DEFAULTS values.
    """
    global _config_cache, _config_cache_key
    resolved = Path(path) if path is not None else _DEFAULT_TOML
    key = str(resolved)
    if _config_cache is not None and _config_cache_key == key:
        return _config_cache

    cfg: dict = {k: dict(v) for k, v in _DEFAULTS.items()}

    if resolved.exists():
        with open(resolved, "rb") as f:
            toml = tomllib.load(f)
        for section, values in toml.items():
            if section in cfg:
                cfg[section].update(values)
            else:
                cfg[section] = values

    _config_cache = cfg
    _config_cache_key = key
    return cfg


@dataclass
class ScoredAction:
    action: Action
    score: float
    rank: int         # 1-based; rank 1 is the policy's top choice
    delta: float      # score - top_score (0.0 for rank 1, negative otherwise)
    reasons: list[str]


def rank_actions(
    state: GameState,
    actions: list[Action],
    cfg: dict | None = None,
) -> list[ScoredAction]:
    """Return all actions sorted by descending score with rank/delta/reasons."""
    if cfg is None:
        cfg = load_policy_config()
    pairs = [(score_action_with_reasons(state, a, cfg), a) for a in actions]
    pairs.sort(key=lambda x: -x[0][0])
    top_score = pairs[0][0][0] if pairs else 0.0
    return [
        ScoredAction(
            action=action,
            score=score,
            rank=rank,
            delta=score - top_score,
            reasons=reasons,
        )
        for rank, ((score, reasons), action) in enumerate(pairs, 1)
    ]


def choose_action(
    state: GameState,
    actions: list[Action],
    cfg: dict | None = None,
) -> Optional[Action]:
    if not actions:
        return None
    if cfg is None:
        cfg = load_policy_config()
    ranked = rank_actions(state, actions, cfg)
    best = ranked[0]
    if best.score <= 0:
        return None
    return best.action


def score_action(
    state: GameState,
    action: Action,
    cfg: dict | None = None,
) -> float:
    if cfg is None:
        cfg = load_policy_config()
    score, _ = score_action_with_reasons(state, action, cfg)
    return score


def score_action_with_reasons(
    state: GameState,
    action: Action,
    cfg: dict,
) -> tuple[float, list[str]]:
    features = extract_features(state, action)
    weights = feature_weights_from_config(cfg)
    return score_features(features, weights)


def extract_features(state: GameState, action: Action) -> dict[str, float]:
    """Return the active sparse policy features for a legal action."""
    from .cards import get_card

    features: dict[str, float] = {}
    s_card = action.source_card
    cd = get_card(s_card) if s_card else None

    # ── Instant win ───────────────────────────────────────────────────────────
    if action.action_type == CAST_SPELL and s_card in EXTRA_TURN_WIN_CARDS:
        _add_feature(features, "guardrail.extra_turn_win")
        return features

    # ── Cast spell ────────────────────────────────────────────────────────────
    if action.action_type == CAST_SPELL:
        if cd is None:
            _add_feature(features, "card.unknown")
            return features

        if cd.is_creature:
            _add_feature(features, "card.creature")
            _add_risk_feature(features, action.risk_level)
            return features

        if not cd.is_noncreature_spell:
            _add_feature(features, "card.not_noncreature")
            return features

        _add_feature(features, "card.noncreature")

        effective_cost = action.costs.mana.total_mana
        if effective_cost == 0:
            _add_feature(features, "cost.free")
        elif effective_cost == 1:
            _add_feature(features, "cost.mana_value.1")
        elif effective_cost == 2:
            _add_feature(features, "cost.mana_value.2")
        elif effective_cost <= 3:
            _add_feature(features, "cost.mana_value.3")

        if s_card in _MANA_RITUALS:
            _add_feature(features, "card.mana_ritual_legacy")

        if effective_cost == 0 and s_card in _FREE_MANA_SOURCES:
            _add_feature(features, "card.free_mana_source_legacy")

        if _is_tutor(s_card):
            _add_feature(features, "card.tutor_legacy")

        if s_card in ("Gitaxian Probe", "Twisted Image", "Repeal"):
            _add_feature(features, "card.draw_spell_legacy")

        if action.target and action.requires_target:
            obj = state.get_stack_object(action.target)
            if obj:
                _add_feature(features, "target.stack_object")
            else:
                target_perm = state.get_perm_by_id(action.target)
                if target_perm is not None:
                    if target_perm.card_name.startswith("_opponent"):
                        _add_feature(features, "target.opponent_dummy")
                    elif target_perm.card_name == "Vivi Ornitier":
                        _add_feature(features, "target.vivi")

        if action.alt_cost_type in ("pay_life", "commander_free", "delayed_upkeep"):
            _add_feature(features, f"alt.{action.alt_cost_type}")

        # Pitching a card exiles it permanently — undo the free_cost_bonus and apply
        # a value-based penalty based on how good the pitched card is.
        if action.alt_cost_type in ("pitch_blue", "pitch_red", "pitch_blue_x"):
            if effective_cost == 0:
                _add_feature(features, "pitch.undo_free_cost")
            _add_pitch_features(features, action.costs.pitched_card)

        _add_risk_feature(features, action.risk_level)

        if effective_cost >= 3 and _mana_is_tight(state):
            _add_feature(features, "risk.tight_mana")

        # Penalise spending our only red mana on spells that don't make mana back,
        # when a win card in hand still needs red to be cast.
        if (action.costs.mana.pip_r > 0
                and state.floating_mana.R <= action.costs.mana.pip_r
                and s_card not in _MANA_RITUALS
                and _any_win_card_needs_red(state)):
            _add_feature(features, "mana.spend_last_red")

        if _should_defer_cast_to_pending_draw(state, action):
            _add_feature(features, "cast.defer_to_pending_draw")

        return features

    # ── Resolve stack object ──────────────────────────────────────────────────
    if action.action_type == RESOLVE_STACK_OBJECT:
        obj = state.get_stack_object(action.target or "")
        if obj is None:
            _add_feature(features, "resolve.no_target_fallback")
            return features

        if obj.is_draw_trigger:
            if _led_crack_is_better(state):
                _add_feature(features, "resolve.draw_trigger_led_preempt")
                return features
            _add_feature(features, "resolve.draw_trigger")
            return features

        if _will_produce_mana(obj.card_name):
            if _should_prioritize_mana_producer_resolution(state, obj.card_name):
                _add_feature(features, "resolve.mana_producer_priority")
                return features
            _add_feature(features, "resolve.mana_producer_legacy")
            return features

        if _is_engine_card(obj.card_name):
            _add_feature(features, "resolve.engine_card_legacy")
            return features

        _add_feature(features, "resolve.default")
        return features

    # ── Mana actions ──────────────────────────────────────────────────────────
    if action.action_type in (ACTIVATE_MANA_ABILITY, SACRIFICE_FOR_MANA):
        if (action.action_type == SACRIFICE_FOR_MANA
                and action.source_card == "Lion's Eye Diamond"
                and state.pending_curiosity_draws > 0
                and len(state.hand) <= 1):
            _add_feature(features, "mana.led_crack_with_draws")
            return features

        if _mana_enables_win_cast(state, action):
            _add_feature(features, "mana.enables_win_cast")
        elif _mana_enables_new_cast(state, action):
            _add_feature(features, "mana.enables_new_cast")
        elif action.risk_level == RISK_SAFE:
            _add_feature(features, "mana.risk_safe")
        else:
            _add_feature(features, "mana.default")

        _add_mana_color_features(features, state, action)
        return features

    if action.action_type == EXILE_FOR_MANA:
        if _mana_enables_win_cast(state, action):
            _add_feature(features, "mana.exile_enables_win_cast")
        elif _mana_enables_new_cast(state, action):
            _add_feature(features, "mana.exile_enables_new_cast")
        else:
            _add_feature(features, "mana.exile_default")

        _add_mana_color_features(features, state, action)
        return features

    # ── Land play ─────────────────────────────────────────────────────────────
    if action.action_type == PLAY_LAND:
        if _land_enables_new_cast(state, action):
            _add_feature(features, "land.enables_new_cast")
            return features
        _add_feature(features, "land.default")
        return features

    # ── Pending choice actions ────────────────────────────────────────────────
    if action.action_type == CHOOSE_IMPRINT:
        _add_imprint_features(features, state, action)
        return features

    if action.action_type == CHOOSE_DISCARD:
        _add_discard_features(features, state, action)
        return features

    if action.action_type == CHOOSE_TUTOR:
        _add_tutor_features(features, action)
        return features

    _add_feature(features, "action.unknown")
    return features


def feature_weights_from_config(cfg: dict) -> dict[str, float]:
    """Adapt the existing sectioned policy config to flat sparse feature weights."""
    cs = cfg["cast_spell"]
    rc = cfg["resolve"]
    mc = cfg["mana"]
    lc = cfg["land"]
    risk = cfg["risk"]
    return {
        "guardrail.extra_turn_win": cs["instant_win"],
        "card.unknown": cs["unknown_card"],
        "card.creature": cs["creature"],
        "card.not_noncreature": cs["not_noncreature"],
        "card.noncreature": cs["noncreature_base"],
        "cost.free": cs["free_cost_bonus"],
        "cost.mana_value.1": cs["cost_1_bonus"],
        "cost.mana_value.2": cs["cost_2_bonus"],
        "cost.mana_value.3": cs["cost_3_bonus"],
        "card.mana_ritual_legacy": cs["mana_ritual_bonus"],
        "card.free_mana_source_legacy": cs["free_mana_source_bonus"],
        "card.tutor_legacy": cs["tutor_bonus"],
        "card.draw_spell_legacy": cs["draw_spell_bonus"],
        "target.stack_object": cs["own_stack_target_bonus"],
        "target.opponent_dummy": cs["opponent_dummy_target_bonus"],
        "target.vivi": cs["vivi_target_penalty"],
        "alt.pay_life": cs["free_alt_cost_bonus"],
        "alt.commander_free": cs["free_alt_cost_bonus"],
        "alt.delayed_upkeep": cs["free_alt_cost_bonus"],
        "pitch.undo_free_cost": -cs["free_cost_bonus"],
        "pitch.card": cs["pitch_base_penalty"],
        "pitch.priority_card": cs["pitch_priority_extra"],
        "pitch.win_card": cs["pitch_win_card_penalty"],
        "risk.expensive": risk.get("expensive", -15.0),
        "risk.risky": risk.get("risky", -35.0),
        "risk.desperate": risk.get("desperate", -70.0),
        "risk.tight_mana": cs["tight_mana_penalty"],
        "mana.spend_last_red": cs["red_spend_penalty"],
        "cast.defer_to_pending_draw": cs["pending_draw_deferral_penalty"],
        "resolve.no_target_fallback": rc["no_target_fallback"],
        "resolve.draw_trigger": rc["draw_trigger"],
        "resolve.draw_trigger_led_preempt": rc["draw_trigger_led_preempt"],
        "resolve.mana_producer_priority": rc["mana_producer_priority"],
        "resolve.mana_producer_legacy": rc["mana_producer"],
        "resolve.engine_card_legacy": rc["engine_card"],
        "resolve.default": rc["default"],
        "mana.led_crack_with_draws": mc["led_crack_with_draws"],
        "mana.enables_win_cast": mc["enables_win_cast"],
        "mana.enables_new_cast": mc["enables_new_cast"],
        "mana.risk_safe": mc["risk_safe"],
        "mana.default": mc["default"],
        "mana.exile_enables_win_cast": mc["exile_enables_win_cast"],
        "mana.exile_enables_new_cast": mc["exile_enables_new_cast"],
        "mana.exile_default": mc["exile_default"],
        "mana.produces_red_for_win": mc["red_for_win_bonus"],
        "mana.produces_red": mc["red_mana_bonus"],
        "mana.reserve_r": mc["reserve_r_bonus"],
        "mana.reserve_u": mc["reserve_u_bonus"],
        "land.enables_new_cast": lc["enables_new_cast"],
        "land.default": lc["default"],
        "choice.fixed_score": 1.0,
        "choice.imprint": cfg["imprint"]["baseline"],
        "choice.imprint.color_needed": cfg["imprint"]["color_needed_bonus"],
        "choice.imprint.mv": -cfg["imprint"]["mv_penalty_per_pip"],
        "choice.imprint.priority_penalty_legacy": 1.0,
        "choice.discard": cfg["discard"]["baseline"],
        "choice.discard.enters_tapped": cfg["discard"]["enters_tapped_bonus"],
        "choice.discard.basic_land": cfg["discard"]["basic_land_bonus"],
        "choice.discard.excess_color": cfg["discard"]["excess_color_bonus"],
        "choice.tutor": cfg["tutor"]["top_score"],
        "choice.tutor.step": -cfg["tutor"]["step_penalty"],
        "choice.tutor.unlisted": cfg["tutor"]["unlisted_score"],
    }


def score_features(features: dict[str, float], weights: dict[str, float]) -> tuple[float, list[str]]:
    """Score active sparse features and return nonzero contribution names."""
    score = 0.0
    reasons: list[str] = []
    for name, value in features.items():
        weight = weights.get(name, 0.0)
        contribution = value * weight
        if contribution != 0.0:
            score += contribution
            reasons.append(name)
    return score, reasons


def _add_feature(features: dict[str, float], name: str, value: float = 1.0) -> None:
    if value != 0.0:
        features[name] = features.get(name, 0.0) + value


def _add_risk_feature(features: dict[str, float], risk: str) -> None:
    mapping = {
        RISK_EXPENSIVE: "risk.expensive",
        RISK_RISKY: "risk.risky",
        RISK_DESPERATE: "risk.desperate",
    }
    feature = mapping.get(risk)
    if feature:
        _add_feature(features, feature)


def _add_pitch_features(features: dict[str, float], card_name: str | None) -> None:
    if card_name in EXTRA_TURN_WIN_CARDS:
        _add_feature(features, "pitch.win_card")
        return
    _add_feature(features, "pitch.card")
    if card_name is not None:
        try:
            idx = _TUTOR_PRIORITY.index(card_name)
        except ValueError:
            return
        frac = 1.0 - idx / max(len(_TUTOR_PRIORITY), 1)
        _add_feature(features, "pitch.priority_card", frac)


def _add_mana_color_features(features: dict[str, float], state: GameState, action: Action) -> None:
    gained = action.effects.add_mana
    produces_red = gained.R > 0
    produces_any = gained.ANY > 0
    produces_blue = gained.U > 0

    if _any_win_card_needs_red(state) and (produces_red or produces_any):
        _add_feature(features, "mana.produces_red_for_win")
    elif produces_red:
        _add_feature(features, "mana.produces_red")

    # Reserve bonuses: reaching 1R (more valuable) or 1U from zero
    if produces_red and state.floating_mana.R == 0:
        _add_feature(features, "mana.reserve_r")
    elif (produces_blue or produces_any) and state.floating_mana.U == 0:
        _add_feature(features, "mana.reserve_u")


def _add_imprint_features(features: dict[str, float], state: GameState, action: Action) -> None:
    """Emit CHOOSE_IMPRINT features matching the legacy score shape."""
    from .cards import get_card

    card = action.source_card
    if card is None:
        _add_feature(features, "choice.fixed_score", 1.0)
        return

    cd = get_card(card)
    if cd is None:
        _add_feature(features, "choice.fixed_score", 10.0)
        return

    _add_feature(features, "choice.imprint")

    priority_idx = next((i for i, c in enumerate(_TUTOR_PRIORITY) if c == card), None)
    if priority_idx is not None:
        _add_feature(features, "choice.imprint.priority_penalty_legacy", -max(5.0, 40.0 - priority_idx * 2.0))

    color = "U" if cd.has_blue else "R"
    need_u = sum(1 for c in state.hand if (c2 := get_card(c)) and c2 and c2.pip_u > 0)
    need_r = sum(1 for c in state.hand if (c2 := get_card(c)) and c2 and c2.pip_r > 0)
    if color == "U" and need_u > state.floating_mana.U:
        _add_feature(features, "choice.imprint.color_needed")
    if color == "R" and need_r > state.floating_mana.R:
        _add_feature(features, "choice.imprint.color_needed")

    _add_feature(features, "choice.imprint.mv", cd.mv)


def _add_discard_features(features: dict[str, float], state: GameState, action: Action) -> None:
    """Emit CHOOSE_DISCARD features matching the legacy score shape."""
    from .cards import get_card

    land = action.source_card
    if land is None:
        _add_feature(features, "choice.fixed_score", 1.0)
        return

    cd = get_card(land)
    if cd is None:
        _add_feature(features, "choice.fixed_score", 20.0)
        return

    _add_feature(features, "choice.discard")
    if cd.land_enters_tapped == "true":
        _add_feature(features, "choice.discard.enters_tapped")
    if "Basic" in cd.card_types:
        _add_feature(features, "choice.discard.basic_land")

    colors = cd.mana_colors or ""
    if "U" in colors and state.floating_mana.U >= 2:
        _add_feature(features, "choice.discard.excess_color")
    if "R" in colors and state.floating_mana.R >= 2:
        _add_feature(features, "choice.discard.excess_color")


def _add_tutor_features(features: dict[str, float], action: Action) -> None:
    """Emit CHOOSE_TUTOR features matching the legacy priority score."""
    card = action.source_card
    if card is None:
        return
    try:
        idx = _TUTOR_PRIORITY.index(card)
    except ValueError:
        _add_feature(features, "choice.tutor.unlisted")
        return
    _add_feature(features, "choice.tutor")
    _add_feature(features, "choice.tutor.step", idx)


def _is_engine_card(card_name: str | None) -> bool:
    ENGINE_CARDS = {
        "Tandem Lookout", "Curiosity", "Ophidian Eye",
        "Sol Ring", "Mana Vault", "Grim Monolith",
        "Lotus Petal", "Chrome Mox", "Mox Diamond",
        "Mox Opal", "Mox Amber", "Springleaf Drum",
    }
    return card_name in ENGINE_CARDS


def _is_tutor(card_name: str | None) -> bool:
    TUTORS = {
        "Mystical Tutor", "Merchant Scroll", "Solve the Equation",
        "Gamble", "Intuition", "Drift of Phantasms",
    }
    return card_name in TUTORS


def _will_produce_mana(card_name: str) -> bool:
    MANA_PRODUCERS = {
        "Rite of Flame", "Strike It Rich", "Jeska's Will",
        "Sol Ring", "Mana Vault", "Grim Monolith",
        "Lotus Petal", "Lion's Eye Diamond",
        "Chrome Mox", "Mox Diamond", "Mox Opal", "Mox Amber",
        "Springleaf Drum", "Jeweled Amulet",
    }
    return card_name in MANA_PRODUCERS


def _should_prioritize_mana_producer_resolution(
    state: GameState,
    card_name: str,
) -> bool:
    """Prefer turning pending mana-producing spells into mana before other work."""
    if not _will_produce_mana(card_name):
        return False
    if not state.stack:
        return False
    top = state.stack[-1]
    return top.card_name == card_name and not top.is_draw_trigger


def _should_defer_cast_to_pending_draw(state: GameState, action: Action) -> bool:
    """Prefer resolving a top Curiosity draw before non-win casts."""
    if not state.stack or not state.stack[-1].is_draw_trigger:
        return False
    if action.source_card in EXTRA_TURN_WIN_CARDS:
        return False
    return True


def _led_crack_is_better(state: GameState) -> bool:
    """True when cracking LED before resolving draws is the right play.

    Conditions: LED is on the battlefield, hand is tiny (≤1 card), and there
    are pending curiosity draws queued up — discarding a nearly-empty hand and
    getting 3 mana before drawing new cards is a net gain.
    """
    if state.pending_curiosity_draws <= 0:
        return False
    if len(state.hand) > 1:
        return False
    return any(p.card_name == "Lion's Eye Diamond" for p in state.battlefield)


def _mana_is_tight(state: GameState) -> bool:
    return state.floating_mana.total() <= 2


def _any_win_card_needs_red(state: GameState) -> bool:
    """True if we have a win card in hand that we can't yet cast due to missing red."""
    from .cards import get_card
    from .mana import can_pay_cost, ManaCost
    for card_name in state.hand:
        if card_name not in EXTRA_TURN_WIN_CARDS:
            continue
        cd = get_card(card_name)
        if cd is None or cd.pip_r == 0:
            continue
        cost = ManaCost(pip_u=cd.pip_u, pip_r=cd.pip_r, generic=cd.generic_mana,
                        pip_ur_hybrid=cd.pip_ur_hybrid)
        if not can_pay_cost(state.floating_mana, cost):
            return True
    return False


def _mana_enables_win_cast(state: GameState, mana_action: Action) -> bool:
    """True if adding this mana would let us cast a win card we can't currently cast."""
    from .mana import ManaPool, can_pay_cost, ManaCost
    from .cards import get_card

    gained = mana_action.effects.add_mana
    if gained.total() == 0:
        return False

    simulated_pool = state.floating_mana.copy()
    simulated_pool.add(gained)

    for card_name in state.hand:
        if card_name not in EXTRA_TURN_WIN_CARDS:
            continue
        cd = get_card(card_name)
        if cd is None:
            continue
        cost = ManaCost(pip_u=cd.pip_u, pip_r=cd.pip_r, generic=cd.generic_mana,
                        pip_ur_hybrid=cd.pip_ur_hybrid)
        if not can_pay_cost(state.floating_mana, cost) and can_pay_cost(simulated_pool, cost):
            return True
    return False


def _mana_enables_new_cast(state: GameState, mana_action: Action) -> bool:
    """Check if activating this mana source would let us cast something we can't currently."""
    from .mana import ManaPool, can_pay_cost
    from .mana import ManaCost
    from .cards import get_card
    from .action_generator import generate_actions

    gained = mana_action.effects.add_mana
    if gained.total() == 0:
        return False

    simulated_pool = state.floating_mana.copy()
    simulated_pool.add(gained)

    for card_name in state.hand:
        cd = get_card(card_name)
        if cd is None or cd.is_land or cd.is_creature:
            continue
        cost = ManaCost(pip_u=cd.pip_u, pip_r=cd.pip_r, generic=cd.generic_mana,
                        pip_ur_hybrid=cd.pip_ur_hybrid)
        if not can_pay_cost(state.floating_mana, cost) and can_pay_cost(simulated_pool, cost):
            return True
    return False


_TUTOR_PRIORITY = [
    "Alchemist's Gambit", "Final Fortune", "Last Chance", "Warrior's Oath",
    "Gitaxian Probe", "Lotus Petal", "Lion's Eye Diamond", "Simian Spirit Guide",
    "Fierce Guardianship", "Pact of Negation",
    "Rite of Flame", "Mystical Tutor", "Merchant Scroll", "Solve the Equation",
    "Gamble", "Intuition",
    "Force of Will", "Swan Song", "Flusterstorm", "Mental Misstep",
]


def _land_enables_new_cast(state: GameState, land_action: Action) -> bool:
    """Would playing this land (and tapping it) enable a new cast?"""
    from .cards import get_card
    from .mana import ManaPool, can_pay_cost, ManaCost

    land_name = land_action.source_card
    if not land_name:
        return False
    cd = get_card(land_name)
    if cd is None or not cd.produces_mana:
        return False

    # Estimate mana gain
    if cd.land_enters_tapped == "true":
        return False  # can't tap it this turn

    try:
        amount = int(cd.mana_amount)
    except (ValueError, TypeError):
        amount = 1

    simulated = state.floating_mana.copy()
    if "U" in (cd.mana_colors or ""):
        simulated.U += amount
    elif "R" in (cd.mana_colors or ""):
        simulated.R += amount
    else:
        simulated.ANY += amount

    for card_name in state.hand:
        c = get_card(card_name)
        if c is None or c.is_land:
            continue
        cost = ManaCost(pip_u=c.pip_u, pip_r=c.pip_r, generic=c.generic_mana,
                        pip_ur_hybrid=c.pip_ur_hybrid)
        if not can_pay_cost(state.floating_mana, cost) and can_pay_cost(simulated, cost):
            return True
    return False
