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
        with patch("slack_to_notion.slack_client.WebClient"):
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


class TestSlackClientListDMs:
    """DM 목록 조회 테스트."""

    def setup_method(self):
        with patch("slack_to_notion.slack_client.WebClient"):
            self.client = SlackClient("xoxb-fake-token")
            self.mock_api = self.client.client

    def test_list_dms_success(self):
        """im + mpim 모두 정상 반환, 이름 포맷 확인."""
        self.mock_api.conversations_list.return_value = {
            "channels": [
                {"id": "D001", "user": "U001", "is_mpim": False},
                {"id": "G001", "name": "mpdm-alice--bob-1", "is_mpim": True},
            ],
            "response_metadata": {"next_cursor": ""},
        }
        self.mock_api.users_info.return_value = {
            "user": {"profile": {"display_name": "김동영", "real_name": ""}}
        }

        dms = self.client.list_dms()
        assert len(dms) == 2
        assert dms[0]["id"] == "D001"
        assert dms[0]["name"] == "DM: 김동영"
        assert dms[0]["is_dm"] is True
        assert dms[0]["is_group_dm"] is False
        assert dms[1]["id"] == "G001"
        assert dms[1]["name"] == "Group DM: alice, bob"
        assert dms[1]["is_group_dm"] is True

    def test_list_dms_im_only_fallback(self):
        """im,mpim 실패 → im only 폴백."""
        call_count = 0

        def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            types = kwargs.get("types", "")
            limit = kwargs.get("limit", 200)
            if call_count == 1 and types == "im,mpim" and limit == 1:
                raise _make_slack_error("missing_scope")
            if call_count == 2 and types == "im" and limit == 1:
                return {"channels": [], "response_metadata": {"next_cursor": ""}}
            return {
                "channels": [
                    {"id": "D001", "user": "U001", "is_mpim": False},
                ],
                "response_metadata": {"next_cursor": ""},
            }

        self.mock_api.conversations_list.side_effect = side_effect
        self.mock_api.users_info.return_value = {
            "user": {"profile": {"display_name": "테스트", "real_name": ""}}
        }

        dms = self.client.list_dms()
        assert len(dms) == 1
        # 세 번째 호출(실제 목록 조회)에서 im만 사용 확인
        third_call_kwargs = self.mock_api.conversations_list.call_args_list[2][1]
        assert third_call_kwargs["types"] == "im"

    def test_list_dms_no_scope_raises(self):
        """모든 스코프 없음 → SlackClientError."""
        self.mock_api.conversations_list.side_effect = _make_slack_error("missing_scope")

        with pytest.raises(SlackClientError) as exc_info:
            self.client.list_dms()
        assert "im:read" in exc_info.value.message

    def test_list_dms_pagination(self):
        """페이지네이션 커서 동작."""
        self.mock_api.conversations_list.side_effect = [
            # scope 확인 호출
            {"channels": [], "response_metadata": {"next_cursor": ""}},
            # 첫 페이지
            {
                "channels": [{"id": "D001", "user": "U001", "is_mpim": False}],
                "response_metadata": {"next_cursor": "cursor_abc"},
            },
            # 두 번째 페이지
            {
                "channels": [{"id": "D002", "user": "U002", "is_mpim": False}],
                "response_metadata": {"next_cursor": ""},
            },
        ]
        self.mock_api.users_info.return_value = {
            "user": {"profile": {"display_name": "유저", "real_name": ""}}
        }

        dms = self.client.list_dms()
        assert len(dms) == 2
        assert dms[0]["id"] == "D001"
        assert dms[1]["id"] == "D002"

    def test_list_dms_user_name_resolved(self):
        """1:1 DM에서 get_user_name 호출 확인."""
        self.mock_api.conversations_list.return_value = {
            "channels": [
                {"id": "D001", "user": "U001", "is_mpim": False},
            ],
            "response_metadata": {"next_cursor": ""},
        }
        self.mock_api.users_info.return_value = {
            "user": {"profile": {"display_name": "홍길동", "real_name": ""}}
        }

        dms = self.client.list_dms()
        assert dms[0]["name"] == "DM: 홍길동"
        self.mock_api.users_info.assert_called_once_with(user="U001")

    def test_list_dms_group_dm_name_formatted(self):
        """mpdm-a--b--1 → 'Group DM: a, b'."""
        self.mock_api.conversations_list.return_value = {
            "channels": [
                {"id": "G001", "name": "mpdm-alice--bob--charlie-1", "is_mpim": True},
            ],
            "response_metadata": {"next_cursor": ""},
        }

        dms = self.client.list_dms()
        assert dms[0]["name"] == "Group DM: alice, bob, charlie"
        assert dms[0]["is_group_dm"] is True


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


