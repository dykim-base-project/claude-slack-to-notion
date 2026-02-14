"""환경변수 로딩 및 설정 관리."""

import os
from pathlib import Path

from dotenv import load_dotenv


def load_config() -> dict:
    """환경변수를 로딩하고 필수 값을 검증한다.

    Returns:
        설정값 딕셔너리

    Raises:
        SystemExit: 필수 환경변수가 누락된 경우 (비개발자 안내 메시지 포함)
    """
    env_path = Path.cwd() / ".env"
    load_dotenv(env_path)

    required_vars = {
        "SLACK_BOT_TOKEN": "Slack Bot 토큰",
        "NOTION_API_KEY": "Notion API 키",
        "NOTION_PARENT_PAGE_ID": "Notion 상위 페이지 ID",
    }

    config = {}
    missing = []

    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            missing.append(f"  - {var}: {description}")
        else:
            config[var] = value

    if missing:
        print("\n[설정 오류] 필수 환경변수가 설정되지 않았습니다.\n")
        print("누락된 항목:")
        for item in missing:
            print(item)
        print("\n설정 방법:")
        print("1. 프로젝트 루트의 .env.example 파일을 .env로 복사하세요")
        print("2. .env 파일을 열어 각 항목에 값을 입력하세요")
        print("3. 자세한 발급 방법은 README.md를 참고하세요\n")
        raise SystemExit(1)

    return config
