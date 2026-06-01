from app.routes import v3
from app.services import agent


def test_v3_chat_returns_tool_calls():
    response = v3.chat(body={"message": "服务 OOM 了怎么办？"})
    assert response["toolCalls"]


def test_v3_database_lag_reads_dba_sop():
    response = v3.chat(body={"message": "数据库主从延迟超过30秒怎么处理？"})
    fnames = _tool_filenames(response)
    assert "index.json" in fnames
    assert "sop-002.html" in fnames
    assert "主从" in response["answer"] or "延迟" in response["answer"]


def test_v3_service_oom_reads_backend_sop():
    response = v3.chat(body={"message": "服务 OOM 了怎么办？"})
    fnames = _tool_filenames(response)
    assert "index.json" in fnames
    assert "sop-001.html" in fnames
    assert "sop-007.html" not in fnames
    assert "OOM" in response["answer"] or "OutOfMemoryError" in response["answer"]


def test_v3_p0_reads_multiple_sops():
    response = v3.chat(body={"message": "P0 故障的响应流程是什么？"})
    fnames = _tool_filenames(response)
    assert "index.json" in fnames
    assert len([fname for fname in fnames if fname.endswith(".html")]) >= 2
    assert "升级" in response["answer"] or "P0" in response["answer"]


def test_v3_intrusion_reads_security_sop():
    response = v3.chat(body={"message": "怀疑有人入侵了系统"})
    fnames = _tool_filenames(response)
    assert "index.json" in fnames
    assert "sop-005.html" in fnames
    assert "安全" in response["answer"] or "入侵" in response["answer"]


def test_v3_recommendation_quality_reads_ai_sop():
    response = v3.chat(body={"message": "推荐结果质量下降了"})
    fnames = _tool_filenames(response)
    assert "index.json" in fnames
    assert "sop-008.html" in fnames
    assert "推荐" in response["answer"] or "模型" in response["answer"]


def test_v3_deepseek_planner_accepts_only_index_filenames(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_MODE", "deepseek")

    def fake_chat_completion(messages, **kwargs):
        if kwargs.get("response_format"):
            return '{"files":["sop-002.html","../README.md","missing.html","*.html"],"reason":"test"}'
        return "DeepSeek answer based on SOP"

    monkeypatch.setattr(agent.deepseek_client, "chat_completion", fake_chat_completion)
    response = v3.chat(body={"message": "数据库主从延迟超过30秒怎么处理？"})
    fnames = _tool_filenames(response)
    assert fnames == ["index.json", "sop-002.html"]
    assert response["answer"] == "DeepSeek answer based on SOP"
    assert response["agent"]["planner"] == "deepseek"
    assert response["agent"]["answerMode"] == "deepseek"
    assert response["agent"]["deepseekConfigured"] is True


def _tool_filenames(response: dict) -> list[str]:
    return [call["args"]["fname"] for call in response["toolCalls"]]
