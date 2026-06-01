from app.main import app
from app.routes import v1
from app.services import keyword_search
from fastapi import HTTPException
import pytest


def test_app_created():
    assert app.title == "On-Call Assistant"


def test_v1_oom_returns_sop_001():
    results = keyword_search.search("OOM")
    assert results
    assert any(item.id == "sop-001" for item in results)


def test_v1_incident_returns_multiple_documents():
    results = keyword_search.search("故障")
    assert len(results) > 1


def test_v1_script_content_is_excluded():
    assert keyword_search.search("replication") == []


def test_v1_cdn_returns_frontend_and_network_docs():
    result_ids = {item.id for item in keyword_search.search("CDN")}
    assert {"sop-003", "sop-010"}.issubset(result_ids)


def test_v1_ampersand_is_searchable():
    results = keyword_search.search("&")
    assert results
    assert any(item.id in {"sop-003", "sop-008", "sop-010"} for item in results)


def test_v1_post_document_indexes_visible_text_only():
    response = v1.create_document(
        {
            "id": "sop-unit-test",
            "html": "<html><title>单元测试 SOP</title><body><script>hidden_phase1_token</script><p>visible_phase1_token</p></body></html>",
        }
    )
    assert response == {"id": "sop-unit-test", "title": "单元测试 SOP"}
    assert [item.id for item in keyword_search.search("visible_phase1_token")] == ["sop-unit-test"]
    assert keyword_search.search("hidden_phase1_token") == []


def test_v1_post_document_requires_id_and_html():
    with pytest.raises(HTTPException) as exc:
        v1.create_document({"id": "", "html": ""})
    assert exc.value.status_code == 400
