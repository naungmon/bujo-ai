"""Test fixtures and setup for bujo tests."""

import os
import pytest


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the AI rate limiter and API key before each test."""
    from bujo.rate_limit import reset_for_testing
    reset_for_testing()
    yield
    reset_for_testing()
