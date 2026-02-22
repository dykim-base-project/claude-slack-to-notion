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

    def __init__(self, token: str, token_type: str = "bot"):
        """클라이언트 초기화.

        Args:
            token: Slack 토큰 (봇 또는 사용자)
            token_type: 토큰 타입 ("bot" 또는 "user", 기본값 "bot")
        """
        self.client = WebClient(token=token)
        self.token_type = token_type
        self._user_cache: dict[str, str] = {}
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
            types = "public_channel,private_channel"

            try:
                # 비공개 채널 포함 조회 시도
                self.client.conversations_list(types=types, limit=1)
            except SlackApiError as e:
                if e.response.get("error") == "missing_scope":
                    types = "public_channel"
                else:
                    raise

            while True:
                response = self.client.conversations_list(
                    types=types,
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

    def get_user_name(self, user_id: str) -> str:
        """사용자 ID를 표시 이름으로 변환.

        캐시를 사용하여 동일 사용자에 대한 중복 API 호출을 방지한다.
        변환 실패 시 원본 user_id를 반환한다.

        Args:
            user_id: Slack 사용자 ID (예: U0AF00FUC30)

        Returns:
            표시 이름. 실패 시 원본 user_id.
        """
        if user_id in self._user_cache:
            return self._user_cache[user_id]

        try:
            response = self.client.users_info(user=user_id)
            user = response["user"]
            profile = user.get("profile", {})
            name = (
                profile.get("display_name")
                or profile.get("real_name")
                or user.get("real_name")
                or user_id
            )
            self._user_cache[user_id] = name
            return name
        except SlackApiError:
            self._user_cache[user_id] = user_id
            return user_id

    def list_users(self) -> list[dict]:
        """워크스페이스 전체 사용자 목록 조회.

        봇과 삭제된 사용자는 제외한다.

        Returns:
            사용자 정보 리스트 [{"id", "name", "real_name"}]

        Raises:
            SlackClientError: API 호출 실패 시
        """
        try:
            users = []
            cursor = None

            while True:
                response = self.client.users_list(cursor=cursor, limit=200)

                for user in response["members"]:
                    if user.get("is_bot") or user.get("deleted") or user.get("id") == "USLACKBOT":
                        continue
                    profile = user.get("profile", {})
                    name = (
                        profile.get("display_name")
                        or profile.get("real_name")
                        or user.get("real_name")
                        or user.get("id")
                    )
                    users.append({
                        "id": user["id"],
                        "name": name,
                        "real_name": user.get("real_name", ""),
                    })
                    self._user_cache[user["id"]] = name

                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break

            return users

        except SlackApiError as e:
            raise SlackClientError(self._format_error_message(e)) from e

    def get_user_presence(self, user_id: str) -> str:
        """사용자 온라인 상태 조회.

        Args:
            user_id: Slack 사용자 ID

        Returns:
            "active" 또는 "away"

        Raises:
            SlackClientError: API 호출 실패 시
        """
        try:
            response = self.client.users_getPresence(user=user_id)
            return response.get("presence", "away")
        except SlackApiError as e:
            raise SlackClientError(self._format_error_message(e)) from e

    def get_active_users(self) -> list[dict]:
        """현재 활성 상태인 사용자 목록 조회.

        워크스페이스 전체 사용자를 조회한 뒤, 각 사용자의
        온라인 상태를 확인하여 활성(active) 사용자만 반환한다.

        Returns:
            활성 사용자 리스트 [{"id", "name", "real_name", "presence"}]

        Raises:
            SlackClientError: API 호출 실패 시
        """
        users = self.list_users()
        active_users = []

        for user in users:
            try:
                presence = self.get_user_presence(user["id"])
                if presence == "active":
                    user["presence"] = presence
                    active_users.append(user)
            except SlackClientError:
                continue

        return active_users

    def resolve_user_names(self, messages: list[dict]) -> list[dict]:
        """메시지 리스트의 user ID를 표시 이름으로 변환.

        각 메시지에 user_name 필드를 추가한다.
        원본 user 필드는 유지된다.

        Args:
            messages: Slack 메시지 리스트

        Returns:
            user_name 필드가 추가된 메시지 리스트
        """
        for msg in messages:
            user_id = msg.get("user")
            if user_id:
                msg["user_name"] = self.get_user_name(user_id)
        return messages

    def _format_error_message(self, error: SlackApiError) -> str:
        """API 에러를 사용자 친화적 메시지로 변환.

        Args:
            error: SlackApiError 객체

        Returns:
            한글 안내 메시지
        """
        error_code = error.response.get("error", "")
        is_user_token = self.token_type == "user"

        if error_code in ("invalid_auth", "not_authed"):
            if is_user_token:
                return "Slack 토큰이 올바르지 않습니다. SLACK_USER_TOKEN 값을 확인하세요. 토큰은 xoxp-로 시작해야 합니다."
            return "Slack 토큰이 올바르지 않습니다. SLACK_BOT_TOKEN 값을 확인하세요. 토큰은 xoxb-로 시작해야 합니다."

        if error_code in ("channel_not_found", "not_in_channel"):
            if is_user_token:
                return "해당 채널에 접근 권한이 없습니다. Slack에서 채널에 참여해 있는지 확인하세요."
            return "Bot이 해당 채널에 초대되어 있지 않습니다. 채널 설정 → Integrations → Add apps에서 Bot을 추가하세요."

        if error_code == "missing_scope":
            if is_user_token:
                return "사용자 토큰에 필요한 권한이 없습니다. Slack App 설정에서 User Token Scopes를 추가하세요."
            return "Bot에 필요한 권한이 없습니다. Slack App 설정에서 channels:history, channels:read 권한을 추가하세요."

        if error_code == "thread_not_found":
            return "해당 스레드를 찾을 수 없습니다. 스레드 타임스탬프가 올바른지 확인하세요."

        return f"예상치 못한 오류가 발생했습니다 ({error_code}). 문제가 지속되면 README.md를 참고하세요."
