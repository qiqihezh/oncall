from app.routes import v2
from app.services import semantic_search


def test_v2_server_down_returns_backend_and_sre_first():
    result_ids = [item.id for item in semantic_search.search("服务器挂了")]
    assert result_ids[:2] == ["sop-001", "sop-004"]


def test_v2_hacker_attack_returns_security_first():
    result_ids = [item.id for item in semantic_search.search("黑客攻击")]
    assert result_ids[0] == "sop-005"


def test_v2_ml_model_problem_returns_ai_first():
    result_ids = [item.id for item in semantic_search.search("机器学习模型出问题")]
    assert result_ids[0] == "sop-008"


def test_v2_route_returns_results():
    response = v2.search(q="黑客攻击")
    assert response["query"] == "黑客攻击"
    assert response["results"][0]["id"] == "sop-005"
