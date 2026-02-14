"""Slack 메시지 수집 모듈.

slack_sdk를 사용하여 채널 메시지와 스레드를 수집한다.
"""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler


class SlackClientError(Exception):
    """Slack 클라이언트 에러."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class SlackClient:
    """Slack API 클라이언트."""

    def __init__(self, token: str):
        """클라이언트 초기화.

        Args:
            token: Slack Bot 토큰
        """
        self.client = WebClient(token=token)
        retry_handler = RateLimitErrorRetryHandler(max_retry_count=3)
        self.client.retry_handlers.append(retry_handler)

    def list_channels(self) -> list[dict]:
        """채널 목록 조회.

        Returns:
            채널 정보 리스트 [{"id", "name", "topic", "num_members"}]

        Raises:
            SlackClientError: API 호출 실패 시
        """
        try:
            channels = []
            cursor = None

            while True:
                response = self.client.conversations_list(
                    types="public_channel,private_channel",
                    cursor=cursor,
                    limit=200,
                )

                for channel in response["channels"]:
                    channels.append({
                        "id": channel["id"],
                        "name": channel["name"],
                        "topic": channel.get("topic", {}).get("value", ""),
                        "num_members": channel.get("num_members", 0),
                    })

                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break

            return channels

        except SlackApiError as e:
            raise SlackClientError(self._format_error_message(e)) from e

    def fetch_channel_messages(
        self,
        channel_id: str,
        limit: int = 100,
        oldest: str | None = None,
    ) -> list[dict]:
        """채널 메시지 조회.

        Args:
            channel_id: 채널 ID
            limit: 조회할 메시지 수
            oldest: 시작 타임스탬프 (해당 시점 이후 메시지만 조회)

        Returns:
            메시지 리스트

        Raises:
            SlackClientError: API 호출 실패 시
        """
        try:
            kwargs = {"channel": channel_id, "limit": limit}
            if oldest:
                kwargs["oldest"] = oldest

            response = self.client.conversations_history(**kwargs)
            return response["messages"]

        except SlackApiError as e:
            raise SlackClientError(self._format_error_message(e)) from e

    def fetch_thread_replies(self, channel_id: str, thread_ts: str) -> list[dict]:
        """스레드 메시지 조회.

        Args:
            channel_id: 채널 ID
            thread_ts: 스레드 타임스탬프

        Returns:
            스레드 메시지 리스트

        Raises:
            SlackClientError: API 호출 실패 시
        """
        try:
            response = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
            )
            return response["messages"]

        except SlackApiError as e:
            raise SlackClientError(self._format_error_message(e)) from e

    def fetch_channel_info(self, channel_id: str) -> dict:
        """채널 정보 조회.

        Args:
            channel_id: 채널 ID

        Returns:
            채널 정보 dict

        Raises:
            SlackClientError: API 호출 실패 시
        """
        try:
            response = self.client.conversations_info(channel=channel_id)
            return response["channel"]

        except SlackApiError as e:
            raise SlackClientError(self._format_error_message(e)) from e

    def _format_error_message(self, error: SlackApiError) -> str:
        """API 에러를 사용자 친화적 메시지로 변환.

        Args:
            error: SlackApiError 객체

        Returns:
            한글 안내 메시지
        """
        error_code = error.response.get("error", "")

        if error_code in ("invalid_auth", "not_authed"):
            return "Slack 토큰이 올바르지 않습니다. .env 파일의 SLACK_BOT_TOKEN을 확인하세요."

        if error_code == "channel_not_found":
            return "채널을 찾을 수 없습니다. Bot이 해당 채널에 초대되어 있는지 확인하세요."

        if error_code == "missing_scope":
            return "Bot에 필요한 권한이 없습니다. Slack App 설정에서 channels:history, channels:read 권한을 추가하세요."

        return f"Slack API 오류가 발생했습니다: {error_code}. 자세한 내용은 README.md를 참고하세요."
