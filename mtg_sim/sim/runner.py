"""Main simulation runner."""
from __future__ import annotations
from dataclasses import dataclass, field
from random import Random
from pathlib import Path
from typing import Optional
from uuid import uuid4
from .mana import ManaPool
from .state import GameState, Permanent, ActionLog, OPPONENT_COUNT
from .actions import (
    WIN_EXTRA_TURN, WIN_NONCREATURE_SPELL_COUNT,
    BRICK_NO_ACTIONS, BRICK_NO_USEFUL_ACTIONS, ERROR_INVALID_STATE,
    NONCREATURE_SPELL_WIN_THRESHOLD,
)
from .card_behaviors import CARD_BEHAVIORS
from .action_generator import generate_actions
from .resolver import resolve_action, draw_cards
from .policies import choose_action, rank_actions, load_policy_config
from .observations import (
    append_jsonl,
    build_manual_decision_entry,
    build_policy_adjustment_entry,
    snapshot_state,
)

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
    manual_session_id = str(uuid4()) if config.manual_mode else None
    # Tracks whether a `resolution` bug note was filed; taints all subsequent snapshots.
    taint_state: dict = {"tainted": False}

    result = _simulate_loop(config, state, cfg, obs_buffer, taint_state, manual_session_id)

    if config.manual_mode and obs_buffer:
        _manual_session_save(obs_buffer, config.manual_observation_log_path)

    return result


def _simulate_loop(
    config: RunConfig,
    state: GameState,
    cfg: dict | None,
    obs_buffer: list,
    taint_state: dict,
    manual_session_id: str | None,
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
                session_id=manual_session_id,
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
    for obj in state.stack:
        beh = CARD_BEHAVIORS.get(obj.card_name)
        if not beh:
            continue
        outcome, winning_card = beh.check_win(state, obj.card_name)
        if outcome:
            return outcome, winning_card
    if state.noncreature_spells_cast >= NONCREATURE_SPELL_WIN_THRESHOLD:
        return WIN_NONCREATURE_SPELL_COUNT, f"{state.noncreature_spells_cast} spells"
    checked_battlefield_cards = {p.card_name for p in state.battlefield}
    for card_name in checked_battlefield_cards:
        beh = CARD_BEHAVIORS.get(card_name)
        if not beh:
            continue
        outcome, winning_card = beh.check_win(state, card_name)
        if outcome:
            return outcome, winning_card
    return "", ""


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
    session_id: str | None = None,
) -> Optional:
    """Present ranked actions to the user and return their choice, or None to brick.

    Displays policy score, rank, and delta for each action (no reason labels).
    Supports commands: n/note, m/missing, i/illegal, d/dominated,
    r/resolution, q/quit.
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
    print("  [ n] Note  [ m] Missing action  [ i] Illegal action  [ d] Dominated action  [ r] Resolution bug  [ q] Quit")

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

        if cmd in ("d", "dominated", "dominated_action"):
            try:
                idx_str = input("Dominated action index: ").strip()
                note_text = input("Note: ").strip()
            except (EOFError, KeyboardInterrupt):
                idx_str, note_text = "", ""
            try:
                dominated_idx = int(idx_str)
            except ValueError:
                dominated_idx = None
            notes.append({
                "kind": "dominated_action",
                "action_index": dominated_idx,
                "text": note_text,
                "policy_trainable": True,
            })
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
                    entry = build_manual_decision_entry(
                        state=state,
                        ranked=ranked,
                        chosen_sa=chosen_sa,
                        chosen_idx=idx,
                        step=step,
                        seed=seed,
                        session_id=session_id,
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
                    append_jsonl(
                        adjustment_log_path,
                        build_policy_adjustment_entry(
                            state=state,
                            ranked=ranked,
                            chosen_sa=chosen_sa,
                            top_sa=top_sa,
                            step=step,
                            seed=seed,
                            session_id=session_id,
                            reason=reason,
                        ),
                    )

                return chosen_sa.action
        except ValueError:
            pass
        print(f"Enter a number 0-{len(ranked)-1}, a command (n/m/i/d/r), or 'q'.")


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
            append_jsonl(log_path, entry)
        print(f"Saved {total} entries to {log_path}")
    else:
        print("Session data discarded.")


# Keep for backward compatibility with any external callers.
def _write_adjustment_log(log_path: Path, entry: dict) -> None:
    append_jsonl(log_path, entry)


# Keep for backward compatibility with any external callers.
_append_jsonl = append_jsonl
_state_snapshot = snapshot_state
_build_manual_decision_entry = build_manual_decision_entry


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
