## Touchpoints
- `_FREE_MANA_SOURCES`, `_MANA_RITUALS` frozensets: ~20–28
- `_DEFAULTS` dict (all numeric weights): ~30; `_DEFAULT_TOML` path: ~20
- `load_policy_config(path=None)`: ~100 — lazy-loads TOML, caches by resolved path
- `ScoredAction` dataclass: ~130 — action, score, rank, delta, reasons
- `rank_actions(state, actions, cfg=None)`: ~140 — sorted ScoredAction list
- `score_action_with_reasons(state, action, cfg)`: ~195 — (float, list[str])
- `extract_features(state, action)`: sparse feature extraction for one legal action
- `feature_weights_from_config(cfg)`: adapts existing sectioned TOML/default config to flat feature weights
- `score_features(features, weights)`: weighted sparse sum; reason labels are nonzero contributing feature names
- `_TUTOR_PRIORITY` list: pending-choice priority order shared by tutor, imprint, and pitch features
- Feature predicate helpers: `_any_win_card_needs_red`, `_mana_enables_win_cast`, `_add_mana_color_features`, `_add_pitch_features`
- `_should_prioritize_mana_producer_resolution`: makes top-stack mana-producing spells outrank most actions

## Gotchas
- Cache is keyed by resolved path string; call `_clear_config_cache()` in tests that load different TOML files in the same process (conftest.py autouse fixture does this).
- `_mana_enables_new_cast` imports `generate_actions` but does not use it — kept from original to preserve import side-effects.
- Pitch spells have mana cost = 0 (CostBundle(pitched_card=…)); they get free_cost_bonus unless undone by pitch penalty logic.
- `policy.toml` overrides `_DEFAULTS` at runtime; always update **both** when adding new weight keys, or new keys will silently fall back to defaults and be shadowed by the old TOML.
- `resolve.mana_producer_priority` is intentionally below truly free Gitaxian Probe-style casts but above ordinary paid casts and mana activations.
- Policy scoring now flows through sparse features. Keep config compatibility by adding new mappings in `feature_weights_from_config`; do not bypass it with direct branch scoring in `score_action_with_reasons`.
- Reason strings are feature names, not legacy short labels. Tests/manual display should assert stable feature labels such as `card.noncreature`, `cost.free`, or `resolve.draw_trigger`.
- Pending-choice scoring is decomposed into provisional `choice.*` features that preserve the legacy helper score shapes; choice-policy redesign is still separate work.

## Recent changes
- 2026-05-07: Added pitch penalty (undoes free_cost_bonus + value-based penalty), free_mana_source_bonus, win-cast mana scoring, red-mana color bonuses, red_spend_penalty; refactored mana scoring to accumulate score + call `_apply_mana_color_bonuses`.
- 2026-05-07: Full refactor — extracted `score_action_with_reasons`, `ScoredAction`, `rank_actions`; all weights externalised to `mtg_sim/config/policy.toml`.
- 2026-05-09: Added `pending_draw_deferral_penalty` so non-win casts are deprioritized while a Curiosity draw trigger is top of stack; keep `_DEFAULTS` and `policy.toml` in sync for this key.
- 2026-05-10: Added `mana_producer_priority` for top-stack mana-producing spells so the policy usually resolves them before other actions, with free draw-spell casts still able to outrank them.
- 2026-05-10: Refactored policy scoring into sparse `extract_features` + `feature_weights_from_config` + `score_features`; existing TOML sections remain the public config surface through the adapter.
