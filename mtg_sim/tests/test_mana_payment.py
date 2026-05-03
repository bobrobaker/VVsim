import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mtg_sim.sim.mana import ManaPool, ManaCost, can_pay_cost, pay_cost


def test_exact_colored_pay():
    pool = ManaPool(U=1, R=1)
    cost = ManaCost(pip_u=1, pip_r=1)
    assert can_pay_cost(pool, cost)
    result = pay_cost(pool, cost)
    assert result.U == 0 and result.R == 0


def test_cannot_pay_missing_color():
    pool = ManaPool(U=2)
    cost = ManaCost(pip_r=1)
    assert not can_pay_cost(pool, cost)


def test_any_pays_for_u_pip():
    pool = ManaPool(ANY=1)
    cost = ManaCost(pip_u=1)
    assert can_pay_cost(pool, cost)
    result = pay_cost(pool, cost)
    assert result.ANY == 0


def test_any_pays_for_generic():
    pool = ManaPool(ANY=2)
    cost = ManaCost(generic=2)
    assert can_pay_cost(pool, cost)
    result = pay_cost(pool, cost)
    assert result.ANY == 0


def test_generic_uses_colorless_first():
    pool = ManaPool(U=1, C=2)
    cost = ManaCost(generic=2)
    result = pay_cost(pool, cost)
    assert result.C == 0
    assert result.U == 1


def test_insufficient_generic():
    pool = ManaPool(U=1, R=1)
    cost = ManaCost(pip_u=1, pip_r=1, generic=1)
    assert not can_pay_cost(pool, cost)


def test_x_cost():
    # pip_u=1 + x_value=2 = 3 total mana needed
    pool = ManaPool(U=1, C=2)
    cost = ManaCost(pip_u=1, x_cost=True, x_value=2)
    assert can_pay_cost(pool, cost)
    result = pay_cost(pool, cost)
    assert result.total() == 0


def test_free_cost():
    pool = ManaPool()
    cost = ManaCost.zero()
    assert can_pay_cost(pool, cost)
