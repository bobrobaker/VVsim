# Card Specifics

Purpose: compact source of truth for card-specific simulator behavior. Each card appears in exactly one bucket. Keep entries brief and implementation-oriented.

Checksum: expected card entries = 99 non-commander deck cards; current card entries = 99. Do not count the `Intake New Cards` placeholder.

## Terminators

Bucket logic: these cards or battlefield states terminate the sim successfully. Tests should verify both the enabling action/state and the win result.

Bucket tests: extra-turn spells win once cast/on stack; Hullbreaker and Quicksilver wins are checked from battlefield state; noncreature terminator casts still create normal Curiosity/Vivi draw triggers before the run ends if current architecture records them.

### Alchemist's Gambit
Action gen: default.
Resolution: Terminator; wins once cast/on stack.
Tests: payable hand state generates cast action; casting produces WIN_EXTRA_TURN.
Comments: "Cleave cost not implemented; not relevant for current sim."

### Final Fortune
Action gen: default.
Resolution: Terminator; wins once cast/on stack.
Tests: payable hand state generates cast action; casting produces WIN_EXTRA_TURN.
Comments: "Delayed lose-the-game trigger ignored."

### Hullbreaker Horror
Action gen: flash speed.
Resolution: enters battlefield; wins if any later spell is placed on stack while two eligible bounce permanents exist: nonland, nontoken, reusable, non-sacrifice mana sources, mana-neutral-or-better.
Tests: flash cast at instant speed; resolves to battlefield; later spell wins with two eligible permanents; no win with one/zero eligible permanents, lands, tokens, or sacrifice-only sources.
Comments: "Can win the game in slightly more flexible circumstances."

### Last Chance
Action gen: default.
Resolution: Terminator; wins once cast/on stack.
Tests: payable hand state generates cast action; casting produces WIN_EXTRA_TURN.
Comments: "Delayed lose-the-game trigger ignored."

### Quicksilver Elemental
Action gen: default.
Resolution: enters battlefield; wins if Quicksilver Elemental is on battlefield and at least one blue mana is floating.
Tests: generated as normal creature cast when payable; resolves to battlefield; wins with Quicksilver Elemental on battlefield plus `{U}` floating; no win without `{U}` floating.
Comments: "Activated ability details not modeled; simulator treats `{U}` available with Quicksilver Elemental as deterministic win."

### Warrior's Oath
Action gen: default.
Resolution: Terminator; wins once cast/on stack.
Tests: payable hand state generates cast action; casting produces WIN_EXTRA_TURN.
Comments: "Delayed lose-the-game trigger ignored."

## Fetchlands

Bucket logic: fetchlands change library composition, so model activation as tutoring a land to battlefield, not direct mana production.

Bucket tests: activation sacrifices fetchland; removes fetched card from library; puts fetched card onto battlefield; prefers Volcanic Island, then Steam Vents, then basic Island/Mountain if legal; fails or generates no action if no legal fetch target exists; cannot reuse after sacrifice.

### Arid Mesa
Action gen: fetchland-mountain.
Resolution: fetch priority Volcanic Island > Steam Vents > Mountain.
Tests: covered by bucket tests.
Comments: "Fetch/shuffle modeled as deterministic priority tutor."

### Bloodstained Mire
Action gen: fetchland-mountain.
Resolution: fetch priority Volcanic Island > Steam Vents > Mountain.
Tests: covered by bucket tests.
Comments: "Fetch/shuffle modeled as deterministic priority tutor."

### Flooded Strand
Action gen: fetchland-island.
Resolution: fetch priority Volcanic Island > Steam Vents > Island.
Tests: covered by bucket tests.
Comments: "Fetch/shuffle modeled as deterministic priority tutor."

### Misty Rainforest
Action gen: fetchland-island.
Resolution: fetch priority Volcanic Island > Steam Vents > Island.
Tests: covered by bucket tests.
Comments: "Fetch/shuffle modeled as deterministic priority tutor."

### Polluted Delta
Action gen: fetchland-island.
Resolution: fetch priority Volcanic Island > Steam Vents > Island.
Tests: covered by bucket tests.
Comments: "Fetch/shuffle modeled as deterministic priority tutor."

### Prismatic Vista
Action gen: fetchland-basics.
Resolution: fetch priority Island or Mountain by chosen action.
Tests: covered by bucket tests.
Comments: "Fetch/shuffle modeled as deterministic basic-land tutor."

### Scalding Tarn
Action gen: fetchland-island/mountain.
Resolution: fetch priority Volcanic Island > Steam Vents > chosen basic Island/Mountain.
Tests: covered by bucket tests.
Comments: "Fetch/shuffle modeled as deterministic priority tutor."

