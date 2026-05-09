## Touchpoints
- `_FREE_MANA_SOURCES`, `_MANA_RITUALS` frozensets: ~20–28
- `_DEFAULTS` dict (all numeric weights): ~30; `_DEFAULT_TOML` path: ~20
- `load_policy_config(path=None)`: ~100 — lazy-loads TOML, caches by resolved path
- `ScoredAction` dataclass: ~130 — action, score, rank, delta, reasons
- `rank_actions(state, actions, cfg=None)`: ~140 — sorted ScoredAction list
- `score_action_with_reasons(state, action, cfg)`: ~195 — (float, list[str])
- `_TUTOR_PRIORITY` list / `_score_imprint/discard/tutor`: near end of file
- New helpers: `_any_win_card_needs_red`, `_mana_enables_win_cast`, `_apply_mana_color_bonuses`, `_pitched_card_penalty_with_reason`

## Gotchas
- Cache is keyed by resolved path string; call `_clear_config_cache()` in tests that load different TOML files in the same process (conftest.py autouse fixture does this).
- `_mana_enables_new_cast` imports `generate_actions` but does not use it — kept from original to preserve import side-effects.
- Pitch spells have mana cost = 0 (CostBundle(pitched_card=…)); they get free_cost_bonus unless undone by pitch penalty logic.
- `policy.toml` overrides `_DEFAULTS` at runtime; always update **both** when adding new weight keys, or new keys will silently fall back to defaults and be shadowed by the old TOML.

## Recent changes
- 2026-05-07: Added pitch penalty (undoes free_cost_bonus + value-based penalty), free_mana_source_bonus, win-cast mana scoring, red-mana color bonuses, red_spend_penalty; refactored mana scoring to accumulate score + call `_apply_mana_color_bonuses`.
- 2026-05-07: Full refactor — extracted `score_action_with_reasons`, `ScoredAction`, `rank_actions`; all weights externalised to `mtg_sim/config/policy.toml`.
