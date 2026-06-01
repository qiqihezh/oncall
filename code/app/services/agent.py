from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from app.services import deepseek_client, html_parser, tools


SENTENCE_SPLIT = re.compile(r"(?<=[。！？])")


@dataclass(frozen=True)
class LoadedDoc:
    filename: str
    title: str
    text: str
    keywords: tuple[str, ...]


def reply(message: str) -> dict:
    question = message.strip()
    if not question:
        return {"answer": "请输入一个 On-Call 问题。", "toolCalls": [], "documents": []}

    tool_calls: list[dict] = []
    index = _read_index(tool_calls)
    selected_entries, planner = _select_entries(question, index)

    loaded_docs: list[LoadedDoc] = []
    for entry in selected_entries:
        filename = entry["filename"]
        raw_html = _read_with_trace(filename, tool_calls)
        title, text = html_parser.parse_html(raw_html)
        loaded_docs.append(
            LoadedDoc(
                filename=filename,
                title=title,
                text=text,
                keywords=tuple(entry.get("keywords", [])),
            )
        )

    answer, answer_mode = _build_answer(question, loaded_docs)
    return {
        "answer": answer,
        "toolCalls": tool_calls,
        "documents": [{"filename": doc.filename, "title": doc.title} for doc in loaded_docs],
        "agent": {
            "planner": planner,
            "answerMode": answer_mode,
            "deepseekConfigured": deepseek_client.is_configured(),
            "mode": "deepseek" if deepseek_client.is_enabled() else "local",
        },
    }


def _read_index(tool_calls: list[dict]) -> dict[str, Any]:
    raw_index = _read_with_trace("index.json", tool_calls)
    return json.loads(raw_index)


def _read_with_trace(fname: str, tool_calls: list[dict]) -> str:
    content = tools.read_file(fname)
    tool_calls.append({"tool": "readFile", "args": {"fname": fname}})
    return content


def _select_entries(question: str, index: dict[str, Any]) -> tuple[list[dict], str]:
    if deepseek_client.is_enabled() and deepseek_client.is_configured():
        try:
            selected = _select_entries_with_deepseek(question, index)
            if selected:
                return selected, "deepseek"
        except Exception:
            pass

    return _select_entries_locally(question, index), "local-fallback"


def _select_entries_with_deepseek(question: str, index: dict[str, Any]) -> list[dict]:
    docs = index.get("documents", [])
    allowed = {doc.get("filename"): doc for doc in docs}
    index_summary = [
        {
            "filename": doc.get("filename"),
            "title": doc.get("title"),
            "keywords": doc.get("keywords", []),
            "queryPhrases": doc.get("queryPhrases", []),
        }
        for doc in docs
    ]

    content = deepseek_client.chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "你是 On-Call SOP 文件选择 Agent。"
                    "你不能列目录，不能使用通配符，不能发明文件名。"
                    "只能从用户提供的 index.json 摘要里选择明确 filename。"
                    "输出必须是 JSON：{\"files\":[\"sop-xxx.html\"],\"reason\":\"...\"}。"
                    "P0 或跨团队故障可以选择多个 SOP。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"question": question, "index": index_summary, "p0_files": index.get("p0_files", [])},
                    ensure_ascii=False,
                ),
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=500,
        temperature=0.0,
    )
    data = json.loads(content)
    filenames = data.get("files", [])
    if not isinstance(filenames, list):
        return []

    selected: list[dict] = []
    seen: set[str] = set()
    for filename in filenames:
        if filename in allowed and filename not in seen:
            selected.append(allowed[filename])
            seen.add(filename)

    if _is_p0_question(question):
        for filename in index.get("p0_files", []):
            if filename in allowed and filename not in seen:
                selected.append(allowed[filename])
                seen.add(filename)
        return selected[:5]

    return selected[:1]


def _select_entries_locally(question: str, index: dict[str, Any]) -> list[dict]:
    normalized_question = _normalize(question)
    docs = index.get("documents", [])

    if _is_p0_question(question):
        filenames = index.get("p0_files", [])
        return [doc for doc in docs if doc.get("filename") in filenames]

    scored: list[tuple[float, dict]] = []
    for doc in docs:
        score = 0.0
        matched = False
        for phrase in doc.get("queryPhrases", []):
            if _normalize(phrase) in normalized_question:
                score += 3.0
                matched = True
        for keyword in doc.get("keywords", []):
            if _normalize(keyword) in normalized_question:
                score += 1.2
                matched = True
        if matched:
            scored.append((score, doc))

    if not scored:
        fallback = index.get("fallback_files", ["sop-004.html"])
        return [doc for doc in docs if doc.get("filename") in fallback]

    scored.sort(key=lambda item: (-item[0], item[1].get("filename", "")))
    top_score = scored[0][0]
    if top_score >= 3.0:
        selected = [doc for score, doc in scored if score >= max(3.0, top_score - 1.0)]
        return selected[:2]
    return [scored[0][1]]