### Wooded Foothills
Action gen: fetchland-mountain.
Resolution: fetch priority Volcanic Island > Steam Vents > Mountain.
Tests: covered by bucket tests.
Comments: "Fetch/shuffle modeled as deterministic priority tutor."

## MDFC Lands

Bucket logic: MDFC spell faces use their card-specific spell behavior; land faces are simplified as untapped lands producing their listed color.

Bucket tests: MDFC can be played as land; land face enters untapped; land face taps for correct color; spell face and land face are generated as separate legal actions when appropriate.

Comments: "Skip lifeloss."

### Hydroelectric Specimen / Hydroelectric Laboratory
Action gen: default creature cast or MDFC blue land.
Resolution: creature enters battlefield and creates a targeted ETB ability on stack; land enters untapped and taps for `{U}`.
Tests: creature creates targeted ETB stack object that enables Deflecting Swat; land enters untapped and taps for U.
Comments: "Skip lifeloss; ETB effect modeled mainly to create targetable stack context."

### Pinnacle Monk / Mystic Peak
Action gen: default creature cast or MDFC red land.
Resolution: creature enters battlefield, then creates pending graveyard-choice for target instant/sorcery to return to hand; land enters untapped and taps for `{R}`.
Tests: creature enters battlefield; ETB creates pending choice from graveyard instant/sorcery targets; manual mode can choose target; policy can rank choices using tutor-style value; chosen card returns to hand; no choice if no legal target; land enters untapped and taps for R.
Comments: "Skip lifeloss."

### Sea Gate Restoration / Sea Gate, Reborn
Action gen: sorcery speed spell or MDFC blue land.
Resolution: spell draws cards equal to hand size plus one; land enters untapped and taps for `{U}`.
Tests: spell draw count uses current hand size; land enters untapped and taps for U.
Comments: "Skip lifeloss; no maximum hand size ignored."

### Shatterskull Smashing / Shatterskull, the Hammer Pass
Action gen: sorcery speed X=0 spell costing `{R}{R}`, or MDFC red land.
Resolution: default spell behavior; land enters untapped and taps for `{R}`.
Tests: only X=0 spell action needed; spell follows default resolution; land enters untapped and taps for R.
Comments: "Skip lifeloss; damage mode ignored."

### Sink into Stupor / Soporific Springs
Action gen: instant speed spell targeting dummy opponent permanent, or MDFC blue land.
Resolution: spell removes/ignores dummy opponent permanent; land enters untapped and taps for `{U}`.
Tests: spell requires dummy opponent permanent target; land enters untapped and taps for U.
Comments: "Skip lifeloss; owner-library placement simplified away."

### Sundering Eruption / Volcanic Fissure
Action gen: sorcery speed spell targeting dummy opponent land, or MDFC red land.
Resolution: spell removes/ignores dummy opponent land; land enters untapped and taps for `{R}`.
Tests: spell requires dummy opponent land target; land enters untapped and taps for R.
Comments: "Skip lifeloss; land destruction only modeled against dummy target."

## Other Lands

Bucket logic: non-fetch, non-MDFC lands. Model relevant mana abilities and type choices; ignore life loss unless explicitly stated otherwise.

Bucket tests: land plays use land-play availability; lands enter with correct tapped/untapped state; mana actions respect tapped state; subtype/basic-type flags work for Island/Mountain checks.

### Ancient Tomb
Action gen: land play; tap for `{C}{C}`.
Resolution: enters untapped.
Tests: playable as land; taps once for two colorless; cannot tap while tapped.
Comments: "Life loss ignored."

### Cavern of Souls
Action gen: land play; tap for `{C}` or restricted colored mana for creature spells.
Resolution: enters untapped.
Tests: playable as land; colorless mana works generally; colored mana can pay creature spells; colored mana cannot pay noncreature spells.
Comments: "Creature type choice simplified to support relevant creatures."

### Fiery Islet
Action gen: land play; tap for `{U}`/`{R}`; if untapped on battlefield, pay 1, tap, sac: draw 1.
Resolution: enters untapped; mana ability adds chosen mana; draw ability moves Fiery Islet to graveyard and draws 1.
Tests: taps for U/R; cannot use abilities tapped; draw ability requires 1 mana; sacrifice draws 1 and prevents reuse.
Comments: "Damage from mana ability ignored."

