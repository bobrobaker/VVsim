# Vivi Curiosity Chain Simulator: LLM Implementation Prompt

Build a Python simulator for a cEDH Magic: The Gathering deck. The simulator is not a full MTG rules engine. It is a focused single-turn spell-chain crawler for a deck built around Vivi Ornitier plus Curiosity-like effects.

## Goal

Given:
- Vivi already on battlefield.
- One or more Curiosity-like effects already active.
- A starting hand.
- A randomized or specified library.
- Some floating mana.
- All preexisting ordinary mana sources tapped out.

Simulate how long the deck can continue chaining noncreature spells before it bricks or wins.

Core loop:

```text
cast noncreature spell -> draw from Curiosity/Vivi -> use new cards/resources -> repeat
```

The simulator mostly models one turn exactly. Do not implement full turns, combat, opponents, full priority, or a complete MTG rules engine.

## Existing Inputs

Use a card-data CSV with one row per card. The CSV stores card facts only, not strategy labels.

Expected CSV columns:

```csv
card_id,name,mana_cost,mv,colors,pip_u,pip_r,generic_mana,x_in_cost,card_types,is_noncreature_spell,can_play_as_land,land_enters_tapped,land_mana_mode,land_limited_uses,alt_costs,produces_mana,mana_source_type,mana_colors,mana_amount,mana_timing,mana_condition,requires_tap,requires_sacrifice,requires_discard,requires_exile,requires_creature
```

The CSV should answer factual questions only:
- What is the card's cost?
- Is it a noncreature spell?
- Can it be played as a land?
- Can it produce mana?
- Does it have an alternate cost?

Do not put strategy labels in the CSV, such as combo_piece, tutor_target, protection, win_condition, good_to_cast, or bad_to_cast.

## Terminal Conditions

A run ends with one of these outcomes:

```python
WIN_EXTRA_TURN
WIN_NONCREATURE_SPELL_COUNT
BRICK_NO_ACTIONS
BRICK_NO_USEFUL_ACTIONS
ERROR_INVALID_STATE
```

### Win: Extra-turn spell cast

If one of these cards is successfully cast, the run wins immediately:

```python
EXTRA_TURN_WIN_CARDS = {
    "Alchemist's Gambit",
    "Final Fortune",
    "Last Chance",
    "Warrior's Oath",
}
```

The card must actually be castable and cast. Merely drawing it is not enough.

### Win: 40 noncreature spells

If 40 noncreature spells are cast, the run wins:

```python
NONCREATURE_SPELL_WIN_THRESHOLD = 40
```

Only noncreature spells count toward this threshold.

### Brick

Brick if no useful action can continue the chain. Common brick reasons:
- No castable noncreature spells.
- Insufficient mana.
- Mana exists but no useful spell exists.
- Spells exist but no valid targets exist.
- Only lands, creatures, or inert cards remain.

Record the brick reason.

## Architecture

Use these modules/concepts:

```text
Card Data
Game State
Mana Model
Stack Model
Action Model
Action Generator
Action Resolver
Card Behavior Registry
Greedy Policy
Runner
Trace / Metrics
```

Core principle:

```text
CSV stores card facts.
Behavior registry stores card-specific rules.
Action generator lists legal/useful actions.
Policy chooses actions.
Resolver mutates game state.
Runner advances the simulation.
Metrics explain results.
```

## GameState

Suggested structure:

```python
@dataclass
class GameState:
    hand: list[CardRef]
    library: list[CardRef]
    graveyard: list[CardRef]
    exile: list[CardRef]
    battlefield: list[Permanent]
    stack: list[StackObject]

    floating_mana: ManaPool

    curiosity_effect_count: int
    cards_drawn_per_noncreature_spell: int

    noncreature_spells_cast: int
    total_spells_cast: int

    land_play_available: bool

    vivi_on_battlefield: bool
    vivi_available_as_creature_to_tap: bool
    legendary_permanent_available: bool

    permissions: list[Permission]
    trace: list[ActionLog]
    rng: Random
```

Track explicit zones:

```text
hand, library, graveyard, exile, battlefield, stack
```

