from __future__ import annotations

from dataclasses import dataclass

from app.models import Document, SearchResult
from app.services import document_store, keyword_search


@dataclass(frozen=True)
class SemanticProfile:
    doc_id: str
    query_phrases: tuple[str, ...]
    doc_terms: tuple[str, ...]


PROFILES = (
    SemanticProfile(
        doc_id="sop-001",
        query_phrases=("服务器挂了", "服务挂了", "服务崩了", "服务不可用", "后端挂了", "接口挂了", "服务超时", "oom"),
        doc_terms=("后端", "服务", "OOM", "OutOfMemoryError", "超时", "降级", "回滚", "Pod", "故障分级"),
    ),
    SemanticProfile(
        doc_id="sop-002",
        query_phrases=("数据库", "主从延迟", "慢查询", "连接池满", "数据恢复", "从库延迟"),
        doc_terms=("数据库", "主从", "延迟", "慢查询", "连接池", "恢复"),
    ),
    SemanticProfile(
        doc_id="sop-003",
        query_phrases=("页面白屏", "白屏", "前端挂了", "资源加载失败", "兼容性问题", "页面变慢"),
        doc_terms=("前端", "白屏", "CDN", "资源加载", "兼容性", "性能", "CORS"),
    ),
    SemanticProfile(
        doc_id="sop-004",
        query_phrases=("服务器挂了", "服务挂了", "故障响应", "监控告警", "k8s故障", "集群异常", "容量不足"),
        doc_terms=("SRE", "K8s", "集群", "监控", "告警", "容量", "故障响应", "P0"),
    ),
    SemanticProfile(
        doc_id="sop-005",
        query_phrases=("黑客攻击", "被攻击", "有人入侵", "入侵系统", "安全事件", "漏洞被利用", "异常登录"),
        doc_terms=("安全", "入侵", "漏洞", "攻击", "事件", "隔离", "取证", "应急响应"),
    ),
    SemanticProfile(
        doc_id="sop-006",
        query_phrases=("数据管道故障", "etl失败", "spark任务失败", "数据延迟", "数据平台异常"),
        doc_terms=("数据管道", "ETL", "Spark", "任务", "延迟", "集群"),
    ),
    SemanticProfile(
        doc_id="sop-007",
        query_phrases=("app崩溃", "移动端崩了", "热修复", "推送失败", "崩溃率上升"),
        doc_terms=("App", "崩溃", "移动端", "热修复", "推送", "Crash"),
    ),
    SemanticProfile(
        doc_id="sop-008",
        query_phrases=("机器学习模型出问题", "模型出问题", "推荐结果质量下降", "推荐质量下降", "推理延迟", "gpu异常"),
        doc_terms=("AI", "算法", "模型", "机器学习", "推荐", "质量", "推理", "GPU"),
    ),
    SemanticProfile(
        doc_id="sop-009",
        query_phrases=("测试环境故障", "自动化测试失败", "发版卡点", "qa环境异常"),
        doc_terms=("QA", "测试", "自动化", "发版", "环境"),
    ),
    SemanticProfile(
        doc_id="sop-010",
        query_phrases=("cdn故障", "dns异常", "ddos攻击", "网络异常", "网络延迟", "节点故障"),
        doc_terms=("网络", "CDN", "DNS", "DDoS", "节点", "负载均衡", "延迟"),
    ),
)


def search(query: str) -> list[SearchResult]:
    normalized_query = _normalize(query)
    if not normalized_query:
        return []

    docs = {doc.id: doc for doc in document_store.list_documents()}
    scored: dict[str, SearchResult] = {}

    for item in keyword_search.search(query):
        scored[item.id] = SearchResult(
            id=item.id,
            title=item.title,
            snippet=item.snippet,
            score=round(min(item.score * 0.35, 0.75), 3),
        )

    for profile in PROFILES:
        doc = docs.get(profile.doc_id)
        if not doc:
            continue

        profile_score, matches = _score_profile(normalized_query, doc, profile)
        if profile_score <= 0:
            continue

        current = scored.get(doc.id)
        score = round(profile_score + (current.score if current else 0), 3)
        scored[doc.id] = SearchResult(
            id=doc.id,
            title=doc.title,
            snippet=_semantic_snippet(doc, matches),
            score=score,
        )

    return sorted(scored.values(), key=lambda item: (-item.score, item.id))


def _score_profile(query: str, doc: Document, profile: SemanticProfile) -> tuple[float, list[str]]:
    matches: list[str] = []
    score = 0.0

    for phrase in profile.query_phrases:
        normalized_phrase = _normalize(phrase)
        if normalized_phrase and normalized_phrase in query:
            matches.append(phrase)
            score += 1.2

    doc_text = _normalize(f"{doc.title} {doc.text}")
    for term in profile.doc_terms:
        normalized_term = _normalize(term)
        if not normalized_term:
            continue
        if normalized_term in query:
            matches.append(term)
            score += 0.8
        elif matches and normalized_term in doc_text and _has_related_signal(query, normalized_term):
            score += 0.15

    return score, _unique(matches)


def _has_related_signal(query: str, term: str) -> bool:
    if len(term) <= 1:
        return False
    return any(char in query for char in term)


def _semantic_snippet(doc: Document, matches: list[str]) -> str:
    prefix = f"语义命中：{', '.join(matches)}。 " if matches else "语义相关。 "
    return f"{prefix}{doc.text[:120]}"


def _normalize(value: str) -> str:
    return value.strip().lower().replace(" ", "")


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = _normalize(value)
        if key not in seen:
            result.append(value)
            seen.add(key)
    return result