### Gemstone Caverns
Action gen: land play; if pregame luck counter modeled, tap for any color; otherwise tap for `{C}`.
Resolution: enters untapped.
Tests: playable as land; initial-state luck counter produces U/R/C; no luck counter produces only colorless; exiled setup card is not in library/hand.
Comments: "Pregame exile/luck-counter setup may be modeled through initial state."

### Island
Action gen: land play; tap for `{U}`.
Resolution: enters untapped.
Tests: playable as land; taps for U; cannot tap while tapped; counts as basic Island.

### Mountain
Action gen: land play; tap for `{R}`.
Resolution: enters untapped.
Tests: playable as land; taps for R; cannot tap while tapped; counts as basic Mountain.

### Multiversal Passage
Action gen: land play; choose basic type Island or Mountain; tap for chosen type's mana.
Resolution: enters untapped; creates pending choice to mark as Island or Mountain.
Tests: playable as land; pending basic-type choice generated; chosen type persists on permanent; chosen Island taps for U and counts for Island checks; chosen Mountain taps for R and counts for Mountain checks.
Comments: "Type choice compressed to Island/Mountain because only those basics matter."

### Sandstone Needle
Action gen: land play; tapped depletion land; tap/remove counter for `{R}{R}`.
Resolution: enters tapped with two depletion counters.
Tests: enters tapped; cannot tap while tapped; produces RR and loses counter when untapped; unusable after counters gone.

### Saprazzan Skerry
Action gen: land play; tapped depletion land; tap/remove counter for `{U}{U}`.
Resolution: enters tapped with two depletion counters.
Tests: enters tapped; cannot tap while tapped; produces UU and loses counter when untapped; unusable after counters gone.

### Steam Vents
Action gen: land play; tap for `{U}` or `{R}`.
Resolution: enters untapped.
Tests: playable as land; taps for U/R; counts as Island and Mountain.
Comments: "Skip lifeloss."

### Thran Portal
Action gen: land play; choose basic type Island or Mountain; tap for chosen type's mana.
Resolution: enters untapped; creates pending choice to mark as Island or Mountain.
Tests: playable as land; pending basic-type choice generated; chosen type persists on permanent; chosen Island taps for U and counts for Island checks; chosen Mountain taps for R and counts for Mountain checks.
Comments: "Type choice compressed to Island/Mountain; skip lifeloss."

### Thundering Falls
Action gen: land play; tap for `{U}` or `{R}`.
Resolution: enters tapped.
Tests: playable as land; enters tapped; later taps for U/R; counts as Island and Mountain.

### Volcanic Island
Action gen: land play; tap for `{U}` or `{R}`.
Resolution: enters untapped.
Tests: playable as land; taps for U/R; counts as Island and Mountain.

## Tutors

Bucket logic: tutor effects create pending choices. Preferred targets are ordering hints for manual/policy, not hard restrictions. If no preferred target is available, offer the next legal target in library order.

Bucket tests: creates pending tutor choice; applies correct filter/MV; preferred available targets appear first; unavailable preferred targets skipped; fallback legal target works; chosen card moves to correct zone.

### Dizzy Spell
Action gen: instant spell mode targeting creature; or tutor at sorcery speed for MV=1 card.
Resolution: spell mode no modeled effect; tutor mode discards Dizzy Spell and puts chosen MV=1 card into hand.
Preferred tutor targets: Gitaxian Probe, Twisted Image, Sol Ring, Mana Vault, Rite of Flame.
Tests: creature target required for spell mode; tutor only with empty stack; tutors MV=1 only; preferred targets first.
Comments: "Power reduction ignored."

### Drift of Phantasms
Action gen: default creature cast; or tutor at sorcery speed for MV=3 card.
Resolution: creature enters battlefield; tutor mode discards Drift and puts chosen MV=3 card into hand.
Preferred tutor targets: Alchemist's Gambit, Final Fortune, Last Chance, Warrior's Oath, Jeska's Will, Intuition, Solve the Equation, Snapback, Tandem Lookout.
Tests: normal cast enters battlefield; tutor only with empty stack; tutors MV=3 only; preferred targets first.
Comments: "Creature keywords ignored."

### Gamble
Action gen: sorcery speed.
Resolution: tutor any card to hand, then discard random card from hand.
Preferred tutor targets: Final Fortune, Last Chance, Warrior's Oath, Lotus Petal, Jeska's Will.
Tests: creates any-card tutor choice; chosen card enters hand before random discard; random discard can discard tutored card.
Comments: "Random discard modeled using seeded RNG."