## Initial State

Default setup:

```text
Vivi on battlefield.
Curiosity effect count >= 1.
All preexisting ordinary mana sources tapped out.
Starting floating mana specified by config.
Starting hand specified by config.
Library = deck minus starting hand and battlefield assumptions, shuffled unless specified.
Before any player action, draw 3 from the initial Curiosity trigger.
```

If multiple Curiosity-like effects are active:

```python
cards_drawn_per_noncreature_spell = 3 * curiosity_effect_count
```

## Stack and Decision Windows

Do not implement full priority. Implement simplified decision windows.

Decision windows occur:
- After initial draw.
- After drawing cards.
- After casting a spell and putting it on stack.
- After resolving a stack object.
- After activating mana.
- After a tutor/search changes known cards.
- After a permanent enters and creates new actions.

Critical ordering for noncreature spells:

```text
pay costs -> put spell on stack -> trigger Curiosity/Vivi -> draw cards -> decision window while spell remains on stack -> eventually resolve or counter spell
```

This ordering is intentional. It allows this play pattern:

```text
cast a spell -> draw 3 -> draw counterspell -> counter the original spell while it is still on stack -> draw 3 again
```

## Spell Lifecycle

Default cast behavior:

```python
def cast_spell(state, card, cost, targets=None):
    pay_costs(state, cost)
    move card from hand to stack
    state.total_spells_cast += 1

    if card.is_noncreature_spell:
        state.noncreature_spells_cast += 1
        draw_cards(state, 3 * state.curiosity_effect_count)

    open_decision_window(state)
```

Resolving is separate:

```python
def resolve_stack_object(state, stack_object):
    apply_card_resolution_effect(state, stack_object)
    move_stack_object_to_final_zone(state, stack_object)
```

If the player counters their own spell:
- The original spell does not resolve.
- It moves to the correct final zone, usually graveyard.
- The counterspell itself may be a noncreature spell and trigger Curiosity.

## Reactive Spells and Targets

Reactive spells are castable only if they have valid targets. Do not create dummy opponent targets by default.

Examples:
- Force of Will requires a spell target.
- Pact of Negation requires a spell target.
- Swan Song requires an enchantment, instant, or sorcery spell target.
- Mental Misstep requires mana value 1 spell target.
- Disrupting Shoal can target a spell, but only counters if X matches mana value.
- Deflecting Swat requires a spell or ability with targets.
- Pyroblast requires an appropriate blue spell/permanent target depending on mode.

A spell may be cast even if its effect will fail or be irrelevant, as long as target conditions are valid.

For Deflecting Swat, distinguish:

```text
spell on stack
spell/ability on stack with targets
```

Only the second allows Deflecting Swat.

## Curiosity Effects

State tracks active Curiosity-like effects:

```python
state.curiosity_effect_count = 1
state.cards_drawn_per_noncreature_spell = 3 * state.curiosity_effect_count
```

When a noncreature spell is cast:

```python
draw_cards(state, 3 * state.curiosity_effect_count)
```

Cards that can increase curiosity_effect_count include:
- Tandem Lookout
- Curiosity
- Ophidian Eye

Creature spells do not trigger the noncreature loop, but some creatures still matter. Generate creature cast actions only when a registered behavior says they matter.

Example:
- Tandem Lookout can resolve and pair with Vivi, increasing future draw from 3 to 6.

## Mana Model

Use a simple real mana pool:

```python
@dataclass
class ManaPool:
    U: int = 0
    R: int = 0
    C: int = 0
    ANY: int = 0
```

Payment rules:
- U pips require U or ANY.
- R pips require R or ANY.
- Generic costs may be paid by U, R, C, or ANY.

The deck is Izzet, so v1 only needs U, R, C, and ANY.

Future extension: restricted mana, e.g. Cavern of Souls colored mana only for creature spells.

## Permanents

Use a simple permanent model:

```python
@dataclass
class Permanent:
    card: CardRef
    tapped: bool = False
    counters: dict[str, int] = field(default_factory=dict)
    imprinted_card: CardRef | None = None
    attached_to: CardRef | None = None
```

