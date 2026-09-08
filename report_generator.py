"""
수집된 현안을 Claude API 로 통합 가공하여 경영진용 보고서를 만든다.
"""

from __future__ import annotations

import os

import config
import org_store

SYSTEM_PROMPT = """당신은 경영기획팀의 보고서 작성 전문가입니다.
각 부문·팀이 제출한 일일 현안 원문을 받아 경영진 보고용 '일일 현안 보고서'로 통합 가공합니다.

작성 규칙:
1. 문서 최상단에 경영진용 '핵심 요약(Executive Summary)'을 3~6개 항목으로 작성한다.
   - 전사 관점에서 의사결정·리스크·주요 성과에 해당하는 내용만 선별한다.
2. 이어서 6개 대부문(공통, 에너지부문, 해저부문, 인더스트리부문, 생산/기술부문, 경영부문)
   순서로 정리하고, 각 대부문 아래에 팀별 현안을 정리한다.
   - 제출 데이터가 없는 대부문/팀은 아예 표기하지 않는다.
3. 모든 문장은 개조식으로 작성한다. 어미는 '~함', '~임', '~예정임', '~필요함' 형태를 사용한다.
4. 여러 팀이 같은 내용을 제출한 경우 중복을 제거하고 하나로 통합하되,
   관련 팀명을 괄호로 병기한다.
5. 원문에 없는 사실을 지어내지 않는다. 수치·일정·고유명사는 원문 그대로 유지한다.
6. 출력은 마크다운으로만 하며, 인사말이나 설명 문구를 덧붙이지 않는다."""


def build_source_text(records: list[dict], date_str: str) -> str:
    """시트에서 읽은 행들을 LLM 입력용 텍스트로 정리."""
    lines = [f"[대상 일자] {date_str}", ""]

    by_division: dict[str, dict[str, list[dict]]] = {}
    for record in records:
        division = record.get("대부문", "미분류") or "미분류"
        team = record.get("팀명", "미분류") or "미분류"
        by_division.setdefault(division, {}).setdefault(team, []).append(record)

    # config 에 정의된 순서를 우선하고, 그 밖의 값은 뒤에 붙인다
    organization = org_store.load_organization()
    ordered = [d for d in organization if d in by_division]
    ordered += [d for d in by_division if d not in ordered]

    for division in ordered:
        lines.append(f"## {division}")
        for team, items in by_division[division].items():
            lines.append(f"### {team}")
            for item in items:
                author = item.get("작성자", "")
                written_at = item.get("작성일시", "")
                content = (item.get("일일현안내용", "") or "").strip()
                lines.append(f"- (작성자: {author} / 작성일시: {written_at}) {content}")
        lines.append("")

    return "\n".join(lines)


def generate_report(records: list[dict], date_str: str) -> tuple[str | None, str | None]:
    """통합 보고서 마크다운을 생성. 반환값은 (보고서, 오류 메시지)."""
    if not records:
        return None, f"{date_str} 에 제출된 현안이 없습니다."

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        if config.DEMO_MODE:
            # 시연 환경에서 API 키 없이도 화면 흐름을 끝까지 확인할 수 있도록
            # 규칙 기반 보고서를 대신 생성합니다 (요약 문구는 고정).
            return build_offline_report(records, date_str), None
        return None, "`.env` 에 ANTHROPIC_API_KEY 를 설정해 주세요."

    try:
        import anthropic
    except ImportError:
        return None, "anthropic 패키지가 설치되어 있지 않습니다. `pip install anthropic`"

    source_text = build_source_text(records, date_str)
    user_prompt = (
        f"다음은 {date_str} 각 팀이 제출한 일일 현안 원문입니다. "
        "위 규칙에 따라 통합 보고서를 작성해 주세요.\n\n"
        f"{source_text}"
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        with client.messages.stream(
            model=config.ANTHROPIC_MODEL,
            max_tokens=config.ANTHROPIC_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            response = stream.get_final_message()
    except anthropic.APIStatusError as e:
        return None, f"Claude API 오류({e.status_code}): {e.message}"
    except anthropic.APIConnectionError:
        return None, "Claude API 에 연결하지 못했습니다. 네트워크를 확인해 주세요."
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

    if response.stop_reason == "refusal":
        return None, "모델이 요청을 거절했습니다. 입력 내용을 확인해 주세요."

    text = "\n".join(b.text for b in response.content if b.type == "text").strip()
    if not text:
        return None, "보고서 본문이 비어 있습니다. 다시 시도해 주세요."

    header = f"# 일일 현안 보고서 ({date_str})\n\n"
    return header + text, None


# ---------------------------------------------------------------------------
# 오프라인(데모) 보고서 — Claude API 키 없이 화면 흐름 확인용
# ---------------------------------------------------------------------------


def build_offline_report(records: list[dict], date_str: str) -> str:
    """LLM 없이 제출 원문을 부문/팀별로 묶어 마크다운으로 출력.

    실제 통합 가공(중복 제거·요약·개조식 변환)은 하지 않습니다.
    레이아웃과 다운로드 동작을 확인하기 위한 자리표시자입니다.
    """
    by_division: dict[str, dict[str, list[str]]] = {}
    for record in records:
        division = record.get("대부문", "미분류") or "미분류"
        team = record.get("팀명", "미분류") or "미분류"
        content = (record.get("일일현안내용", "") or "").strip()
        by_division.setdefault(division, {}).setdefault(team, []).append(content)

    organization = org_store.load_organization()
    ordered = [d for d in organization if d in by_division]
    ordered += [d for d in by_division if d not in ordered]

    lines = [
        f"# 일일 현안 보고서 ({date_str})",
        "",
        "> ⚠️ **데모 출력** — ANTHROPIC_API_KEY 가 없어 LLM 통합 가공 없이 "
        "제출 원문을 그대로 묶었습니다. 실제 보고서는 핵심 요약과 중복 제거를 포함합니다.",
        "",
        "## 핵심 요약 (Executive Summary)",
        "",
        f"- 금일 {len(records)}건의 현안이 {len(by_division)}개 대부문에서 접수됨",
        f"- 제출 부문: {', '.join(ordered)}",
        "- (실제 운영 시 이 영역은 Claude 가 경영진 관점으로 재작성함)",
        "",
    ]

    for division in ordered:
        lines.append(f"## {division}")
        lines.append("")
        for team, contents in by_division[division].items():
            lines.append(f"### {team}")
            for content in contents:
                for raw in content.splitlines():
                    text = raw.strip().lstrip("-").strip()
                    if text:
                        lines.append(f"- {text}")
            lines.append("")

    return "\n".join(lines)
