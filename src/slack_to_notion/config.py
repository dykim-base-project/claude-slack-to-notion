"""환경변수 설정 관리.

플러그인 모드: .mcp.json의 env 섹션에서 환경변수 주입
독립 실행 모드: export 또는 .env 파일로 환경변수 설정
"""

import os


def load_config() -> dict:
    """환경변수를 검증하고 설정값을 반환한다.

    Returns:
        설정값 딕셔너리

    Raises:
        SystemExit: 필수 환경변수가 누락된 경우 (비개발자 안내 메시지 포함)
    """
    required_vars = {
        "SLACK_BOT_TOKEN": "Slack Bot 토큰",
        "NOTION_API_KEY": "Notion API 키",
        "NOTION_PARENT_PAGE_ID": "Notion 상위 페이지 ID",
    }

    config = {}
    missing = []

    for var, description in required_vars.items():
        value = os.environ.get(var)
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
        print("  export SLACK_BOT_TOKEN=\"xoxb-...\"")
        print("  export NOTION_API_KEY=\"secret_...\"")
        print("  export NOTION_PARENT_PAGE_ID=\"...\"")
        print("\n자세한 발급 방법은 README.md를 참고하세요.\n")
        raise SystemExit(1)

    return config
