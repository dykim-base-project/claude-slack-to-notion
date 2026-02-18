"""Slack 클라이언트 단위 테스트."""

from unittest.mock import MagicMock, patch

import pytest
from slack_sdk.errors import SlackApiError

from slack_to_notion.slack_client import SlackClient, SlackClientError


def _make_slack_error(error_code: str) -> SlackApiError:
    """테스트용 SlackApiError 생성."""
    response = MagicMock()
    response.get.side_effect = lambda key, default="": error_code if key == "error" else default
    response.__getitem__ = lambda self, key: error_code if key == "error" else ""
    return SlackApiError(message=f"Error: {error_code}", response=response)


class TestSlackClientErrorFormatting:
    """에러 메시지 변환 테스트."""

    def setup_method(self):
        with patch("slack_to_notion.slack_client.WebClient"):
            self.client = SlackClient("xoxb-fake-token")

    def test_invalid_auth(self):
        msg = self.client._format_error_message(_make_slack_error("invalid_auth"))
        assert "토큰이 올바르지 않습니다" in msg

    def test_not_authed(self):
        msg = self.client._format_error_message(_make_slack_error("not_authed"))
        assert "토큰이 올바르지 않습니다" in msg

    def test_channel_not_found(self):
        msg = self.client._format_error_message(_make_slack_error("channel_not_found"))
        assert "초대되어 있지 않습니다" in msg

    def test_not_in_channel(self):
        msg = self.client._format_error_message(_make_slack_error("not_in_channel"))
        assert "초대되어 있지 않습니다" in msg

    def test_missing_scope(self):
        msg = self.client._format_error_message(_make_slack_error("missing_scope"))
        assert "권한이 없습니다" in msg

    def test_unknown_error(self):
        msg = self.client._format_error_message(_make_slack_error("some_other_error"))
        assert "some_other_error" in msg


class TestSlackClientListChannels:
    """채널 목록 조회 테스트."""

    def setup_method(self):
        with patch("slack_to_notion.slack_client.WebClient") as mock_cls:
            self.client = SlackClient("xoxb-fake-token")
            self.mock_api = self.client.client

    def test_list_channels_success(self):
        self.mock_api.conversations_list.return_value = {
            "channels": [
                {"id": "C001", "name": "general", "topic": {"value": "일반"}, "num_members": 10},
                {"id": "C002", "name": "random", "topic": {"value": ""}, "num_members": 5},
            ],
            "response_metadata": {"next_cursor": ""},
        }
        channels = self.client.list_channels()
        assert len(channels) == 2
        assert channels[0]["id"] == "C001"
        assert channels[0]["name"] == "general"
        assert channels[0]["topic"] == "일반"
        assert channels[1]["num_members"] == 5

    def test_list_channels_groups_read_fallback(self):
        """groups:read 스코프 없을 때 public_channel로 fallback."""
        call_count = 0

        def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # 첫 호출 (scope 확인): missing_scope 에러
                raise _make_slack_error("missing_scope")
            # 이후 호출: 정상 응답
            return {
                "channels": [
                    {"id": "C001", "name": "general", "topic": {"value": ""}, "num_members": 3},
                ],
                "response_metadata": {"next_cursor": ""},
            }

        self.mock_api.conversations_list.side_effect = side_effect
        channels = self.client.list_channels()
        assert len(channels) == 1

        # 두 번째 호출(실제 목록 조회)에서 public_channel만 사용 확인
        second_call_kwargs = self.mock_api.conversations_list.call_args_list[1][1]
        assert second_call_kwargs["types"] == "public_channel"

    def test_list_channels_pagination(self):
        """페이지네이션 테스트."""
        self.mock_api.conversations_list.side_effect = [
            # scope 확인 호출
            {"channels": [], "response_metadata": {"next_cursor": ""}},
            # 첫 페이지
            {
                "channels": [{"id": "C001", "name": "ch1", "topic": {"value": ""}, "num_members": 1}],
                "response_metadata": {"next_cursor": "cursor123"},
            },
            # 두 번째 페이지
            {
                "channels": [{"id": "C002", "name": "ch2", "topic": {"value": ""}, "num_members": 2}],
                "response_metadata": {"next_cursor": ""},
            },
        ]
        channels = self.client.list_channels()
        assert len(channels) == 2
        assert channels[0]["name"] == "ch1"
        assert channels[1]["name"] == "ch2"


