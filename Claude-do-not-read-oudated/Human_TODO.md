Claude my WRITE to this file if excplicitely told but do not READ to this file. If you do, expose to user. 


## Policy / scoring known issues
Deferred to the dedicated policy pass (v0.6).

- policy refining: refactor policy to have weights that are in text editable policy config file, in manual mode when reporting actions for the user to choose also display what the policies system thinks of each choice, if then you choose not the top policy manual mode will prompt you as to why and it will log that in a policy-adjustment log + any relevant info about the state. Then review the policy log with claude to refine policy behavior
- explore the feasiblity of spliting card-specific code into per-card files so each card's full behavior (generation + resolution + tests) can be handed off cleanly.

## Card specific bug squash
- Final fortune is under "extra turn sorceries" even though it technically isn't a sorcery. Probably should just update the comment title above to say Extra turn effects.
- Hullbreaker horror test dosn't look quite right - not sure its actually doing what the test says it should be doing
- does bouncing vivi detach it from existing curiosities? I think we should have a simplified wincon involving bouncing vivi floating enuough mana to recast it + a new curiosity in hand since we're already assuming at start of simulation vivi button isn't pressed (if it is we for sure have won already) 
- need to double check tapping dual lands lets you choose which color to produce 

## High prioroity bug squash 
- cast from exiles must respect cast timings
- cast from exiles must allow for alternate casting costs (life)
- you need to be able to choose how to 

## architectural setup:
- how would you introspect tokens workflow?
    - prompt pre-baking / manual exploring agent? Is this exploration
- create upper level claud.md with insights from looking at ilya's claud.nd (todo, testing)

## Pending ideas:
- Project management/orchestration implementor: an phase (maybe an agent?) that translates the development plan into workstreams 

