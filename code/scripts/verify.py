from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify On-Call assistant core APIs.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    verifier = Verifier(args.base_url.rstrip("/"))
    checks = [
        ("health", verifier.check_health),
        ("phase1_oom", lambda: verifier.check_search("/v1/search", "OOM", contains=["sop-001"])),
        ("phase1_incident", lambda: verifier.check_min_results("/v1/search", "故障", 2)),
        ("phase1_script_excluded", lambda: verifier.check_search("/v1/search", "replication", exact=[])),
        ("phase1_cdn", lambda: verifier.check_search("/v1/search", "CDN", contains=["sop-003", "sop-010"])),
        ("phase1_ampersand", lambda: verifier.check_min_results("/v1/search", "&", 1)),
        ("phase1_literal_ampersand", verifier.check_literal_ampersand),
        ("phase2_server_down", lambda: verifier.check_top("/v2/search", "服务器挂了", ["sop-001", "sop-004"])),
        ("phase2_hacker", lambda: verifier.check_top("/v2/search", "黑客攻击", ["sop-005"])),
        ("phase2_ml", lambda: verifier.check_top("/v2/search", "机器学习模型出问题", ["sop-008"])),
        ("phase3_database", lambda: verifier.check_chat("数据库主从延迟超过30秒怎么处理？", ["index.json", "sop-002.html"])),
        ("phase3_oom", lambda: verifier.check_chat("服务 OOM 了怎么办？", ["index.json", "sop-001.html"])),
        ("phase3_p0", verifier.check_p0_chat),
        ("phase3_intrusion", lambda: verifier.check_chat("怀疑有人入侵了系统", ["index.json", "sop-005.html"])),
        ("phase3_recommendation", lambda: verifier.check_chat("推荐结果质量下降了", ["index.json", "sop-008.html"])),
    ]

    failures: list[str] = []
    for name, check in checks:
        try:
            detail = check()
            print(f"[PASS] {name}: {detail}")
        except Exception as exc:
            print(f"[FAIL] {name}: {exc}")
            failures.append(name)

    if failures:
        print(f"\n{len(failures)} checks failed: {', '.join(failures)}")
        return 1

    print("\nAll verification checks passed.")
    return 0


class Verifier:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def check_health(self) -> str:
        payload = self.get_json("/health")
        assert payload == {"status": "ok"}, payload
        return "status=ok"

    def check_search(
        self,
        endpoint: str,
        query: str,
        *,
        contains: list[str] | None = None,
        exact: list[str] | None = None,
    ) -> str:
        ids = self.search_ids(endpoint, query)
        if exact is not None and ids != exact:
            raise AssertionError(f"expected exact {exact}, got {ids}")
        if contains:
            missing = [item for item in contains if item not in ids]
            if missing:
                raise AssertionError(f"missing {missing}, got {ids}")
        return f"{query} => {ids[:6]}"

    def check_min_results(self, endpoint: str, query: str, minimum: int) -> str:
        ids = self.search_ids(endpoint, query)
        if len(ids) < minimum:
            raise AssertionError(f"expected at least {minimum}, got {ids}")
        return f"{query} => {len(ids)} results"

    def check_top(self, endpoint: str, query: str, expected_prefix: list[str]) -> str:
        ids = self.search_ids(endpoint, query)
        actual_prefix = ids[: len(expected_prefix)]
        if actual_prefix != expected_prefix:
            raise AssertionError(f"expected top {expected_prefix}, got {actual_prefix}")
        return f"{query} => top {actual_prefix}"

    def check_chat(self, message: str, expected_files: list[str]) -> str:
        payload = self.post_json("/v3/chat", {"message": message})
        files = self.tool_files(payload)
        for expected in expected_files:
            if expected not in files:
                raise AssertionError(f"missing {expected}, got {files}")
        answer = payload.get("answer", "")
        if not answer:
            raise AssertionError("empty answer")
        return f"files={files}, answerLength={len(answer)}"

    def check_p0_chat(self) -> str:
        payload = self.post_json("/v3/chat", {"message": "P0 故障的响应流程是什么？"})
        files = self.tool_files(payload)
        html_files = [item for item in files if item.endswith(".html")]
        if "index.json" not in files or len(html_files) < 2:
            raise AssertionError(f"expected index.json and multiple SOP files, got {files}")
        return f"files={files}"

    def check_literal_ampersand(self) -> str:
        payload = self.get_json("/v1/search?q=&")
        if payload.get("query") != "&":
            raise AssertionError(f"expected query '&', got {payload.get('query')!r}")
        ids = [item["id"] for item in payload.get("results", [])]
        if not ids:
            raise AssertionError("expected results for literal ampersand")
        return f"literal q=& => {ids[:6]}"

    def search_ids(self, endpoint: str, query: str) -> list[str]:
        path = f"{endpoint}?q={urllib.parse.quote(query)}"
        payload = self.get_json(path)
        return [item["id"] for item in payload.get("results", [])]

    def tool_files(self, payload: dict[str, Any]) -> list[str]:
        return [call.get("args", {}).get("fname", "") for call in payload.get("toolCalls", [])]

    def get_json(self, path: str) -> dict[str, Any]:
        with urllib.request.urlopen(f"{self.base_url}{path}", timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    sys.exit(main())