### Imperial Recruiter
Action gen: default creature cast.
Resolution: enters battlefield; tutor creature with power 2 or less to hand.
Preferred tutor targets: Simian Spirit Guide, Ragavan, Nimble Pilferer, Tandem Lookout.
Tests: resolves to battlefield; creates creature tutor choice; only legal power<=2 creatures offered; preferred targets first.

### Intuition
Action gen: instant speed.
Resolution: choose one preferred mana-positive card to hand and put two other available preferred mana-positive cards into graveyard.
Preferred tutor targets: Chrome Mox, Lion's Eye Diamond, Lotus Petal, Mox Amber, Mox Diamond, Mox Opal.
Tests: instant-speed action generated; chosen card enters hand; two available preferred alternatives go to graveyard.
Comments: "Opponent pile/choice simplified to deterministic mana-positive package."

### Invert / Invent
Action gen: instant speed; either Invert mode with legal target or Invent mode.
Resolution: Invert no modeled effect; Invent tutors one instant and one sorcery to hand.
Preferred tutor targets: instant = Snapback, Force of Will, Fierce Guardianship, Intuition, Mystical Tutor; sorcery = Final Fortune, Last Chance, Warrior's Oath, Jeska's Will, Solve the Equation, Gamble, Rite of Flame.
Tests: both modes are instant speed; Invent creates instant tutor and sorcery tutor choices; chosen cards enter hand; preferred targets first.
Comments: "Invert effect ignored."

### Merchant Scroll
Action gen: sorcery speed.
Resolution: tutor blue instant to hand.
Preferred tutor targets: Intuition, Snapback, Force of Will, Fierce Guardianship, Mystical Tutor.
Tests: creates blue-instant tutor choice; nonblue/noninstant cards illegal; preferred targets first.

### Mystical Tutor
Action gen: instant speed.
Resolution: tutor instant or sorcery to top of library.
Preferred tutor targets: Final Fortune, Last Chance, Warrior's Oath, Jeska's Will, Intuition, Solve the Equation, Gamble, Gitaxian Probe.
Tests: creates instant/sorcery tutor choice; chosen card placed on top, not hand; preferred targets first.
Comments: "Topdeck tutor is relevant because Curiosity draws can immediately access it."

### Solve the Equation
Action gen: sorcery speed.
Resolution: tutor instant or sorcery to hand.
Preferred tutor targets: Final Fortune, Last Chance, Warrior's Oath, Jeska's Will, Intuition, Gamble, Gitaxian Probe, Snapback.
Tests: creates instant/sorcery tutor choice; chosen card enters hand; preferred targets first.

## Counterspells and Stack Interaction

Bucket logic: stack interaction needs target legality, alternate/free casting, and correct resolution on stack objects.

Bucket tests: legal stack targets only; own spells can be targeted where legal; pitched cards are exiled; countered spells leave stack to correct zone; no Curiosity trigger from copied/noncast effects.

### An Offer You Can't Refuse
Action gen: instant speed; target noncreature spell on stack, including own spells.
Resolution: counter target; if target was own spell, create two Treasure tokens.
Tests: generates only noncreature stack targets; counters target; own target creates two Treasures; creature target illegal.
Comments: "Opponent Treasure creation is ignored."

### Commandeer
Action gen: instant speed; normal cast or pitch two blue cards; target noncreature spell.
Resolution: gain control of target spell; for own spell, no modeled effect and target remains on stack.
Tests: generates normal/pitch actions; requires two distinct blue pitches; pitched cards exiled; own target is not countered/removed.
Comments: "Control-changing of opponent spells is ignored; own targets remain on stack."

### Daze
Action gen: instant speed; target spell; normal cast or return untapped Island-source to hand.
Resolution: pending pay `{1}` choice if targeting own spell; if unpaid, counter target.
Tests: generates normal/alternate actions; alternate returns Island-source; own target can pay `{1}` to survive; unpaid target is countered.
Comments: "Tax payment matters because sim often Dazes its own spell to trigger draws."

### Deflecting Swat
Action gen: instant speed; target spell/ability with target; free if commander controlled.
Resolution: target-changing has no modeled effect.
Tests: generates free action with Vivi; requires targeted stack object/ability; no action without legal target; resolves without removing target.
Comments: "Target-changing is ignored for this sim."

### Disrupting Shoal
Action gen: instant speed; target spell; normal X-cost or pitch blue card where pitched MV sets X.
Resolution: counter target only if target MV equals X.
Tests: generates normal X actions; generates pitch-blue actions; pitched card exiled; counters matching MV; fails on mismatched MV.
Comments: "X from pitch is modeled because it determines counter legality."

