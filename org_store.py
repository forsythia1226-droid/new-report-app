"""
조직 구조(대부문 / 팀)의 저장·수정.

`config.ORGANIZATION` 은 최초 기본값(시드)이고, 화면에서 수정한 결과는
`organization.json` 파일에 저장되어 이후 실행에도 유지됩니다.
파일이 없으면 언제나 config 의 기본값으로 시작합니다.

순서는 사용자가 넣은 순서를 그대로 유지합니다(JSON 객체 순서 보존).
"""

from __future__ import annotations

import json
import os

import config


def _path() -> str:
    return config.ORG_FILE


def load_organization() -> dict[str, list[str]]:
    """현재 조직 구조를 반환. 저장 파일이 없거나 깨졌으면 기본값."""
    path = _path()
    if not os.path.exists(path):
        return {d: list(teams) for d, teams in config.ORGANIZATION.items()}

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {d: list(teams) for d, teams in config.ORGANIZATION.items()}

    if not isinstance(data, dict) or not data:
        return {d: list(teams) for d, teams in config.ORGANIZATION.items()}

    # 형식 방어: 값이 리스트가 아니거나 빈 문자열이 섞여 있어도 앱이 죽지 않도록
    cleaned: dict[str, list[str]] = {}
    for division, teams in data.items():
        if not isinstance(division, str) or not division.strip():
            continue
        if not isinstance(teams, list):
            continue
        cleaned[division] = [t for t in teams if isinstance(t, str) and t.strip()]
    return cleaned or {d: list(teams) for d, teams in config.ORGANIZATION.items()}


def save_organization(organization: dict[str, list[str]]) -> None:
    with open(_path(), "w", encoding="utf-8") as f:
        json.dump(organization, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 수정 연산 — 모두 (성공 여부, 메시지) 를 반환
# ---------------------------------------------------------------------------


def add_division(name: str) -> tuple[bool, str]:
    name = name.strip()
    if not name:
        return False, "대부문 이름을 입력해 주세요."

    organization = load_organization()
    if name in organization:
        return False, f"'{name}' 대부문이 이미 있습니다."

    organization[name] = []
    save_organization(organization)
    return True, f"'{name}' 대부문을 추가했습니다."


def remove_division(name: str) -> tuple[bool, str]:
    organization = load_organization()
    if name not in organization:
        return False, f"'{name}' 대부문을 찾을 수 없습니다."
    if name == config.ADMIN_DIVISION:
        return False, (
            f"'{name}' 은 경영기획팀이 속한 대부문이라 삭제할 수 없습니다. "
            "먼저 config.py 의 ADMIN_DIVISION 을 바꿔 주세요."
        )
    if len(organization) <= 1:
        return False, "대부문은 최소 1개 이상 있어야 합니다."

    del organization[name]
    save_organization(organization)
    return True, f"'{name}' 대부문을 삭제했습니다."


def add_team(division: str, team: str) -> tuple[bool, str]:
    team = team.strip()
    if not team:
        return False, "팀 이름을 입력해 주세요."

    organization = load_organization()
    if division not in organization:
        return False, f"'{division}' 대부문을 찾을 수 없습니다."
    if team in organization[division]:
        return False, f"'{division}' 에 '{team}' 이 이미 있습니다."

    organization[division].append(team)
    save_organization(organization)
    return True, f"'{division} › {team}' 을 추가했습니다."


def remove_team(division: str, team: str) -> tuple[bool, str]:
    organization = load_organization()
    if division not in organization or team not in organization[division]:
        return False, f"'{division} › {team}' 을 찾을 수 없습니다."
    if division == config.ADMIN_DIVISION and team == config.ADMIN_TEAM:
        return False, (
            f"'{team}' 을 삭제하면 통합 보고서 화면에 들어갈 수 없습니다. "
            "삭제하려면 먼저 config.py 의 ADMIN_TEAM 을 바꿔 주세요."
        )

    organization[division].remove(team)
    save_organization(organization)
    return True, f"'{division} › {team}' 을 삭제했습니다."


def rename_team(division: str, old: str, new: str) -> tuple[bool, str]:
    new = new.strip()
    if not new:
        return False, "새 팀 이름을 입력해 주세요."

    organization = load_organization()
    if division not in organization or old not in organization[division]:
        return False, f"'{division} › {old}' 을 찾을 수 없습니다."
    if new in organization[division]:
        return False, f"'{division}' 에 '{new}' 이 이미 있습니다."

    index = organization[division].index(old)
    organization[division][index] = new
    save_organization(organization)
    return True, f"'{old}' 을 '{new}' 으로 변경했습니다."


def reset_to_default() -> None:
    """config.py 의 기본 조직도로 되돌린다."""
    if os.path.exists(_path()):
        os.remove(_path())
