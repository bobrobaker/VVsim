import pytest
from mtg_sim.sim.policies import _clear_config_cache


@pytest.fixture(autouse=True)
def reset_policy_cache():
    """Clear the policy config cache before each test to prevent cross-test contamination."""
    _clear_config_cache()
    yield
    _clear_config_cache()