### Fierce Guardianship
Action gen: instant speed; target noncreature spell; free if commander controlled.
Resolution: counter target.
Tests: generates free action with Vivi; generates paid action if payable; only targets noncreature spells; countered target leaves stack.
Comments: "Commander-free mode is the important sim behavior."

### Flusterstorm
Action gen: instant speed; target instant/sorcery spell.
Resolution: counter target.
Tests: only targets instant/sorcery stack objects; target removed from stack; creature/permanent spell target illegal.
Comments: "Storm copies and tax payment ignored."

### Force of Will
Action gen: instant speed; target spell; normal cast or pitch blue card.
Resolution: counter target spell.
Tests: generates normal/pitch actions; pitch requires blue card; pitched card exiled; target removed from stack.
Comments: "One life loss ignored."

### Mental Misstep
Action gen: instant speed; target MV=1 spell; normal phyrexian-blue cost or free life-cost mode.
Resolution: counter target spell.
Tests: targets only MV=1 stack objects; generates free cast; target removed from stack; non-MV=1 target illegal.
Comments: "Life payment ignored."

### Misdirection
Action gen: instant speed; target spell with exactly one target; normal cast or pitch blue card.
Resolution: target-changing has no modeled effect.
Tests: generates normal/pitch actions; pitch requires blue card; pitched card exiled; only single-target stack objects legal.
Comments: "Target-changing is ignored for this sim; action mainly provides free spell/draw trigger."

### Pact of Negation
Action gen: instant speed; target spell; free cast.
Resolution: counter target spell.
Tests: generates with legal stack target; target removed from stack; no mana required.
Comments: "Delayed upkeep payment ignored."

### Pyroblast
Action gen: instant speed; target blue spell on stack or blue permanent.
Resolution: counter blue spell or destroy blue permanent.
Tests: targets only blue spell/permanent; counter mode removes stack target; destroy mode removes permanent; nonblue target illegal.

### Swan Song
Action gen: instant speed; target enchantment, instant, or sorcery spell.
Resolution: counter target spell.
Tests: targets only enchantment/instant/sorcery stack objects; target removed from stack.
Comments: "Opponent Bird token ignored."

## Nonland Mana Sources

Bucket logic: nonland cards whose primary modeled role is making mana, producing mana permanents, or enabling mana abilities.

Bucket tests: permanents enter battlefield; mana actions respect tapped/sacrifice/exile state; mana colors are restricted to sim colors; one-shot sources cannot be reused.

### Chrome Mox
Action gen: default cast; pending imprint choice after entering battlefield.
Resolution: enters battlefield; choose imprint nonartifact nonland colored card or no imprint; taps for imprinted card color.
Tests: pending imprint generated; eligible imprint exiled; no-imprint allowed; taps only after imprint; no colorless from imprint.
Comments: "Imprint choice is modeled as pending choice."

### Grim Monolith
Action gen: default cast; tap for `{C}{C}{C}` while untapped.
Resolution: enters battlefield.
Tests: resolves to battlefield; taps for 3 colorless; cannot tap while tapped.
Comments: "Untap ability not modeled."

### Jeweled Amulet
Action gen: default cast; if charged, tap/remove charge to add stored mana.
Resolution: enters battlefield.
Tests: resolves to battlefield; no mana action without charge; charged amulet produces stored color once.
Comments: "Charging ability not modeled unless initial state provides charge."

### Lion's Eye Diamond
Action gen: default cast; tap/sac/discard hand for three mana of chosen color.
Resolution: enters battlefield; activation sacrifices LED, discards hand, adds chosen mana.
Tests: resolves to battlefield; activation discards hand; adds three chosen mana; LED goes to graveyard and cannot reuse.

### Lotus Petal
Action gen: default cast; sacrifice for `{U}`, `{R}`, or `{C}`.
Resolution: enters battlefield; activation sacrifices Lotus Petal and adds chosen mana.
Tests: resolves to battlefield; activation produces chosen mana; Petal goes to graveyard; cannot reuse after sacrifice.

### Mana Vault
Action gen: default cast; tap for `{C}{C}{C}`.
Resolution: enters battlefield.
Tests: resolves to battlefield; taps for 3 colorless; cannot tap while tapped.
Comments: "Untap and damage abilities ignored."

### Mox Amber
Action gen: default cast; tap for `{U}` or `{R}` if Vivi/legendary permanent controlled.
Resolution: enters battlefield.
Tests: resolves to battlefield; produces U/R with Vivi; produces no mana without legendary permanent; cannot tap while tapped.

