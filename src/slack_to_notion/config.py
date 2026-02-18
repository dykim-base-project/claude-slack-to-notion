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

    # Slack 토큰 검증: 봇 토큰 또는 사용자 토큰 중 하나 필수
    slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
    slack_user_token = os.environ.get("SLACK_USER_TOKEN")
    if not slack_bot_token and not slack_user_token:
        missing.append("  - SLACK_BOT_TOKEN 또는 SLACK_USER_TOKEN: Slack 토큰")

    if slack_bot_token:
        config["SLACK_BOT_TOKEN"] = slack_bot_token
    elif slack_user_token:
        config["SLACK_USER_TOKEN"] = slack_user_token

    if missing:
        print("\n[설정 오류] 필수 환경변수가 설정되지 않았습니다.\n")
        print("누락된 항목:")
        for item in missing:
            print(item)
        print("\n설정 방법:")
        print("  export SLACK_BOT_TOKEN=\"xoxb-...\"  # 봇 토큰 (권장)")
        print("  export SLACK_USER_TOKEN=\"xoxp-...\"  # 사용자 토큰 (대안)")
        print("  export NOTION_API_KEY=\"ntn_...\"  # 또는 secret_...")
        print("  export NOTION_PARENT_PAGE_ID=\"...\"")
        print("\n자세한 발급 방법은 README.md를 참고하세요.\n")
        raise SystemExit(1)

    return config