class TestSlackClientFetchMessages:
    """메시지 조회 테스트."""

    def setup_method(self):
        with patch("slack_to_notion.slack_client.WebClient"):
            self.client = SlackClient("xoxb-fake-token")
            self.mock_api = self.client.client

    def test_fetch_messages_success(self):
        self.mock_api.conversations_history.return_value = {
            "messages": [
                {"ts": "1234567890.123456", "user": "U001", "text": "안녕하세요"},
            ]
        }
        messages = self.client.fetch_channel_messages("C001")
        assert len(messages) == 1
        assert messages[0]["text"] == "안녕하세요"

    def test_fetch_messages_with_oldest(self):
        self.mock_api.conversations_history.return_value = {"messages": []}
        self.client.fetch_channel_messages("C001", limit=50, oldest="1234567890.000000")
        call_kwargs = self.mock_api.conversations_history.call_args[1]
        assert call_kwargs["oldest"] == "1234567890.000000"
        assert call_kwargs["limit"] == 50

    def test_fetch_messages_not_in_channel(self):
        self.mock_api.conversations_history.side_effect = _make_slack_error("not_in_channel")
        with pytest.raises(SlackClientError) as exc_info:
            self.client.fetch_channel_messages("C001")
        assert "초대되어 있지 않습니다" in exc_info.value.message

    def test_fetch_thread_success(self):
        self.mock_api.conversations_replies.return_value = {
            "messages": [
                {"ts": "1234567890.123456", "user": "U001", "text": "원본"},
                {"ts": "1234567890.123457", "user": "U002", "text": "답글"},
            ]
        }
        messages = self.client.fetch_thread_replies("C001", "1234567890.123456")
        assert len(messages) == 2

    def test_fetch_channel_info_success(self):
        self.mock_api.conversations_info.return_value = {
            "channel": {"id": "C001", "name": "general"}
        }
        info = self.client.fetch_channel_info("C001")
        assert info["name"] == "general"

    # ── fetch_channel_messages limit 경계값 ──

    def test_fetch_messages_limit_zero_calls_api_with_zero(self):
        """limit=0 으로 직접 API 호출 — SlackClient는 클램핑하지 않음(mcp_server가 담당)."""
        self.mock_api.conversations_history.return_value = {"messages": []}
        self.client.fetch_channel_messages("C001", limit=0)
        call_kwargs = self.mock_api.conversations_history.call_args[1]
        assert call_kwargs["limit"] == 0

    def test_fetch_messages_limit_negative_calls_api_with_negative(self):
        """limit 음수는 SlackClient에서 그대로 전달 — 클램핑은 mcp_server 담당."""
        self.mock_api.conversations_history.return_value = {"messages": []}
        self.client.fetch_channel_messages("C001", limit=-10)
        call_kwargs = self.mock_api.conversations_history.call_args[1]
        assert call_kwargs["limit"] == -10

    def test_fetch_messages_limit_1001_calls_api_with_1001(self):
        """limit=1001은 SlackClient에서 그대로 전달 — 클램핑은 mcp_server 담당."""
        self.mock_api.conversations_history.return_value = {"messages": []}
        self.client.fetch_channel_messages("C001", limit=1001)
        call_kwargs = self.mock_api.conversations_history.call_args[1]
        assert call_kwargs["limit"] == 1001

    # ── fetch_thread_replies thread_not_found ──

    def test_fetch_thread_not_found(self):
        """thread_not_found 에러 발생 시 SlackClientError로 변환."""
        self.mock_api.conversations_replies.side_effect = _make_slack_error("thread_not_found")
        with pytest.raises(SlackClientError) as exc_info:
            self.client.fetch_thread_replies("C001", "0000000000.000000")
        assert "스레드를 찾을 수 없습니다" in exc_info.value.message