### Mox Diamond
Action gen: default cast; pending discard-land choice after entering battlefield.
Resolution: enters battlefield; discard a land or sacrifice Mox Diamond; taps for `{U}`, `{R}`, or `{C}` after successful discard.
Tests: pending discard generated; discarded land moves to graveyard; no-land choice sacrifices Mox; successful Mox taps once for chosen mana.
Comments: "Any-color mana restricted to sim colors."

### Mox Opal
Action gen: default cast; tap for `{U}`, `{R}`, or `{C}` if metalcraft.
Resolution: enters battlefield.
Tests: resolves to battlefield; produces mana only with 3+ artifacts; cannot produce before metalcraft; cannot tap while tapped.
Comments: "Any-color mana restricted to sim colors."

### Paradise Mantle
Action gen: default cast; sorcery-speed equip ability targeting Vivi; equipped Vivi gains instant-speed tap for `{U}` or `{R}`.
Resolution: enters battlefield; equip attaches to Vivi.
Tests: resolves to battlefield; equip action targets Vivi only; equip only at sorcery speed; equipped Vivi can tap for U/R at instant speed; cannot use if Vivi already tapped.
Comments: "Only equips to Vivi; other creatures likely have summoning sickness."

### Ragavan, Nimble Pilferer
Action gen: default creature cast.
Resolution: enters battlefield.
Tests: resolves to battlefield; counts as creature for Springleaf Drum/convoke/equipment; no immediate spell/draw trigger.
Comments: "Combat damage and Treasure trigger ignored."

### Rite of Flame
Action gen: sorcery speed.
Resolution: add `{R}{R}`.
Tests: cast when payable; resolution adds RR.
Comments: "Graveyard bonus ignored."

### Simian Spirit Guide
Action gen: instant speed; exile from hand for `{R}`.
Resolution: move Simian Spirit Guide from hand to exile and add `{R}`.
Tests: instant-speed action generated from hand; adds R; card moves to exile; cannot reuse.

### Sol Ring
Action gen: default cast; tap for `{C}{C}`.
Resolution: enters battlefield.
Tests: resolves to battlefield; taps for 2 colorless; cannot tap while tapped.

### Springleaf Drum
Action gen: default cast; tap plus untapped creature for `{U}`, `{R}`, or `{C}`.
Resolution: enters battlefield.
Tests: resolves to battlefield; mana action requires untapped creature; taps Drum and chosen creature; produces chosen mana.
Comments: "Any-color mana restricted to sim colors."

### Strike It Rich
Action gen: sorcery speed; or flashback from graveyard.
Resolution: create Treasure token.
Tests: normal cast creates Treasure; flashback cast creates Treasure and exiles card on resolution; Treasure sacrifices for sim color.

## Draw and Cast-Permission Engines

Bucket logic: cards that alter draw count, create extra draw/exile triggers, or create temporary cast permissions.

Bucket tests: engine state is created on resolution; later noncreature casts trigger the correct extra effect; permissions do not incorrectly enable pitch/adventure modes.

### Curiosity
Action gen: default; target Vivi.
Resolution: enters battlefield; increase Curiosity effect count by 1.
Tests: generates only when Vivi target exists; resolves to battlefield; later noncreature spells draw one additional card per opponent.
Comments: "Always modeled as enchanting Vivi."

### Jeska's Will
Action gen: sorcery speed.
Resolution: add red equal to configured opponent hand size; exile top 3 with temporary permission to cast those cards this turn.
Tests: adds configured red; exiles up to 3; exiled castable spells generate cast-from-exile actions; exiled lands not castable; exiled cards cannot be used as pitch cards; Virtue of Courage exiled this way cannot cast adventure side.
Comments: "Both modes assumed available because commander is controlled."

### Gitaxian Probe
Action gen: sorcery speed; normal blue cost or free life-cost mode.
Resolution: draw 1.
Tests: generates free cast; increments noncreature count/Curiosity trigger; resolution draws 1.
Comments: "Life payment and opponent hand info ignored."

### Niv-Mizzet, Visionary
Action gen: default creature cast.
Resolution: enters battlefield; modeled as one additional Curiosity-like draw effect.
Tests: resolves to battlefield; increments draw count like another Curiosity effect; later noncreature spell draws one additional card per opponent; creature spells do not trigger.
Comments: "Full printed trigger details simplified to Curiosity-like draw engine."

### Ophidian Eye
Action gen: flash speed; target Vivi.
Resolution: enters battlefield; increase Curiosity effect count by 1.
Tests: generated at instant speed; requires Vivi target; resolves to battlefield; later noncreature spells draw one additional card per opponent.
Comments: "Always modeled as enchanting Vivi."