def _build_answer(question: str, docs: list[LoadedDoc]) -> tuple[str, str]:
    if not docs:
        return "没有定位到相关 SOP。请补充故障现象、涉及系统或告警关键词。", "local-fallback"

    if deepseek_client.is_enabled() and deepseek_client.is_configured():
        try:
            return _build_answer_with_deepseek(question, docs), "deepseek"
        except Exception:
            pass

    return _build_answer_locally(question, docs), "local-fallback"


def _build_answer_with_deepseek(question: str, docs: list[LoadedDoc]) -> str:
    sop_payload = [
        {
            "filename": doc.filename,
            "title": doc.title,
            "content": _shorten(doc.text, 5000),
        }
        for doc in docs
    ]
    return deepseek_client.chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "你是 On-Call 助手。必须只根据用户提供的 SOP 内容回答，不能编造。"
                    "回答要包含：处理步骤、排查方向、升级建议、禁止操作。"
                    "如果 SOP 中没有明确禁止操作，就写“未在已读取 SOP 中找到明确禁止操作”。"
                    "不要声称读取过未提供的文件。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps({"question": question, "sops": sop_payload}, ensure_ascii=False),
            },
        ],
        max_tokens=1600,
        temperature=0.2,
    )


def _build_answer_locally(question: str, docs: list[LoadedDoc]) -> str:

    lines: list[str] = []
    lines.append("已通过 readFile 读取相关 SOP，并基于文档内容整理如下：")
    lines.append("")
    lines.append("相关文档：")
    for doc in docs:
        lines.append(f"- {doc.filename}：{doc.title}")

    handling = _collect_sentences(question, docs, preferred=("首先", "检查", "确认", "如果", "需要", "通过", "立即", "紧急"))
    diagnosis = _collect_sentences(question, docs, preferred=("监控", "指标", "日志", "面板", "状态", "范围", "影响", "原因", "定位"))
    escalation = _collect_sentences(question, docs, preferred=("升级", "P0", "负责人", "通知", "故障群", "技术总监", "VP"))
    forbidden = _collect_sentences(question, docs, preferred=("禁止", "严禁", "不能", "不得"))

    lines.append("")
    lines.append("处理步骤：")
    for idx, sentence in enumerate((handling or diagnosis)[:6], start=1):
        lines.append(f"{idx}. {sentence}")

    lines.append("")
    lines.append("排查方向：")
    for sentence in (diagnosis or handling)[:4]:
        lines.append(f"- {sentence}")

    lines.append("")
    lines.append("升级建议：")
    if escalation:
        for sentence in escalation[:4]:
            lines.append(f"- {sentence}")
    else:
        lines.append("- 已读取 SOP 中没有找到明确升级路径；建议根据影响范围、持续时间和业务等级升级给对应负责人。")

    lines.append("")
    lines.append("禁止操作：")
    if forbidden:
        for sentence in forbidden[:3]:
            lines.append(f"- {sentence}")
    else:
        lines.append("- 未在已读取 SOP 中找到明确禁止操作。")

    lines.append("")
    lines.append("读取依据：")
    for doc in docs:
        lines.append(f"- readFile(\"{doc.filename}\")")

    return "\n".join(lines)


def _collect_sentences(question: str, docs: list[LoadedDoc], preferred: tuple[str, ...]) -> list[str]:
    query_signals = _query_signals(question)
    collected: list[tuple[int, str]] = []

    for doc in docs:
        signals = set(query_signals)
        signals.update(doc.keywords)
        for sentence in _sentences(doc.text):
            score = 0
            for signal in signals:
                if signal and signal.lower() in sentence.lower():
                    score += 3
            for marker in preferred:
                if marker.lower() in sentence.lower():
                    score += 1
            if score > 0:
                collected.append((score, _shorten(sentence)))

    collected.sort(key=lambda item: -item[0])
    return _unique([sentence for _, sentence in collected])


def _query_signals(question: str) -> list[str]:
    signals = [
        "主从",
        "延迟",
        "数据库",
        "OOM",
        "OutOfMemoryError",
        "服务",
        "P0",
        "故障",
        "响应",
        "升级",
        "入侵",
        "安全",
        "攻击",
        "推荐",
        "质量",
        "模型",
        "机器学习",
    ]
    normalized = question.lower()
    return [signal for signal in signals if signal.lower() in normalized]


def _sentences(text: str) -> list[str]:
    pieces = [piece.strip() for piece in SENTENCE_SPLIT.split(text)]
    return [piece for piece in pieces if len(piece) >= 8]


def _shorten(sentence: str, limit: int = 180) -> str:
    if len(sentence) <= limit:
        return sentence
    return sentence[: limit - 1] + "..."


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _normalize(value: str) -> str:
    return value.strip().lower().replace(" ", "")


def _is_p0_question(question: str) -> bool:
    normalized_question = _normalize(question)
    return any(token in normalized_question for token in ("p0", "重大故障", "响应流程", "故障响应", "升级流程"))