Preexisting mana sources start tapped. Newly cast or played mana sources may be usable.

Starting assumptions:

```python
state.vivi_on_battlefield = True
state.vivi_available_as_creature_to_tap = True
state.legendary_permanent_available = True
```

This matters for Mox Amber, Springleaf Drum, and Paradise Mantle.

## Action Model

Use explicit actions:

```python
@dataclass
class Action:
    action_type: str
    source_card: CardRef | None
    description: str
    costs: CostBundle
    effects: EffectBundle
    requires_target: bool = False
    target: TargetRef | None = None
    risk_level: str = "normal"
```

Action types:

```text
INITIAL_CURIOSITY_DRAW
CAST_SPELL
RESOLVE_STACK_OBJECT
COUNTER_STACK_OBJECT
PLAY_LAND
ACTIVATE_MANA_ABILITY
EXILE_FOR_MANA
SACRIFICE_FOR_MANA
IMPRINT
DISCARD_FOR_COST
TUTOR
CHOOSE_MODE
CREATE_PERMISSION
STOP
```

Not every action is a spell:
- Playing land does not trigger Curiosity.
- Activating Lotus Petal does not trigger Curiosity.
- Exiling Simian Spirit Guide does not trigger Curiosity.
- Casting Lotus Petal does trigger Curiosity because it is a noncreature spell.

## Action Generator

The action generator enumerates actions. It does not choose the best action.

```python
def generate_actions(state: GameState) -> list[Action]:
    actions = []
    actions += generate_stack_resolution_actions(state)
    actions += generate_cast_actions_from_hand(state)
    actions += generate_cast_actions_from_exile_permissions(state)
    actions += generate_land_play_actions(state)
    actions += generate_mana_actions(state)
    actions += generate_special_card_actions(state)
    return actions
```

Example actions:
- Cast Gitaxian Probe for free.
- Cast Force of Will by exiling a blue card, targeting a spell on stack.
- Resolve Rite of Flame.
- Play Sea Gate, Reborn as land.
- Tap newly cast Sol Ring.
- Exile Simian Spirit Guide for R.
- Cast Gamble.
- Cast Tandem Lookout if enough mana exists.

## Action Resolver

The resolver mutates state:

```python
def resolve_action(state: GameState, action: Action) -> GameState:
    pay_costs(state, action.costs)
    apply_effects(state, action.effects)
    update_zones(state, action)
    update_counts(state, action)
    log_action(state, action)
    return state
```

Keep casting and resolving separate so spells remain on stack long enough to be targeted.

## Card Behavior Registry

Use a registry for card-specific behavior. Do not encode all behavior in CSV.

Interface:

```python
class CardBehavior:
    def generate_actions(self, state: GameState, card: CardRef) -> list[Action]:
        return []

    def resolve_cast(self, state: GameState, stack_object: StackObject) -> None:
        pass

    def resolve_special_action(self, state: GameState, action: Action) -> None:
        pass
```

Registry example:

```python
CARD_BEHAVIORS = {
    "Rite of Flame": RiteOfFlameBehavior(),
    "Gamble": GambleBehavior(),
    "Mystical Tutor": MysticalTutorBehavior(),
    "Merchant Scroll": MerchantScrollBehavior(),
    "Intuition": IntuitionBehavior(),
    "Lion's Eye Diamond": LionsEyeDiamondBehavior(),
    "Chrome Mox": ChromeMoxBehavior(),
    "Mox Diamond": MoxDiamondBehavior(),
    "Tandem Lookout": TandemLookoutBehavior(),
    "Ophidian Eye": OphidianEyeBehavior(),
    "Curiosity": CuriosityBehavior(),
}
```

Default behavior:
- If card is castable, pay cost and put it on stack.
- If it is a noncreature spell, draw from Curiosity.
- Later resolve it normally.