class TestListUsers:
    """사용자 목록 조회 테스트."""

    def setup_method(self):
        with patch("slack_to_notion.slack_client.WebClient"):
            self.client = SlackClient("xoxb-fake-token")
            self.mock_api = self.client.client

    def test_list_users_success(self):
        self.mock_api.users_list.return_value = {
            "members": [
                {"id": "U001", "real_name": "Kim", "profile": {"display_name": "김동영", "real_name": "Kim"}},
                {"id": "U002", "real_name": "Lee", "profile": {"display_name": "이철수", "real_name": "Lee"}},
            ],
            "response_metadata": {"next_cursor": ""},
        }
        users = self.client.list_users()
        assert len(users) == 2
        assert users[0]["id"] == "U001"
        assert users[0]["name"] == "김동영"

    def test_list_users_excludes_bots(self):
        self.mock_api.users_list.return_value = {
            "members": [
                {"id": "U001", "real_name": "Kim", "is_bot": False, "profile": {"display_name": "김동영"}},
                {"id": "U002", "real_name": "Bot", "is_bot": True, "profile": {"display_name": "봇"}},
                {"id": "USLACKBOT", "real_name": "Slackbot", "profile": {"display_name": "Slackbot"}},
                {"id": "U003", "real_name": "Del", "deleted": True, "profile": {"display_name": "삭제됨"}},
            ],
            "response_metadata": {"next_cursor": ""},
        }
        users = self.client.list_users()
        assert len(users) == 1
        assert users[0]["id"] == "U001"

    def test_list_users_caches_names(self):
        self.mock_api.users_list.return_value = {
            "members": [
                {"id": "U001", "real_name": "Kim", "profile": {"display_name": "김동영"}},
            ],
            "response_metadata": {"next_cursor": ""},
        }
        self.client.list_users()
        assert self.client._user_cache["U001"] == "김동영"


class TestGetUserPresence:
    """사용자 온라인 상태 조회 테스트."""

    def setup_method(self):
        with patch("slack_to_notion.slack_client.WebClient"):
            self.client = SlackClient("xoxb-fake-token")
            self.mock_api = self.client.client

    def test_active_presence(self):
        self.mock_api.users_getPresence.return_value = {"ok": True, "presence": "active"}
        assert self.client.get_user_presence("U001") == "active"

    def test_away_presence(self):
        self.mock_api.users_getPresence.return_value = {"ok": True, "presence": "away"}
        assert self.client.get_user_presence("U001") == "away"

    def test_api_error_raises(self):
        self.mock_api.users_getPresence.side_effect = _make_slack_error("user_not_found")
        with pytest.raises(SlackClientError):
            self.client.get_user_presence("U999")