class TestGetUserName:
    """사용자 이름 조회 테스트."""

    def setup_method(self):
        with patch("slack_to_notion.slack_client.WebClient"):
            self.client = SlackClient("xoxb-fake-token")
            self.mock_api = self.client.client

    def test_display_name(self):
        self.mock_api.users_info.return_value = {
            "user": {
                "real_name": "Kim Dongyoung",
                "profile": {"display_name": "김동영", "real_name": "Kim Dongyoung"},
            }
        }
        assert self.client.get_user_name("U001") == "김동영"

    def test_fallback_to_real_name(self):
        self.mock_api.users_info.return_value = {
            "user": {
                "real_name": "Kim Dongyoung",
                "profile": {"display_name": "", "real_name": "Kim Dongyoung"},
            }
        }
        assert self.client.get_user_name("U001") == "Kim Dongyoung"

    def test_fallback_to_user_real_name(self):
        self.mock_api.users_info.return_value = {
            "user": {
                "real_name": "Kim",
                "profile": {"display_name": "", "real_name": ""},
            }
        }
        assert self.client.get_user_name("U001") == "Kim"

    def test_fallback_to_user_id(self):
        self.mock_api.users_info.return_value = {
            "user": {
                "profile": {"display_name": "", "real_name": ""},
            }
        }
        assert self.client.get_user_name("U001") == "U001"

    def test_api_error_returns_user_id(self):
        self.mock_api.users_info.side_effect = _make_slack_error("user_not_found")
        assert self.client.get_user_name("U999") == "U999"

    def test_cache_prevents_duplicate_calls(self):
        self.mock_api.users_info.return_value = {
            "user": {"profile": {"display_name": "테스트", "real_name": ""}}
        }
        self.client.get_user_name("U001")
        self.client.get_user_name("U001")
        assert self.mock_api.users_info.call_count == 1

    def test_cache_error_result(self):
        """API 실패 시에도 캐시하여 재호출 방지."""
        self.mock_api.users_info.side_effect = _make_slack_error("user_not_found")
        self.client.get_user_name("U999")
        self.client.get_user_name("U999")
        assert self.mock_api.users_info.call_count == 1


class TestResolveUserNames:
    """메시지 리스트 사용자 이름 변환 테스트."""

    def setup_method(self):
        with patch("slack_to_notion.slack_client.WebClient"):
            self.client = SlackClient("xoxb-fake-token")
            self.mock_api = self.client.client

    def test_adds_user_name_field(self):
        self.mock_api.users_info.return_value = {
            "user": {"profile": {"display_name": "김동영", "real_name": ""}}
        }
        messages = [{"user": "U001", "text": "hello"}]
        result = self.client.resolve_user_names(messages)
        assert result[0]["user_name"] == "김동영"
        assert result[0]["user"] == "U001"  # 원본 유지

    def test_skips_messages_without_user(self):
        messages = [{"text": "system message"}]
        result = self.client.resolve_user_names(messages)
        assert "user_name" not in result[0]

    def test_multiple_users(self):
        def users_info_side_effect(user):
            names = {"U001": "김동영", "U002": "이철수"}
            return {"user": {"profile": {"display_name": names.get(user, ""), "real_name": ""}}}

        self.mock_api.users_info.side_effect = users_info_side_effect
        messages = [
            {"user": "U001", "text": "msg1"},
            {"user": "U002", "text": "msg2"},
            {"user": "U001", "text": "msg3"},
        ]
        result = self.client.resolve_user_names(messages)
        assert result[0]["user_name"] == "김동영"
        assert result[1]["user_name"] == "이철수"
        assert result[2]["user_name"] == "김동영"
        # U001은 캐시되어 1번만 호출
        assert self.mock_api.users_info.call_count == 2