Special behavior examples:
- Rite of Flame: on resolution, add RR, with optional graveyard scaling later.
- Gitaxian Probe: free alternate cost; on resolution, draw 1 if modeled.
- Gamble: tutor then random discard.
- Mystical Tutor: search instant/sorcery to top; immediate draws may draw it.
- Merchant Scroll: search blue instant to hand.
- Solve the Equation: search instant/sorcery to hand.
- Intuition: needs pile/opponent-choice approximation.
- Lion's Eye Diamond: sacrifice, discard hand, add three mana.
- Chrome Mox: imprint nonartifact nonland card, produce one color of imprinted card.
- Mox Diamond: discard land or fail/sacrifice.
- Tandem Lookout: if resolved and paired with Vivi, increase curiosity_effect_count.
- Ophidian Eye / Curiosity: if resolved on Vivi, increase curiosity_effect_count.

Implement behavior incrementally.

## Lands

Support one land play per run unless changed.

Land play does not trigger Curiosity.

MDFC lands are playable as lands according to CSV fields.

Life costs are ignored. Bolt lands and similar MDFCs may enter untapped unless CSV says otherwise.

Simplified fetch rule:

```text
Fetchlands can produce U or R after being played and sacrificed, assuming valid targets remain.
```

Exact fetch target tracking can be added later.

## Exile and Permissions

Cards in exile are inert unless there is an explicit permission or behavior.

Use permissions for effects that allow future actions:

```python
@dataclass
class Permission:
    card: CardRef
    zone: str
    action_type: str
    expires: str
    cost_modifier: CostModifier | None = None
```

Use this later for adventure, harmonize, cast-from-exile effects, etc.

For v1, only implement exile permissions when needed by a card behavior.

## Greedy Policy

Start with greedy policy, not full search.

```python
def choose_action(state: GameState, actions: list[Action]) -> Action | None:
    ...
```

Priority order:

```text
1. Cast extra-turn win spell if possible.
2. If noncreature spell count >= 40, win.
3. Consider resolving valuable stack objects.
4. If a spell is on stack, consider reactive spells that can target it and draw more cards.
5. Use safe mana actions that unlock castable noncreature spells.
6. Cast mana-positive noncreature spells.
7. Cast free or cheap noncreature spells.
8. Cast tutors/cantrips that improve chain continuation.
9. Cast engine-improving creatures/enchantments if they improve future draw rate.
10. Use risky resources only if otherwise bricked.
11. If no useful action exists, brick.
```

Do not always resolve the top stack object immediately. It may be useful as a target for reactive spells.

Risk categories:

```text
safe: tap Sol Ring, cast zero-mana artifact, play land
normal: cast cheap noncreature spell, cast tutor
expensive: spend scarce colored mana, pitch one card
risky: Chrome Mox imprint, Mox Diamond discard land, Gamble random discard
desperate: LED discard hand, Commandeer pitch two blue cards, counter own useful spell to continue
```

The policy should prefer lower-risk actions unless a risky action prevents a brick or wins.

## Creature Spells

Do not globally ignore creatures.

Rule:

```text
Generate creature cast actions only if the card has registered relevant behavior or enables a known line.
```

Relevant examples:
- Tandem Lookout can increase curiosity_effect_count.
- Imperial Recruiter may search for relevant creature.
- Simian Spirit Guide matters mainly as exile-for-mana.
- Ragavan probably has low relevance unless modeled specially.

## Randomness

Randomness sources:
- Library order.
- Gamble discard.
- Intuition approximation.
- Future stochastic choices.

Every run must have a seed.

```python
@dataclass
class RunConfig:
    seed: int
    starting_hand: list[str]
    starting_floating_mana: ManaPool
    library_order: list[str] | None
    curiosity_effect_count: int = 1
```

Trace must allow reproducing the run.

## Trace

Every run should produce a detailed trace.

```python
@dataclass
class ActionLog:
    step: int
    event_type: str
    action_description: str
    cards_drawn: list[str]
    mana_before: ManaPool
    mana_after: ManaPool
    hand_size_before: int
    hand_size_after: int
    noncreature_spells_cast: int
    stack_snapshot: list[str]
    notes: list[str]
```

Trace event types:

```text
INITIAL_DRAW
CAST_SPELL
DRAW_FROM_CURIOSITY
RESOLVE_SPELL
COUNTER_SPELL
PLAY_LAND
ACTIVATE_MANA
TUTOR
DISCARD
EXILE
BRICK
WIN
```

Trace quality matters. The simulator should explain why a run won or bricked.

## Metrics

For many runs, report:
- Win rate.
- Brick rate.
- Win by extra-turn spell rate.
- Win by 40 noncreature spells rate.
- Average cards drawn before terminal state.
- Median cards drawn before terminal state.
- Average noncreature spells cast.
- Average final hand size.
- Average final floating mana.
- Most common brick reasons.
- Most common winning cards.
- Most common stranded cards.
- Mana bottlenecks: U, R, generic, no target, no noncreature spell.
- Frequency of reaching second Curiosity effect.
- Frequency of casting reactive spells on own stack objects.

Useful deck-tuning KPIs:
- Bricks with cards in hand but no mana.
- Bricks with mana but no castable noncreature spell.
- Draws extra-turn spell but cannot cast it.
- Requires countering own spell to continue.
- Second Curiosity effect improves run.

## Implementation Phases

### v0.1 Minimal Chain

Implement:
- Load CSV.
- Build starting state.
- Shuffle library.
- Initial draw 3.
- Mana pool.
- Cast ordinary noncreature spells.
- Pay U/R/generic costs.
- Draw 3 on noncreature spell cast.
- Track noncreature spell count.
- Extra-turn win.
- 40 noncreature spell win.
- Brick detection.
- Basic trace.

### v0.2 Stack-Aware Casting

Add:
- Spells remain on stack after cast.
- Decision window before resolution.
- Resolve-stack-object actions.
- Reactive spells require valid targets.
- Countering own spells.

### v0.3 Mana Sources

Add behavior for:
- Sol Ring
- Mana Vault
- Grim Monolith
- Lotus Petal
- Lion's Eye Diamond
- Chrome Mox
- Mox Diamond
- Mox Opal
- Mox Amber
- Simian Spirit Guide
- Rite of Flame
- Strike It Rich
- Land plays
- MDFC lands
- Springleaf Drum
- Paradise Mantle

### v0.4 Draw/Tutor Effects

Add behavior for:
- Gitaxian Probe
- Twisted Image
- Repeal
- Gamble
- Mystical Tutor
- Merchant Scroll
- Solve the Equation
- Intuition
- Jeska's Will
- Vexing Bauble
- Baubles if relevant

### v0.5 Engine Enhancement

Add behavior for:
- Tandem Lookout
- Curiosity
- Ophidian Eye
- Other effects that increase curiosity_effect_count

### v0.6 Better Greedy Policy

Add:
- Risk-aware scoring.
- Target selection.
- Tutor target heuristics.
- Mana bottleneck awareness.
- Own-spell countering heuristics.
- Rules to avoid wasting critical cards.

## Suggested Project Structure

```text
mtg_sim/
  data/
    testdecklist.txt
    mtg_sim_card_data_v1.csv
  sim/
    card_data.py
    cards.py
    state.py
    mana.py
    stack.py
    actions.py
    action_generator.py
    resolver.py
    card_behaviors.py
    policies.py
    runner.py
    metrics.py
    trace.py
  scripts/
    run_single.py
    run_monte_carlo.py
    inspect_trace.py
  tests/
    test_mana_payment.py
    test_initial_draw.py
    test_cast_noncreature.py
    test_stack_targeting.py
    test_extra_turn_win.py
    test_basic_brick.py
```

## Non-Negotiable Modeling Choices

Preserve these:
- One-turn-focused simulator.
- Vivi starts on battlefield.
- Curiosity starts active.
- Initial event is draw 3.
- Noncreature spell casts trigger draw.
- Draw happens before spell resolves.
- Spells remain on stack long enough to be targeted.
- Reactive spells require valid targets.
- Only noncreature spells count toward 40-spell win.
- Extra-turn spells are immediate wins if cast.
- Creature spells are ignored by default unless behavior says they matter.
- Multiple Curiosity effects increase draw amount.
- Greedy policy is acceptable initially but must be replaceable.