class TestGetActiveUsers:
    """로그인한 사용자 조회 테스트."""

    def setup_method(self):
        with patch("slack_to_notion.slack_client.WebClient"):
            self.client = SlackClient("xoxb-fake-token")
            self.mock_api = self.client.client

    def test_returns_only_active_users(self):
        self.mock_api.users_list.return_value = {
            "members": [
                {"id": "U001", "real_name": "Kim", "profile": {"display_name": "김동영"}},
                {"id": "U002", "real_name": "Lee", "profile": {"display_name": "이철수"}},
                {"id": "U003", "real_name": "Park", "profile": {"display_name": "박영희"}},
            ],
            "response_metadata": {"next_cursor": ""},
        }

        def presence_side_effect(user):
            statuses = {"U001": "active", "U002": "away", "U003": "active"}
            return {"ok": True, "presence": statuses.get(user, "away")}

        self.mock_api.users_getPresence.side_effect = presence_side_effect
        active = self.client.get_active_users()
        assert len(active) == 2
        assert active[0]["name"] == "김동영"
        assert active[1]["name"] == "박영희"
        assert all(u["presence"] == "active" for u in active)

    def test_skips_presence_errors(self):
        """개별 사용자 presence 조회 실패 시 건너뛴다."""
        self.mock_api.users_list.return_value = {
            "members": [
                {"id": "U001", "real_name": "Kim", "profile": {"display_name": "김동영"}},
                {"id": "U002", "real_name": "Lee", "profile": {"display_name": "이철수"}},
            ],
            "response_metadata": {"next_cursor": ""},
        }

        def presence_side_effect(user):
            if user == "U001":
                return {"ok": True, "presence": "active"}
            raise _make_slack_error("user_not_found")

        self.mock_api.users_getPresence.side_effect = presence_side_effect
        active = self.client.get_active_users()
        assert len(active) == 1
        assert active[0]["id"] == "U001"


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


class TestResolveMentionsInText:
    """메시지 텍스트 내 멘션 치환 테스트."""

    def setup_method(self):
        with patch("slack_to_notion.slack_client.WebClient"):
            self.client = SlackClient("xoxb-fake-token")
            self.mock_api = self.client.client

    def test_single_mention_replaced(self):
        """<@U001> → @김동영 치환."""
        self.mock_api.users_info.return_value = {
            "user": {"profile": {"display_name": "김동영", "real_name": ""}}
        }
        result = self.client._resolve_mentions("안녕 <@U001>님")
        assert result == "안녕 @김동영님"

    def test_multiple_mentions_replaced(self):
        """여러 멘션 각각 치환."""
        def users_info_side_effect(user):
            names = {"U001": "김동영", "U002": "이철수"}
            return {"user": {"profile": {"display_name": names.get(user, ""), "real_name": ""}}}

        self.mock_api.users_info.side_effect = users_info_side_effect
        result = self.client._resolve_mentions("<@U001>과 <@U002>에게 전달")
        assert result == "@김동영과 @이철수에게 전달"

    def test_unknown_user_falls_back_to_id(self):
        """API 실패 시 @U999로 폴백."""
        self.mock_api.users_info.side_effect = _make_slack_error("user_not_found")
        result = self.client._resolve_mentions("확인 부탁 <@U999>")
        assert result == "확인 부탁 @U999"

    def test_no_mentions_unchanged(self):
        """멘션 없으면 원본 유지, API 미호출."""
        result = self.client._resolve_mentions("멘션 없는 메시지")
        assert result == "멘션 없는 메시지"
        self.mock_api.users_info.assert_not_called()

    def test_duplicate_mention_uses_cache(self):
        """동일 사용자 반복 시 API 1회만 호출."""
        self.mock_api.users_info.return_value = {
            "user": {"profile": {"display_name": "김동영", "real_name": ""}}
        }
        result = self.client._resolve_mentions("<@U001> said to <@U001>")
        assert result == "@김동영 said to @김동영"
        assert self.mock_api.users_info.call_count == 1

    def test_resolve_user_names_sets_resolved_text(self):
        """resolve_user_names가 resolved_text 필드를 추가하고 원본 text를 보존."""
        self.mock_api.users_info.return_value = {
            "user": {"profile": {"display_name": "김동영", "real_name": ""}}
        }
        messages = [{"user": "U001", "text": "확인 <@U001>"}]
        result = self.client.resolve_user_names(messages)
        assert result[0]["resolved_text"] == "확인 @김동영"
        assert result[0]["text"] == "확인 <@U001>"  # 원본 보존

    def test_resolve_user_names_no_text(self):
        """text 없으면 resolved_text 미추가."""
        self.mock_api.users_info.return_value = {
            "user": {"profile": {"display_name": "김동영", "real_name": ""}}
        }
        messages = [{"user": "U001"}]
        result = self.client.resolve_user_names(messages)
        assert "resolved_text" not in result[0]
