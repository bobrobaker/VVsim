## Gotchas
- Grep fields before reading the file. `grep -n "field_name" state.py` answers field-existence questions in one line.
- Initial battlefield from `_build_initial_state` always includes a Volcanic Island. Tests asserting Mountain removal must account for this.

## Touchpoints
- `Permanent` dataclass: 14; `Permission`: 30; `PendingChoice`: 39
- `ActionLog`: 51; `GameState` dataclass: 66
- Key GameState methods: `pending_curiosity_draws`:116, `get_permanents_by_name`:123, `count_artifacts`:156, `has_untapped_creature`:160
- `validate_state`: 190

## Recent changes
