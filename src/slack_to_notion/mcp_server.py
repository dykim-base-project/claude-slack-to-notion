"""Slack-to-Notion MCP 서버.

FastMCP를 사용하여 Slack 메시지 수집 기능을 MCP 도구로 제공한다.
"""

import json
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

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

# SlackClient 인스턴스 (lazy init)
_slack_client: SlackClient | None = None


def _get_slack_client() -> SlackClient:
    """SlackClient 인스턴스를 반환한다. 없으면 초기화.

    Returns:
        SlackClient 인스턴스

    Raises:
        RuntimeError: SLACK_BOT_TOKEN이 설정되지 않은 경우
    """
    global _slack_client
    if _slack_client is None:
        token = os.environ.get("SLACK_BOT_TOKEN")
        if not token:
            raise RuntimeError(
                "SLACK_BOT_TOKEN 환경변수가 설정되지 않았습니다. "
                ".mcp.json 파일의 env 섹션을 확인하세요."
            )
        _slack_client = SlackClient(token)
        logger.info("SlackClient 초기화 완료")
    return _slack_client


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
        return json.dumps(channels, ensure_ascii=False, indent=2)
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
        messages = client.fetch_channel_messages(channel_id, limit, oldest)
        return json.dumps(messages, ensure_ascii=False, indent=2)
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
        return json.dumps(messages, ensure_ascii=False, indent=2)
    except SlackClientError as e:
        return f"[에러] {e.message}"
    except Exception as e:
        logger.exception("예상치 못한 에러 발생")
        return f"[에러] 스레드 조회 실패: {e!s}"


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
        return json.dumps(info, ensure_ascii=False, indent=2)
    except SlackClientError as e:
        return f"[에러] {e.message}"
    except Exception as e:
        logger.exception("예상치 못한 에러 발생")
        return f"[에러] 채널 정보 조회 실패: {e!s}"


if __name__ == "__main__":
    logger.info("Slack-to-Notion MCP 서버 시작")
    mcp.run()
