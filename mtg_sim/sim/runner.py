"""Main simulation runner."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from random import Random
from pathlib import Path
from typing import Optional
from .mana import ManaPool
from .state import GameState, Permanent, ActionLog, OPPONENT_COUNT
from .stack import StackObject
from .actions import (
    WIN_EXTRA_TURN, WIN_NONCREATURE_SPELL_COUNT,
    BRICK_NO_ACTIONS, BRICK_NO_USEFUL_ACTIONS, ERROR_INVALID_STATE,
    EXTRA_TURN_WIN_CARDS, NONCREATURE_SPELL_WIN_THRESHOLD,
)
from .cards import get_card
from .action_generator import generate_actions
from .resolver import resolve_action, draw_cards
from .policies import choose_action, rank_actions, load_policy_config

DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent

MAX_STEPS = 500


@dataclass
class RunConfig:
    seed: int
    starting_hand: list = field(default_factory=list)
    starting_floating_mana: ManaPool = field(default_factory=ManaPool)
    library_order: list | None = None
    curiosity_effect_count: int = 1
    jeska_opponent_hand_size: int = 7
    starting_battlefield: list = field(default_factory=lambda: ["Volcanic Island"])
    # Cards in starting_battlefield that enter tapped (Volcanic Island already tapped because
    # we tapped it for the starting mana floating into the sim).
    starting_battlefield_tapped: list = field(default_factory=lambda: ["Volcanic Island"])
    land_play_available: bool = False
    debug: bool = False
    # Interactive mode: pause after each action generation and let the user pick.
    manual_mode: bool = False
    # Path to policy TOML config; None auto-loads mtg_sim/config/policy.toml if present.
    policy_config_path: Path | None = None
    # Path for policy adjustment JSONL log (written when user overrides top policy action).
    adjustment_log_path: Path | None = None
    # Path for manual observation JSONL log (buffered per session, saved at session end).
    manual_observation_log_path: Path | None = None
    # Simulation assumptions
    opponent_controls_island: bool = True  # almost always true in cEDH


@dataclass
class RunResult:
    outcome: str
    noncreature_spells_cast: int = 0
    total_cards_drawn: int = 0
    final_hand_size: int = 0
    final_mana: ManaPool = field(default_factory=ManaPool)
    brick_reason: str = ""
    winning_card: str = ""
    steps: int = 0
    trace: list = field(default_factory=list)
    stranded_cards: list = field(default_factory=list)

    @property
    def won(self) -> bool:
        return self.outcome in (WIN_EXTRA_TURN, WIN_NONCREATURE_SPELL_COUNT)


def simulate_run(config: RunConfig, active_deck: list[str]) -> RunResult:
    from .state import validate_state
    rng = Random(config.seed)
    state = _build_initial_state(config, active_deck, rng)
    validate_state(state)

    # Capture initial state info before the draw
    bf_names = [p.card_name for p in state.battlefield]
    hand_str = ", ".join(config.starting_hand) if config.starting_hand else "(empty)"

    # Initial Curiosity draw
    drawn = draw_cards(state, state.cards_drawn_per_noncreature_spell)
    state.trace.append(ActionLog(
        step=0,
        event_type="INITIAL_DRAW",
        action_description=f"Initial Curiosity draw: {len(drawn)} cards",
        cards_drawn=drawn,
        mana_before=state.floating_mana.copy(),
        mana_after=state.floating_mana.copy(),
        hand_size_before=0,
        hand_size_after=len(state.hand),
        noncreature_spells_cast=0,
        notes=[
            f"Battlefield: {bf_names}",
            f"Starting hand: {hand_str}",
            f"Starting mana: {config.starting_floating_mana}",
            f"Land play available: {state.land_play_available}",
        ],
    ))

    cfg = load_policy_config(config.policy_config_path)

    obs_buffer: list = []
    # Tracks whether a `resolution` bug note was filed; taints all subsequent snapshots.
    taint_state: dict = {"tainted": False}

    result = _simulate_loop(config, state, cfg, obs_buffer, taint_state)

    if config.manual_mode and obs_buffer:
        _manual_session_save(obs_buffer, config.manual_observation_log_path)

    return result


def _simulate_loop(
    config: RunConfig,
    state: GameState,
    cfg: dict | None,
    obs_buffer: list,
    taint_state: dict,
) -> RunResult:
    from .state import validate_state
    for step in range(MAX_STEPS):
        if config.debug:
            validate_state(state)
        # ── Check win ────────────────────────────────────────────────────────
        outcome, winning_card = _check_win(state)
        if outcome:
            return RunResult(
                outcome=outcome,
                noncreature_spells_cast=state.noncreature_spells_cast,
                total_cards_drawn=state.total_cards_drawn,
                final_hand_size=len(state.hand),
                final_mana=state.floating_mana.copy(),
                winning_card=winning_card,
                steps=step,
                trace=state.trace,
            )

        # ── Generate actions ─────────────────────────────────────────────────
        actions = generate_actions(state)

        if not actions:
            return _brick(state, BRICK_NO_ACTIONS, "No legal actions", step)

        # ── Policy selects action ─────────────────────────────────────────────
        if config.manual_mode:
            chosen = _manual_choose_action(
                state, actions, step,
                cfg=cfg,
                adjustment_log_path=config.adjustment_log_path,
                observation_buffer=obs_buffer,
                taint_state=taint_state,
                policy_trainable=not taint_state["tainted"],
                seed=config.seed,
            )
        else:
            chosen = choose_action(state, actions, cfg)

        if chosen is None:
            return _brick(state, BRICK_NO_USEFUL_ACTIONS, "No useful action", step)

        # ── Execute ───────────────────────────────────────────────────────────
        resolve_action(state, chosen)

        # ── Post-action win check ─────────────────────────────────────────────
        outcome, winning_card = _check_win(state)
        if outcome:
            return RunResult(
                outcome=outcome,
                noncreature_spells_cast=state.noncreature_spells_cast,
                total_cards_drawn=state.total_cards_drawn,
                final_hand_size=len(state.hand),
                final_mana=state.floating_mana.copy(),
                winning_card=winning_card,
                steps=step + 1,
                trace=state.trace,
            )

    return _brick(state, ERROR_INVALID_STATE, f"Exceeded {MAX_STEPS} steps", MAX_STEPS)


def _check_win(state: GameState) -> tuple[str, str]:
    # Extra-turn card successfully cast = it's now on the stack. Wins immediately.
    for obj in state.stack:
        if obj.card_name in EXTRA_TURN_WIN_CARDS:
            return WIN_EXTRA_TURN, obj.card_name
    if state.noncreature_spells_cast >= NONCREATURE_SPELL_WIN_THRESHOLD:
        return WIN_NONCREATURE_SPELL_COUNT, f"{state.noncreature_spells_cast} spells"
    bf_names = {p.card_name for p in state.battlefield}
    # Quicksilver Elemental on battlefield + {U} floating = deterministic win.
    if "Quicksilver Elemental" in bf_names and state.floating_mana.U >= 1:
        return WIN_EXTRA_TURN, "Quicksilver Elemental"
    # Hullbreaker Horror on battlefield + spell on stack + 2 eligible mana permanents = loop win.
    if "Hullbreaker Horror" in bf_names and state.stack:
        eligible = sum(
            1 for p in state.battlefield
            if _is_hullbreaker_eligible(p.card_name)
        )
        if eligible >= 2:
            return WIN_EXTRA_TURN, "Hullbreaker Horror"
    return "", ""


def _is_hullbreaker_eligible(card_name: str) -> bool:
    """Nonland, nontoken, reusable, non-sacrifice mana source that is mana-neutral-or-better."""
    cd = get_card(card_name)
    if cd is None:
        return False
    if cd.is_land:
        return False
    if not cd.produces_mana:
        return False
    if cd.requires_sacrifice:
        return False
    if cd.mana_timing not in ("repeatable", "conditional"):
        return False
    try:
        return int(cd.mana_amount) >= cd.mv
    except (ValueError, TypeError):
        return False


def _manual_choose_action(
    state: GameState,
    actions: list,
    step: int,
    cfg: dict | None = None,
    adjustment_log_path: Path | None = None,
    observation_buffer: list | None = None,
    taint_state: dict | None = None,
    policy_trainable: bool = True,
    seed: int | None = None,
) -> Optional:
    """Present ranked actions to the user and return their choice, or None to brick.

    Displays policy score, rank, and delta for each action (no reason labels).
    Supports commands: n/note, m/missing, i/illegal, r/resolution, q/quit.
    Buffers decision snapshots in observation_buffer for session-end save.
    If the user picks a non-top action and adjustment_log_path is set, prompts
    for a reason and appends one JSONL entry to adjustment_log_path.
    """
    ranked = rank_actions(state, actions, cfg)

    print(f"\n{'='*60}")
    print(f"Step {step + 1} | Spells cast: {state.noncreature_spells_cast} | "
          f"Pending draws: {state.pending_curiosity_draws}")
    print(f"Mana: {state.floating_mana}")
    print(f"Hand ({len(state.hand)}): {state.hand}")
    print(f"Battlefield: {state.battlefield}")
    if state.stack:
        print(f"Stack: {[str(o) for o in state.stack]}")
    if state.graveyard:
        print(f"Graveyard: {state.graveyard}")
    if state.exile:
        print(f"Exile: {state.exile}")

    print(f"\nAvailable actions:")
    for i, sa in enumerate(ranked):
        marker = "★ BEST  " if sa.rank == 1 else f"Δ{sa.delta:+.1f}".ljust(8)
        print(f"  [{i:2d}]  {sa.score:7.1f}  {marker}  {sa.action.description}")
    print("  [ n] Note  [ m] Missing action  [ i] Illegal action  [ r] Resolution bug  [ q] Quit")

    notes: list = []
    step_trainable = policy_trainable

    while True:
        try:
            raw = input("\nChoose: ").strip()
        except (EOFError, KeyboardInterrupt):
            return None

        cmd = raw.lower()

        if cmd in ("q", "quit"):
            return None

        if cmd in ("n", "note"):
            try:
                text = input("Note: ").strip()
            except (EOFError, KeyboardInterrupt):
                text = ""
            notes.append({"kind": "note", "text": text, "policy_trainable": True})
            continue

        if cmd in ("m", "missing"):
            try:
                text = input("Missing action description: ").strip()
            except (EOFError, KeyboardInterrupt):
                text = ""
            notes.append({"kind": "missing", "text": text, "policy_trainable": False})
            step_trainable = False
            continue

        if cmd in ("i", "illegal"):
            try:
                idx_str = input("Illegal action index: ").strip()
                note_text = input("Note: ").strip()
            except (EOFError, KeyboardInterrupt):
                idx_str, note_text = "", ""
            try:
                illegal_idx = int(idx_str)
            except ValueError:
                illegal_idx = None
            notes.append({"kind": "illegal", "action_index": illegal_idx, "text": note_text, "policy_trainable": False})
            step_trainable = False
            continue

        if cmd in ("r", "resolution"):
            try:
                note_text = input("Note: ").strip()
            except (EOFError, KeyboardInterrupt):
                note_text = ""
            notes.append({"kind": "resolution", "text": note_text, "policy_trainable": False})
            step_trainable = False
            if taint_state is not None:
                taint_state["tainted"] = True
            continue

        try:
            idx = int(raw)
            if 0 <= idx < len(ranked):
                chosen_sa = ranked[idx]
                print(f">>> {chosen_sa.action.description}")

                if observation_buffer is not None:
                    entry = _build_manual_decision_entry(
                        state=state,
                        ranked=ranked,
                        chosen_sa=chosen_sa,
                        chosen_idx=idx,
                        step=step,
                        seed=seed,
                        notes=notes,
                        policy_trainable=step_trainable,
                    )
                    observation_buffer.append(entry)

                if chosen_sa.rank != 1 and adjustment_log_path is not None:
                    top_sa = ranked[0]
                    try:
                        reason = input(
                            f"Reason (why not [0] {top_sa.action.description}?): "
                        ).strip()
                    except (EOFError, KeyboardInterrupt):
                        reason = ""
                    _append_jsonl(adjustment_log_path, {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "seed": seed,
                        "step": step,
                        "chosen_rank": chosen_sa.rank,
                        "chosen_action": chosen_sa.action.description,
                        "chosen_score": chosen_sa.score,
                        "top_rank": 1,
                        "top_action": top_sa.action.description,
                        "top_score": top_sa.score,
                        "score_delta": chosen_sa.delta,
                        "user_reason": reason,
                        "all_scored": [
                            {
                                "rank": sa.rank,
                                "action": sa.action.description,
                                "score": sa.score,
                                "delta": sa.delta,
                                "reasons": sa.reasons,
                            }
                            for sa in ranked
                        ],
                        "state_snapshot": _state_snapshot(state),
                    })

                return chosen_sa.action
        except ValueError:
            pass
        print(f"Enter a number 0-{len(ranked)-1}, a command (n/m/i/r), or 'q'.")


def _build_manual_decision_entry(
    state: GameState,
    ranked: list,
    chosen_sa,
    chosen_idx: int,
    step: int,
    seed: int | None,
    notes: list,
    policy_trainable: bool,
) -> dict:
    top_sa = ranked[0]
    return {
        "entry_type": "manual_decision_snapshot",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "step": step,
        "policy_trainable": policy_trainable,
        "invalid_reason": None,
        "state": _state_snapshot(state),
        "ranked_actions": [
            {
                "index": i,
                "rank": sa.rank,
                "score": sa.score,
                "delta": sa.delta,
                "action_type": sa.action.action_type,
                "source_card": sa.action.source_card,
                "source_card_id": _card_id(sa.action.source_card),
                "description": sa.action.description,
                "target": sa.action.target,
                "alt_cost_type": sa.action.alt_cost_type,
                "risk_level": sa.action.risk_level,
            }
            for i, sa in enumerate(ranked)
        ],
        "policy_top_action": {
            "index": 0,
            "description": top_sa.action.description,
            "score": top_sa.score,
        },
        "chosen_action": {
            "index": chosen_idx,
            "rank": chosen_sa.rank,
            "score": chosen_sa.score,
            "delta": chosen_sa.delta,
            "description": chosen_sa.action.description,
        },
        "chosen_was_policy_top": chosen_sa.rank == 1,
        "manual_notes": notes,
    }


def _manual_session_save(buffer: list, log_path: Path | None) -> None:
    total = len(buffer)
    note_count = sum(len(e.get("manual_notes", [])) for e in buffer)
    bug_note_count = sum(
        1 for e in buffer
        if any(n.get("kind") in ("missing", "illegal", "resolution") for n in e.get("manual_notes", []))
    )
    trainable_count = sum(1 for e in buffer if e.get("policy_trainable", True))

    print(f"\n{'='*60}")
    print(f"Session: {total} decisions, {note_count} notes ({bug_note_count} bug-note steps), "
          f"{trainable_count}/{total} policy-trainable")

    if log_path is None:
        print("No manual-observation log path configured. Discarding session data.")
        return

    try:
        save = input(f"Save to {log_path}? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        save = "n"

    if save == "y":
        for entry in buffer:
            _append_jsonl(log_path, entry)
        print(f"Saved {total} entries to {log_path}")
    else:
        print("Session data discarded.")


def _append_jsonl(path: Path, entry: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _card_id(name: str | None) -> int | None:
    if name is None:
        return None
    cd = get_card(name)
    return cd.card_id if cd else None


def _snapshot_perm(p: Permanent) -> dict:
    return {
        "card_name": p.card_name,
        "card_id": _card_id(p.card_name),
        "perm_id": p.perm_id,
        "tapped": p.tapped,
        "counters": dict(p.counters),
        "imprinted_card": p.imprinted_card,
        "attached_to": p.attached_to,
    }


def _snapshot_stack_obj(o: StackObject) -> dict:
    return {
        "card_name": o.card_name,
        "card_id": _card_id(o.card_name),
        "stack_id": o.stack_id,
        "targets": list(o.targets),
        "target_names": list(o.target_names),
        "x_value": o.x_value,
        "alt_cost_used": o.alt_cost_used,
        "is_draw_trigger": o.is_draw_trigger,
        "draw_count": o.draw_count,
    }


def _state_snapshot(state: GameState) -> dict:
    return {
        "floating_mana": {
            "U": state.floating_mana.U,
            "R": state.floating_mana.R,
            "C": state.floating_mana.C,
            "ANY": state.floating_mana.ANY,
        },
        "hand": list(state.hand),
        "hand_ids": [_card_id(c) for c in state.hand],
        "library_ids": [_card_id(c) for c in state.library],
        "battlefield": [_snapshot_perm(p) for p in state.battlefield],
        "stack": [_snapshot_stack_obj(o) for o in state.stack],
        "graveyard": list(state.graveyard),
        "graveyard_ids": [_card_id(c) for c in state.graveyard],
        "exile": list(state.exile),
        "exile_ids": [_card_id(c) for c in state.exile],
        "pending_choices": [str(c) for c in state.pending_choices],
        "permissions": [str(p) for p in state.permissions],
        "pending_curiosity_draws": state.pending_curiosity_draws,
        "noncreature_spells_cast": state.noncreature_spells_cast,
        "total_cards_drawn": state.total_cards_drawn,
        "land_play_available": state.land_play_available,
        "vivi_available_as_creature_to_tap": state.vivi_available_as_creature_to_tap,
        "legendary_permanent_available": state.legendary_permanent_available,
        "virtue_of_courage_on_battlefield": state.virtue_of_courage_on_battlefield,
    }


# Keep for backward compatibility with any external callers.
def _write_adjustment_log(log_path: Path, entry: dict) -> None:
    _append_jsonl(log_path, entry)


def _brick(state: GameState, outcome: str, reason: str, step: int) -> RunResult:
    stranded = [
        c for c in state.hand
        if c not in ("Island", "Mountain")
    ]
    return RunResult(
        outcome=outcome,
        noncreature_spells_cast=state.noncreature_spells_cast,
        total_cards_drawn=state.total_cards_drawn,
        final_hand_size=len(state.hand),
        final_mana=state.floating_mana.copy(),
        brick_reason=reason,
        steps=step,
        trace=state.trace,
        stranded_cards=stranded,
    )


def _build_initial_state(config: RunConfig, active_deck: list[str], rng: Random) -> GameState:
    vivi = "Vivi Ornitier"
    remaining = [c for c in active_deck if c != vivi and c not in config.starting_hand]

    # Remove starting_battlefield cards from the library pool (zone consistency)
    for card_name in config.starting_battlefield:
        assert card_name in remaining, (
            f"starting_battlefield card '{card_name}' not found in active deck "
            f"(or conflicts with starting_hand / another starting_battlefield entry)"
        )
        remaining.remove(card_name)

    if config.library_order is not None:
        library = [c for c in config.library_order if c in remaining]
    else:
        library = remaining.copy()
        rng.shuffle(library)

    tapped_set = set(config.starting_battlefield_tapped)

    state = GameState(
        hand=list(config.starting_hand),
        library=library,
        floating_mana=config.starting_floating_mana.copy(),
        curiosity_effect_count=config.curiosity_effect_count,
        cards_drawn_per_noncreature_spell=OPPONENT_COUNT * config.curiosity_effect_count,
        land_play_available=config.land_play_available,
        vivi_on_battlefield=True,
        vivi_available_as_creature_to_tap=True,
        legendary_permanent_available=True,
        rng=rng,
        jeska_opponent_hand_size=config.jeska_opponent_hand_size,
        opponent_controls_island=config.opponent_controls_island,
    )

    # Vivi always starts on the battlefield
    state.battlefield.append(Permanent(card_name=vivi, tapped=False))

    # Place starting battlefield permanents (already removed from library above)
    for card_name in config.starting_battlefield:
        tapped = card_name in tapped_set
        state.battlefield.append(Permanent(card_name=card_name, tapped=tapped))

    return state
