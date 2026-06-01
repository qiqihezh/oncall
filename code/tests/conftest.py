import pytest


@pytest.fixture(autouse=True)
def disable_live_deepseek(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