### Tandem Lookout
Action gen: default creature cast.
Resolution: enters battlefield; if Vivi exists, increase Curiosity effect count by 1.
Tests: resolves to battlefield; increments draw count with Vivi; later noncreature spell draws one additional card per opponent.
Comments: "Soulbond simplified to always pair with Vivi."

### Virtue of Courage / Embereth Blaze
Action gen: enchantment cast, or instant-speed Embereth Blaze adventure targeting legal target.
Resolution: Virtue enters battlefield; when Vivi damages each opponent from a noncreature cast, exile top 3 with temporary cast permission. Embereth Blaze resolves to exile with permission to cast Virtue.
Tests: adventure cast exiles card with Virtue permission; Virtue can be cast from adventure exile; noncreature cast with Vivi+Virtue exiles top 3; exiled cards are castable this turn; Jeska-exiled Virtue cannot cast adventure side.
Comments: "Embereth Blaze damage ignored; Virtue trigger is modeled through Vivi damage to opponents."

## Misc Spells

Bucket logic: targeted utility, cheap artifacts with relevant abilities, alternate-cost spell fodder, and other bespoke cards that do not fit cleaner buckets.

Bucket tests: target restrictions are enforced; ignored effects resolve safely; alternate/free costs pay correct resources; relevant activated abilities are generated and resolve.

### Blazing Shoal
Action gen: instant speed; target creature; normal X-cost or pitch red card for X=pitched MV.
Resolution: no modeled effect.
Tests: generates normal X actions; generates pitch-red actions; requires creature target; pitched card exiled; no target illegal.
Comments: "Power boost not modeled; card is useful as free spell/draw trigger."

### Boomerang Basics
Action gen: sorcery speed; target nonland permanent: own battlefield permanent or dummy opponent nonland permanent.
Resolution: bounce target; if own permanent, move it to hand and draw 1; if opponent dummy, remove/ignore dummy and draw 0.
Tests: generates own/dummy target actions; no land targets; own bounce returns to hand and draws 1; dummy target no draw.
Comments: "Opponent permanents are modeled as dummy targets, not real zones/hands."

### Cave-In
Action gen: sorcery speed; normal cast or pitch red card.
Resolution: deals damage to each creature/player; creates no Vivi/Curiosity draws from resolution damage; moves Ragavan/Tandem Lookout from battlefield to graveyard.
Tests: generates normal/pitch actions; pitched card exiled; cast still triggers normal noncreature Vivi/Curiosity draw; resolution creates no extra Curiosity draws; kills Ragavan/Tandem Lookout if present.
Comments: "Creature toughness not tracked; only relevant own creatures are explicitly killed."

### Chain of Vapor
Action gen: instant speed; target nonland permanent: own battlefield permanent or dummy opponent nonland permanent.
Resolution: bounce target; then create optional pending copy action by sacrificing a land; copy targets another nonland permanent and does not trigger Curiosity; each copy can create another optional copy.
Tests: target legality; own permanent returns to hand; copy requires sacrificing land; copy does not increment spell count/draw trigger; copy can chain repeatedly.
Comments: "Copy clause modeled because bouncing mana-positive permanents can be combo-relevant."

### Crowd's Favor
Action gen: instant speed; target creature; normal cast or convoke using available untapped creature.
Resolution: no modeled effect.
Tests: requires creature target; generates normal cast when payable; generates convoke action when creature available; convoked creature becomes tapped.
Comments: "Combat effect ignored; convoke matters as alternate/free spell casting."

### Gut Shot
Action gen: instant speed; target creature/player/dummy target; normal red cost or free life-cost mode.
Resolution: no modeled effect.
Tests: generates free cast; requires legal target; increments noncreature count/Curiosity trigger.
Comments: "Damage ignored; card is useful as free spell/draw trigger."

### Lodestone Bauble
Action gen: default cast; tapped sac ability with a target.
Resolution: enters battlefield; ability sacrifices Bauble with no modeled library effect.
Tests: resolves to battlefield; generates targeting ability.
Comments: "Actual ability putting basics on libraries is ignored."

### Mishra's Bauble
Action gen: default cast; tap/sac ability targeting a player.
Resolution: enters battlefield; ability sacrifices Bauble with no immediate draw.
Tests: resolves to battlefield; ability requires untapped Bauble; sacrifice moves Bauble to graveyard; target player action generated.
Comments: "Delayed next-upkeep draw ignored."

