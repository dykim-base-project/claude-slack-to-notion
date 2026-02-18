"""Slack-to-Notion MCP 서버.

FastMCP를 사용하여 Slack 수집 → 분석 → Notion 생성 기능을 MCP 도구로 제공한다.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .analyzer import (
    ANALYSIS_GUIDE_EXAMPLES,
    format_messages_for_analysis,
    format_threads_for_analysis,
    get_analysis_guide,
    list_history,
    load_preferences,
    save_preference,
    save_result,
)
from .notion_client import NotionClient, NotionClientError, extract_page_id
from .slack_client import SlackClient, SlackClientError

# stdout은 MCP 프로토콜용이므로 로깅은 stderr로
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# MCP 서버 인스턴스
mcp = FastMCP("slack-to-notion")

# 클라이언트 인스턴스 (lazy init)
_slack_client: SlackClient | None = None
_notion_client: NotionClient | None = None


def _get_slack_client() -> SlackClient:
    """SlackClient 인스턴스를 반환한다. 없으면 초기화.

    봇 토큰(SLACK_BOT_TOKEN)을 우선 사용하고, 없으면 사용자 토큰(SLACK_USER_TOKEN)을 사용한다.
    """
    global _slack_client
    if _slack_client is None:
        # 봇 토큰 우선, 없으면 사용자 토큰
        token = os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_USER_TOKEN")
        if not token:
            raise RuntimeError(
                "SLACK_BOT_TOKEN 또는 SLACK_USER_TOKEN 환경변수가 설정되지 않았습니다. "
                ".mcp.json 파일의 env 섹션을 확인하세요."
            )
        # 접두사로 토큰 타입 판별
        token_type = "user" if token.startswith("xoxp-") else "bot"
        _slack_client = SlackClient(token, token_type)
        logger.info("SlackClient 초기화 완료 (token_type=%s)", token_type)
    return _slack_client


def _get_notion_client() -> NotionClient:
    """NotionClient 인스턴스를 반환한다. 없으면 초기화."""
    global _notion_client
    if _notion_client is None:
        api_key = os.environ.get("NOTION_API_KEY")
        if not api_key:
            raise RuntimeError(
                "NOTION_API_KEY 환경변수가 설정되지 않았습니다. "
                ".mcp.json 파일의 env 섹션을 확인하세요."
            )
        _notion_client = NotionClient(api_key)
        logger.info("NotionClient 초기화 완료")
    return _notion_client


# ──────────────────────────────────────────────
# Slack 도구
# ──────────────────────────────────────────────


@mcp.tool()
def list_channels() -> str:
    """Slack 채널 목록을 조회한다.

    Returns:
        채널 정보 리스트를 JSON 형식 문자열로 반환
        [{"id": "C123", "name": "general", "topic": "...", "num_members": 10}]
    """
    try:
        client = _get_slack_client()
        channels = client.list_channels()
        return json.dumps(channels, ensure_ascii=False)
    except SlackClientError as e:
        return f"[에러] {e.message}"
    except Exception as e:
        logger.exception("예상치 못한 에러 발생")
        return f"[에러] 채널 목록 조회 실패: {e!s}"


@mcp.tool()
def fetch_messages(
    channel_id: str,
    limit: int = 100,
    oldest: str | None = None,
) -> str:
    """Slack 채널의 메시지를 조회한다.

    Args:
        channel_id: 채널 ID (예: C0123456789)
        limit: 조회할 메시지 수 (기본값: 100)
        oldest: 시작 타임스탬프 (해당 시점 이후 메시지만 조회)

    Returns:
        메시지 리스트를 JSON 형식 문자열로 반환
    """
    try:
        client = _get_slack_client()
        limit = max(1, min(limit, 1000))
        messages = client.fetch_channel_messages(channel_id, limit, oldest)
        client.resolve_user_names(messages)
        filtered = [
            {k: m[k] for k in ("ts", "user", "text", "reply_count", "thread_ts") if k in m}
            for m in messages
        ]
        return json.dumps(filtered, ensure_ascii=False)
    except SlackClientError as e:
        return f"[에러] {e.message}"
    except Exception as e:
        logger.exception("예상치 못한 에러 발생")
        return f"[에러] 메시지 조회 실패: {e!s}"


@mcp.tool()
def fetch_thread(channel_id: str, thread_ts: str) -> str:
    """Slack 스레드의 메시지를 조회한다.

    Args:
        channel_id: 채널 ID (예: C0123456789)
        thread_ts: 스레드 타임스탬프 (예: 1234567890.123456)

    Returns:
        스레드 메시지 리스트를 JSON 형식 문자열로 반환
    """
    try:
        client = _get_slack_client()
        messages = client.fetch_thread_replies(channel_id, thread_ts)
        client.resolve_user_names(messages)
        filtered = [
            {k: m[k] for k in ("ts", "user", "text", "reply_count", "thread_ts") if k in m}
            for m in messages
        ]
        return json.dumps(filtered, ensure_ascii=False)
    except SlackClientError as e:
        return f"[에러] {e.message}"
    except Exception as e:
        logger.exception("예상치 못한 에러 발생")
        return f"[에러] 스레드 조회 실패: {e!s}"


@mcp.tool()
def fetch_threads(
    channel_id: str,
    thread_ts_list: list[str],
    channel_name: str = "",
) -> str:
    """여러 Slack 스레드의 메시지를 한 번에 수집하고 AI 분석용으로 포맷팅한다.

    복수의 스레드를 입력받아 각 스레드의 댓글을 모두 수집한 뒤,
    AI가 분석할 수 있는 텍스트로 변환하여 반환한다.

    Args:
        channel_id: 채널 ID (예: C0123456789)
        thread_ts_list: 스레드 타임스탬프 리스트 (예: ["1234567890.123456", "1234567891.654321"])
        channel_name: 채널 이름 (포맷팅 헤더에 표시, 미지정 시 채널 ID 사용)

    Returns:
        AI 분석용으로 포맷팅된 복수 스레드 메시지 텍스트
    """
    try:
        client = _get_slack_client()
        display_name = channel_name or channel_id

        threads = []
        for thread_ts in thread_ts_list:
            try:
                messages = client.fetch_thread_replies(channel_id, thread_ts)
                client.resolve_user_names(messages)
                threads.append({"thread_ts": thread_ts, "messages": messages})
            except SlackClientError as e:
                threads.append({
                    "thread_ts": thread_ts,
                    "messages": [{"text": f"[수집 실패] {e.message}", "user": "system", "ts": thread_ts}],
                })

        return format_threads_for_analysis(threads, display_name)

    except SlackClientError as e:
        return f"[에러] {e.message}"
    except Exception as e:
        logger.exception("예상치 못한 에러 발생")
        return f"[에러] 스레드 수집 실패: {e!s}"


@mcp.tool()
def fetch_channel_info(channel_id: str) -> str:
    """Slack 채널의 상세 정보를 조회한다.

    Args:
        channel_id: 채널 ID (예: C0123456789)

    Returns:
        채널 정보를 JSON 형식 문자열로 반환
    """
    try:
        client = _get_slack_client()
        info = client.fetch_channel_info(channel_id)
        filtered = {k: info[k] for k in ("id", "name", "topic", "purpose", "num_members", "is_private") if k in info}
        return json.dumps(filtered, ensure_ascii=False)
    except SlackClientError as e:
        return f"[에러] {e.message}"
    except Exception as e:
        logger.exception("예상치 못한 에러 발생")
        return f"[에러] 채널 정보 조회 실패: {e!s}"


# ──────────────────────────────────────────────
# 분석 도구
# ──────────────────────────────────────────────


@mcp.tool()
def get_analysis_guide_tool() -> str:
    """분석 방향 안내를 반환한다.

    사용자에게 어떤 방식으로 정리할지 질문할 때 사용한다.
    예시와 팁을 포함한 안내 텍스트를 반환한다.

    Returns:
        분석 방향 안내 텍스트 (예시 포함)
    """
    return get_analysis_guide()


@mcp.tool()
def format_messages(
    channel_id: str,
    channel_name: str,
    limit: int = 100,
    oldest: str | None = None,
) -> str:
    """Slack 채널 메시지를 수집하고 AI 분석용 텍스트로 포맷팅한다.

    메시지 수집과 포맷팅을 한 번에 수행한다.

    Args:
        channel_id: 채널 ID (예: C0123456789)
        channel_name: 채널 이름 (포맷팅 헤더에 표시)
        limit: 조회할 메시지 수 (기본값: 100)
        oldest: 시작 타임스탬프 (해당 시점 이후 메시지만 조회)

    Returns:
        AI 분석용으로 포맷팅된 메시지 텍스트
    """
    try:
        client = _get_slack_client()
        messages = client.fetch_channel_messages(channel_id, limit, oldest)
        client.resolve_user_names(messages)
        return format_messages_for_analysis(messages, channel_name)
    except SlackClientError as e:
        return f"[에러] {e.message}"
    except Exception as e:
        logger.exception("예상치 못한 에러 발생")
        return f"[에러] 메시지 포맷팅 실패: {e!s}"


# ──────────────────────────────────────────────
# Notion 도구
# ──────────────────────────────────────────────


@mcp.tool()
def create_notion_page(
    title: str,
    content: str,
) -> str:
    """분석 결과를 Notion 페이지로 생성한다.

    자유 형식 텍스트(마크다운)를 Notion 블록으로 변환하여 페이지를 생성한다.
    동일 제목의 페이지가 이미 있으면 안내한다.

    Args:
        title: 페이지 제목 (예: "[general] 분석 결과 - 2024-01-15")
        content: 분석 결과 텍스트 (마크다운 형식 지원: #, ##, ###, -, *, **, `코드`, [링크](url), ~~취소선~~)

    Returns:
        생성된 Notion 페이지 URL 또는 에러 메시지
    """
    try:
        client = _get_notion_client()
        raw_page_id = os.environ.get("NOTION_PARENT_PAGE_ID")
        if not raw_page_id:
            return "[에러] NOTION_PARENT_PAGE_ID 환경변수가 설정되지 않았습니다."
        parent_page_id = extract_page_id(raw_page_id)

        # 중복 체크
        if client.check_duplicate(parent_page_id, title):
            return (
                f"[안내] 동일한 제목의 페이지가 이미 존재합니다: {title}. "
                f"제목을 변경하거나 기존 페이지를 확인하세요."
            )

        # 블록 변환 + 페이지 생성
        blocks = client.build_page_blocks(content)
        url = client.create_analysis_page(parent_page_id, title, blocks)
        return f"Notion 페이지가 생성되었습니다: {url}"

    except NotionClientError as e:
        return f"[에러] {e.message}"
    except Exception as e:
        logger.exception("예상치 못한 에러 발생")
        return f"[에러] Notion 페이지 생성 실패: {e!s}"


@mcp.tool()
def save_analysis_result(data_json: str, filename: str = "") -> str:
    """분석 결과를 로컬 JSON 파일로 백업한다.

    Notion 업로드 실패 시 재시도하거나, 분석 히스토리를 보관할 때 사용한다.

    Args:
        data_json: 저장할 데이터 (JSON 문자열)
        filename: 파일명 (미지정 시 타임스탬프 기반 자동 생성)

    Returns:
        저장된 파일 경로 또는 에러 메시지
    """
    try:
        data = json.loads(data_json)

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_{timestamp}.json"

        save_dir = Path(".claude/slack-to-notion/history")
        path = save_result(data, save_dir / filename)
        return f"분석 결과가 저장되었습니다: {path}"

    except json.JSONDecodeError:
        return "[에러] 유효하지 않은 JSON 형식입니다."
    except Exception as e:
        logger.exception("예상치 못한 에러 발생")
        return f"[에러] 저장 실패: {e!s}"


# ──────────────────────────────────────────────
# 커스터마이징 도구
# ──────────────────────────────────────────────


@mcp.tool()
def save_preference_tool(text: str) -> str:
    """사용자의 분석 선호도를 저장한다.

    사용자가 "기억해줘", "앞으로 ~해줘", "다음에는 ~방식으로" 등
    분석 방향에 대한 선호를 표현할 때 호출한다.

    Args:
        text: 저장할 선호도 (예: "회의록은 결정사항 위주로 정리해줘")

    Returns:
        저장 결과 메시지
    """
    try:
        path = save_preference(text)
        return f"선호도가 저장되었습니다: {text}"
    except Exception as e:
        logger.exception("선호도 저장 실패")
        return f"[에러] 선호도 저장 실패: {e!s}"


@mcp.tool()
def get_preferences() -> str:
    """저장된 분석 선호도를 조회한다.

    분석을 시작하기 전에 호출하여 사용자의 선호도를 확인한다.
    저장된 선호도가 있으면 분석 시 해당 방향을 반영한다.

    Returns:
        저장된 선호도 텍스트. 없으면 안내 메시지.
    """
    try:
        content = load_preferences()
        if not content:
            return "저장된 분석 선호도가 없습니다. 사용자에게 분석 방향을 질문하세요."
        return content
    except Exception as e:
        logger.exception("선호도 조회 실패")
        return f"[에러] 선호도 조회 실패: {e!s}"


@mcp.tool()
def list_analysis_history(limit: int = 10) -> str:
    """과거 분석 결과 히스토리를 조회한다.

    사용자가 "지난번처럼", "이전에 정리한 거" 등을 언급할 때 호출한다.
    save_analysis_result로 저장된 분석 결과 목록을 반환한다.

    Args:
        limit: 조회할 최대 건수 (기본값: 10)

    Returns:
        히스토리 목록 (파일명, 요약 포함)
    """
    try:
        history = list_history(limit)
        if not history:
            return "저장된 분석 히스토리가 없습니다."

        lines = [f"최근 분석 히스토리 ({len(history)}건):"]
        for i, item in enumerate(history, 1):
            summary = item["summary"] or "(요약 없음)"
            lines.append(f"  {i}. {item['filename']} - {summary}")
        return "\n".join(lines)
    except Exception as e:
        logger.exception("히스토리 조회 실패")
        return f"[에러] 히스토리 조회 실패: {e!s}"


def main():
    """MCP 서버 진입점. uvx 및 python -m 실행 시 호출된다."""
    if "--help" in sys.argv or "-h" in sys.argv:
        print("slack-to-notion-mcp — Slack 메시지를 Notion 페이지로 정리하는 MCP 서버")
        print()
        print("사용법:")
        print("  uvx slack-to-notion-mcp          MCP 서버 실행 (Claude Code가 자동 호출)")
        print("  uvx slack-to-notion-mcp --help    이 도움말 표시")
        print()
        print("설치:")
        print("  curl -sL https://raw.githubusercontent.com/dykim-base-project/")
        print("    claude-slack-to-notion/main/scripts/setup.sh | bash")
        print()
        print("자세한 내용:")
        print("  https://github.com/dykim-base-project/claude-slack-to-notion")
        return
    logger.info("Slack-to-Notion MCP 서버 시작")
    mcp.run()


if __name__ == "__main__":
    main()