### Mogg Salvage
Action gen: instant speed; target artifact; normal cast or free if opponent controls Island and we control Mountain.
Resolution: destroy/remove target artifact; dummy opponent artifact removed/ignored.
Tests: generates paid/free actions; free action requires opponent Island and own Mountain; requires artifact target.
Comments: "Opponent artifact modeled as dummy target."

### Pyrokinesis
Action gen: instant speed; normal cast or pitch red card; target up to relevant creature/dummy creature targets.
Resolution: no modeled damage effect.
Tests: generates normal/pitch actions; pitch requires red card and exiles it; requires legal creature target; player target illegal.
Comments: "Damage ignored; card is useful as free spell/draw trigger."

### Redirect Lightning
Action gen: instant speed; `{R}` plus ignored life payment; target spell/ability with a single target.
Resolution: no modeled effect.
Tests: generates only with legal single-target stack object and available red mana.
Comments: "Life payment and actual redirection/damage ignored; red mana cost still required."

### Repeal
Action gen: instant speed; target nonland permanent with MV <= X.
Resolution: bounce target to hand if own permanent; draw 1.
Tests: generates affordable X actions; excludes lands and MV>X permanents; own target returns to hand and draws 1.
Comments: "Opponent dummy bounce has no real owner hand."

### Secret Identity
Action gen: sorcery speed; target creature.
Resolution: no modeled effect.
Tests: requires creature target; resolves safely.
Comments: "Manifest dread ignored."

### Snapback
Action gen: instant speed; target creature, including opponent dummy creature; normal cast or pitch blue card.
Resolution: bounce target creature; own creature returns to hand; dummy target removed/ignored.
Tests: generates normal/pitch actions; pitch requires blue card and exiles it; target creature required; own creature returns to hand; dummy target resolves safely.

### Thunderclap
Action gen: instant speed; target creature; normal cast or sacrifice Mountain.
Resolution: damage kills Ragavan/Tandem Lookout if targeted; dummy target ignored.
Tests: generates normal/sac-Mountain actions; sacrifice moves Mountain to graveyard; requires creature target.
Comments: "Damage/toughness simplified to only relevant own creatures."

### Twisted Image
Action gen: instant speed; target creature.
Resolution: draw 1; ignore power/toughness swap.
Tests: requires creature target; resolution draws 1.
Comments: "Power/toughness swap ignored."

### Urza's Bauble
Action gen: default cast; tapped sac ability with target player.
Resolution: enters battlefield; ability sacrifices Bauble with no immediate draw.
Tests: resolves to battlefield; generates targeting ability.
Comments: "Delayed next-upkeep draw ignored."

### Vexing Bauble
Action gen: default cast; activated ability pay `{1}`, sacrifice: draw 1.
Resolution: enters battlefield; while active, any spell cast with no mana spent creates a non-targeting trigger that counters that spell.
Tests: resolves to battlefield; free cast creates Bauble trigger; trigger counters free spell without targeting; paid spells do not trigger; pay-1 sac ability draws 1 and removes Bauble.
Comments: "Only free-spell counter trigger and draw ability modeled."

### Wild Ride
Action gen: sorcery speed; target creature; harmonize from graveyard for `{R}` by tapping Vivi.
Resolution: spell mode no modeled effect; harmonize exiles after cast.
Tests: normal cast requires creature target; harmonize requires Wild Ride in graveyard, `{R}`, legal target, and untapped Vivi; harmonize taps Vivi, triggers noncreature cast effects, and resolves to exile.
Comments: "Pump/haste ignored; harmonize simplified to `{R}` plus tapping Vivi."

## Generic No-Op Permanents

Bucket logic: permanents with triggered abilities that are intentionally irrelevant because opponents are assumed not to cast spells during the sim.

Bucket tests: cast actions generated normally; noncreature cast triggers Vivi/Curiosity; resolution enters battlefield; no extra card draw from printed text.

### Mystic Remora
Action gen: default.
Resolution: enters battlefield; no modeled triggered ability.
Tests: default cast; triggers normal noncreature draw; resolves to battlefield; no Remora draw.
Comments: "Opponent-cast trigger ignored because opponents do not cast spells in this sim."

### Rhystic Study
Action gen: default.
Resolution: enters battlefield; no modeled triggered ability.
Tests: default cast; triggers normal noncreature draw; resolves to battlefield; no Rhystic draw.
Comments: "Opponent-cast trigger ignored because opponents do not cast spells in this sim."

## Intake New Cards

Bucket logic: blank holding area for future additions. Keep `Bucket: TBD` until deliberately sorted.

### Card Name
Bucket: TBD
Action gen:
Resolution:
Tests:
Comments:
