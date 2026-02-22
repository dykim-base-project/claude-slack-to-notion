"""MCP 서버 도구 단위 테스트."""

import sys
from unittest.mock import MagicMock, patch

import pytest


class TestCreateNotionPage:
    """create_notion_page 도구 테스트."""

    def _call_tool(self, title, content, env_vars=None):
        """create_notion_page를 환경변수와 mock으로 호출."""
        env = {
            "NOTION_API_KEY": "fake-key",
            "NOTION_PARENT_PAGE_URL": "https://www.notion.so/abc123def456abc123def456abc123de?source=copy_link",
        }
        if env_vars:
            env.update(env_vars)

        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._notion_client", None), \
             patch("slack_to_notion.notion_client.Client") as mock_cls:
            mock_api = mock_cls.return_value
            mock_api.blocks.children.list.return_value = {"results": []}
            mock_api.pages.create.return_value = {"id": "fake-page-id", "url": "https://notion.so/created-page"}

            from slack_to_notion.mcp_server import create_notion_page
            result = create_notion_page(title, content)
            return result, mock_api

    def test_success(self):
        result, mock_api = self._call_tool("테스트 제목", "# 내용\n본문")
        assert "생성되었습니다" in result
        assert "https://notion.so/created-page" in result

    def test_duplicate_detection(self):
        env = {
            "NOTION_API_KEY": "fake-key",
            "NOTION_PARENT_PAGE_URL": "abc123def456abc123def456abc123de",
        }
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._notion_client", None), \
             patch("slack_to_notion.notion_client.Client") as mock_cls:
            mock_api = mock_cls.return_value
            mock_api.blocks.children.list.return_value = {
                "results": [
                    {"type": "child_page", "child_page": {"title": "중복 제목"}},
                ]
            }
            from slack_to_notion.mcp_server import create_notion_page
            result = create_notion_page("중복 제목", "내용")
            assert "이미 존재합니다" in result

    def test_missing_env_var(self):
        env = {"NOTION_API_KEY": "fake-key"}
        with patch.dict("os.environ", env, clear=True), \
             patch("slack_to_notion.mcp_server._notion_client", None):
            from slack_to_notion.mcp_server import create_notion_page
            result = create_notion_page("제목", "내용")
            assert "NOTION_PARENT_PAGE_URL" in result
            assert "에러" in result


class TestFetchThreads:
    """fetch_threads 도구 테스트."""

    def test_multiple_threads(self):
        env = {"SLACK_BOT_TOKEN": "xoxb-fake"}
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._slack_client", None), \
             patch("slack_to_notion.slack_client.WebClient") as mock_cls:
            mock_api = mock_cls.return_value
            mock_api.conversations_replies.side_effect = [
                {"messages": [
                    {"ts": "100.0", "user": "U001", "text": "스레드1 주제"},
                    {"ts": "100.1", "user": "U002", "text": "답글"},
                ]},
                {"messages": [
                    {"ts": "200.0", "user": "U003", "text": "스레드2 주제"},
                ]},
            ]

            from slack_to_notion.mcp_server import fetch_threads
            result = fetch_threads("C001", ["100.0", "200.0"], "테스트채널")
            assert "Thread count: 2" in result
            assert "Total messages: 3" in result
            assert "스레드1 주제" in result
            assert "스레드2 주제" in result

    def test_partial_failure(self):
        """일부 스레드 수집 실패 시 나머지는 정상 수집."""
        env = {"SLACK_BOT_TOKEN": "xoxb-fake"}
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._slack_client", None), \
             patch("slack_to_notion.slack_client.WebClient") as mock_cls:
            mock_api = mock_cls.return_value

            from slack_sdk.errors import SlackApiError
            error_response = MagicMock()
            error_response.get.side_effect = lambda key, default="": "not_in_channel" if key == "error" else default

            mock_api.conversations_replies.side_effect = [
                SlackApiError(message="err", response=error_response),
                {"messages": [
                    {"ts": "200.0", "user": "U003", "text": "정상 스레드"},
                ]},
            ]

            from slack_to_notion.mcp_server import fetch_threads
            result = fetch_threads("C001", ["100.0", "200.0"], "ch")
            assert "Thread count: 2" in result
            assert "수집 실패" in result
            assert "정상 스레드" in result

    def test_channel_name_fallback(self):
        """channel_name 미지정 시 channel_id 사용."""
        env = {"SLACK_BOT_TOKEN": "xoxb-fake"}
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._slack_client", None), \
             patch("slack_to_notion.slack_client.WebClient") as mock_cls:
            mock_api = mock_cls.return_value
            mock_api.conversations_replies.return_value = {
                "messages": [{"ts": "100.0", "user": "U001", "text": "test"}]
            }

            from slack_to_notion.mcp_server import fetch_threads
            result = fetch_threads("C0AF01XMZB8", ["100.0"])
            assert "Channel: C0AF01XMZB8" in result


class TestSavePreferenceTool:
    """save_preference_tool 도구 테스트."""

    def test_success(self, tmp_path):
        pref_path = tmp_path / "preferences.md"
        with patch("slack_to_notion.mcp_server.save_preference") as mock_save:
            mock_save.return_value = pref_path
            from slack_to_notion.mcp_server import save_preference_tool
            result = save_preference_tool("회의록 위주로 정리해줘")
            assert "저장되었습니다" in result
            mock_save.assert_called_once_with("회의록 위주로 정리해줘")


class TestGetPreferences:
    """get_preferences 도구 테스트."""

    def test_with_preferences(self):
        with patch("slack_to_notion.mcp_server.load_preferences") as mock_load:
            mock_load.return_value = "## 분석 선호도\n\n- [2026-02-16] 결정사항 위주로\n"
            from slack_to_notion.mcp_server import get_preferences
            result = get_preferences()
            assert "분석 선호도" in result

    def test_empty(self):
        with patch("slack_to_notion.mcp_server.load_preferences") as mock_load:
            mock_load.return_value = ""
            from slack_to_notion.mcp_server import get_preferences
            result = get_preferences()
            assert "없습니다" in result


class TestListAnalysisHistory:
    """list_analysis_history 도구 테스트."""

    def test_with_history(self):
        with patch("slack_to_notion.mcp_server.list_history") as mock_list:
            mock_list.return_value = [
                {"filename": "analysis_20260216.json", "path": "/tmp/a.json", "summary": "마케팅 분석"},
            ]
            from slack_to_notion.mcp_server import list_analysis_history
            result = list_analysis_history()
            assert "1건" in result
            assert "마케팅 분석" in result

    def test_empty(self):
        with patch("slack_to_notion.mcp_server.list_history") as mock_list:
            mock_list.return_value = []
            from slack_to_notion.mcp_server import list_analysis_history
            result = list_analysis_history()
            assert "없습니다" in result


class TestCreateNotionPageBlockConversion:
    """페이지 생성 시 블록 변환이 올바르게 전달되는지 테스트."""

    def test_blocks_passed_to_api(self):
        env = {
            "NOTION_API_KEY": "fake-key",
            "NOTION_PARENT_PAGE_URL": "abc123def456abc123def456abc123de",
        }
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._notion_client", None), \
             patch("slack_to_notion.notion_client.Client") as mock_cls:
            mock_api = mock_cls.return_value
            mock_api.blocks.children.list.return_value = {"results": []}
            mock_api.pages.create.return_value = {"id": "fake-page-id", "url": "https://notion.so/page"}

            from slack_to_notion.mcp_server import create_notion_page
            create_notion_page("제목", "# 헤딩\n- 항목")

            call_kwargs = mock_api.pages.create.call_args[1]
            children = call_kwargs["children"]
            assert len(children) == 2
            assert children[0]["type"] == "heading_1"
            assert children[1]["type"] == "bulleted_list_item"


# ──────────────────────────────────────────────
# 에러 케이스 보강
# ──────────────────────────────────────────────


class TestListChannelsErrors:
    """list_channels 에러 처리 테스트."""

    def test_slack_client_error(self):
        """SlackClientError 발생 시 에러 메시지 반환."""
        env = {"SLACK_BOT_TOKEN": "xoxb-fake"}
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._slack_client", None), \
             patch("slack_to_notion.slack_client.WebClient") as mock_cls:
            from slack_sdk.errors import SlackApiError
            error_response = MagicMock()
            error_response.get.side_effect = lambda key, default="": "invalid_auth" if key == "error" else default
            mock_cls.return_value.conversations_list.side_effect = SlackApiError(
                message="err", response=error_response
            )

            from slack_to_notion.mcp_server import list_channels
            result = list_channels()
            assert "[에러]" in result

    def test_unexpected_exception(self):
        """예상치 못한 예외 발생 시 에러 메시지 반환."""
        env = {"SLACK_BOT_TOKEN": "xoxb-fake"}
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._slack_client", None), \
             patch("slack_to_notion.slack_client.WebClient") as mock_cls:
            mock_cls.return_value.conversations_list.side_effect = RuntimeError("네트워크 오류")

            from slack_to_notion.mcp_server import list_channels
            result = list_channels()
            assert "[에러]" in result

    def test_missing_token(self):
        """토큰 미설정 시 에러 메시지 반환."""
        with patch.dict("os.environ", {}, clear=True), \
             patch("slack_to_notion.mcp_server._slack_client", None):
            from slack_to_notion.mcp_server import list_channels
            result = list_channels()
            assert "[에러]" in result


class TestFetchMessagesErrors:
    """fetch_messages 에러 처리 테스트."""

    def _setup_env(self):
        return {"SLACK_BOT_TOKEN": "xoxb-fake"}

    def test_invalid_channel_id(self):
        """잘못된 channel_id로 조회 시 에러 메시지 반환."""
        env = self._setup_env()
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._slack_client", None), \
             patch("slack_to_notion.slack_client.WebClient") as mock_cls:
            from slack_sdk.errors import SlackApiError
            error_response = MagicMock()
            error_response.get.side_effect = lambda key, default="": "channel_not_found" if key == "error" else default
            mock_cls.return_value.conversations_history.side_effect = SlackApiError(
                message="err", response=error_response
            )

            from slack_to_notion.mcp_server import fetch_messages
            result = fetch_messages("INVALID_ID")
            assert "[에러]" in result

    def test_limit_zero_clamped_to_one(self):
        """limit=0은 내부에서 1로 보정되어 정상 호출."""
        env = self._setup_env()
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._slack_client", None), \
             patch("slack_to_notion.slack_client.WebClient") as mock_cls:
            mock_cls.return_value.conversations_history.return_value = {"messages": []}

            from slack_to_notion.mcp_server import fetch_messages
            result = fetch_messages("C001", limit=0)
            # limit=0 → max(1,0)=1 로 보정, 에러 없이 JSON 반환
            assert "[에러]" not in result
            call_kwargs = mock_cls.return_value.conversations_history.call_args[1]
            assert call_kwargs["limit"] == 1

    def test_limit_negative_clamped_to_one(self):
        """limit 음수는 1로 보정."""
        env = self._setup_env()
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._slack_client", None), \
             patch("slack_to_notion.slack_client.WebClient") as mock_cls:
            mock_cls.return_value.conversations_history.return_value = {"messages": []}

            from slack_to_notion.mcp_server import fetch_messages
            fetch_messages("C001", limit=-5)
            call_kwargs = mock_cls.return_value.conversations_history.call_args[1]
            assert call_kwargs["limit"] == 1

    def test_limit_over_1000_clamped_to_1000(self):
        """limit 1001은 1000으로 보정."""
        env = self._setup_env()
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._slack_client", None), \
             patch("slack_to_notion.slack_client.WebClient") as mock_cls:
            mock_cls.return_value.conversations_history.return_value = {"messages": []}

            from slack_to_notion.mcp_server import fetch_messages
            fetch_messages("C001", limit=1001)
            call_kwargs = mock_cls.return_value.conversations_history.call_args[1]
            assert call_kwargs["limit"] == 1000


class TestFetchThreadErrors:
    """fetch_thread 에러 처리 테스트."""

    def test_invalid_thread_ts(self):
        """잘못된 thread_ts로 조회 시 에러 메시지 반환."""
        env = {"SLACK_BOT_TOKEN": "xoxb-fake"}
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._slack_client", None), \
             patch("slack_to_notion.slack_client.WebClient") as mock_cls:
            from slack_sdk.errors import SlackApiError
            error_response = MagicMock()
            error_response.get.side_effect = lambda key, default="": "thread_not_found" if key == "error" else default
            mock_cls.return_value.conversations_replies.side_effect = SlackApiError(
                message="err", response=error_response
            )

            from slack_to_notion.mcp_server import fetch_thread
            result = fetch_thread("C001", "invalid.ts")
            assert "[에러]" in result

    def test_unexpected_exception(self):
        """예상치 못한 예외 발생 시 에러 메시지 반환."""
        env = {"SLACK_BOT_TOKEN": "xoxb-fake"}
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._slack_client", None), \
             patch("slack_to_notion.slack_client.WebClient") as mock_cls:
            mock_cls.return_value.conversations_replies.side_effect = ConnectionError("연결 실패")

            from slack_to_notion.mcp_server import fetch_thread
            result = fetch_thread("C001", "1234567890.000000")
            assert "[에러]" in result


class TestFormatMessagesErrors:
    """format_messages 에러 처리 테스트."""

    def test_slack_client_error(self):
        """SlackClientError 발생 시 에러 메시지 반환."""
        env = {"SLACK_BOT_TOKEN": "xoxb-fake"}
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._slack_client", None), \
             patch("slack_to_notion.slack_client.WebClient") as mock_cls:
            from slack_sdk.errors import SlackApiError
            error_response = MagicMock()
            error_response.get.side_effect = lambda key, default="": "not_in_channel" if key == "error" else default
            mock_cls.return_value.conversations_history.side_effect = SlackApiError(
                message="err", response=error_response
            )

            from slack_to_notion.mcp_server import format_messages
            result = format_messages("C001", "general")
            assert "[에러]" in result

    def test_unexpected_exception(self):
        """예상치 못한 예외 발생 시 에러 메시지 반환."""
        env = {"SLACK_BOT_TOKEN": "xoxb-fake"}
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._slack_client", None), \
             patch("slack_to_notion.slack_client.WebClient") as mock_cls:
            mock_cls.return_value.conversations_history.side_effect = RuntimeError("오류")

            from slack_to_notion.mcp_server import format_messages
            result = format_messages("C001", "general")
            assert "[에러]" in result


class TestSaveAnalysisResultErrors:
    """save_analysis_result 에러 처리 테스트."""

    def test_invalid_json_input(self):
        """유효하지 않은 JSON 문자열 입력 시 에러 메시지 반환."""
        from slack_to_notion.mcp_server import save_analysis_result
        result = save_analysis_result("이것은 JSON이 아닙니다")
        assert "[에러]" in result
        assert "JSON" in result

    def test_empty_json_string(self):
        """빈 문자열 입력 시 에러 메시지 반환."""
        from slack_to_notion.mcp_server import save_analysis_result
        result = save_analysis_result("")
        assert "[에러]" in result

    def test_valid_json_succeeds(self, tmp_path):
        """유효한 JSON 입력 시 정상 저장."""
        with patch("slack_to_notion.mcp_server.save_result") as mock_save:
            import json
            from pathlib import Path
            mock_save.return_value = tmp_path / "analysis_test.json"

            from slack_to_notion.mcp_server import save_analysis_result
            result = save_analysis_result(json.dumps({"title": "테스트"}), "test.json")
            assert "[에러]" not in result
            assert "저장되었습니다" in result


class TestCreateNotionPageErrors:
    """create_notion_page NotionClientError 처리 테스트."""

    def test_notion_client_error_on_check_duplicate(self):
        """check_duplicate에서 NotionClientError 발생 시 에러 메시지 반환."""
        from slack_to_notion.notion_client import NotionClientError

        env = {
            "NOTION_API_KEY": "fake-key",
            "NOTION_PARENT_PAGE_URL": "abc123def456abc123def456abc123de",
        }
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._notion_client", None), \
             patch("slack_to_notion.notion_client.Client") as mock_cls:
            mock_cls.return_value.blocks.children.list.side_effect = \
                NotionClientError("API 키가 올바르지 않습니다")

            from slack_to_notion.mcp_server import create_notion_page
            result = create_notion_page("제목", "내용")
            assert "[에러]" in result

    def test_notion_client_error_on_page_create(self):
        """pages.create에서 NotionClientError 발생 시 에러 메시지 반환."""
        from slack_to_notion.notion_client import NotionClientError

        env = {
            "NOTION_API_KEY": "fake-key",
            "NOTION_PARENT_PAGE_URL": "abc123def456abc123def456abc123de",
        }
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._notion_client", None), \
             patch("slack_to_notion.notion_client.Client") as mock_cls:
            mock_api = mock_cls.return_value
            mock_api.blocks.children.list.return_value = {"results": []}
            mock_api.pages.create.side_effect = NotionClientError("페이지를 찾을 수 없습니다")

            from slack_to_notion.mcp_server import create_notion_page
            result = create_notion_page("새 제목", "내용")
            assert "[에러]" in result

    def test_unexpected_exception(self):
        """예상치 못한 예외 발생 시 에러 메시지 반환."""
        env = {
            "NOTION_API_KEY": "fake-key",
            "NOTION_PARENT_PAGE_URL": "abc123def456abc123def456abc123de",
        }
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._notion_client", None), \
             patch("slack_to_notion.notion_client.Client") as mock_cls:
            mock_cls.return_value.blocks.children.list.side_effect = RuntimeError("연결 실패")

            from slack_to_notion.mcp_server import create_notion_page
            result = create_notion_page("제목", "내용")
            assert "[에러]" in result


class TestMainHelp:
    """main 함수 --help 플래그 테스트."""

    def test_help_flag_returns_without_systemexit(self):
        """--help 플래그 시 SystemExit 없이 정상 반환."""
        with patch.object(sys, "argv", ["slack-to-notion-mcp", "--help"]):
            from slack_to_notion.mcp_server import main
            # SystemExit 없이 정상 종료되어야 함
            main()  # 예외 없으면 통과

    def test_short_help_flag_returns_without_systemexit(self):
        """-h 플래그 시 SystemExit 없이 정상 반환."""
        with patch.object(sys, "argv", ["slack-to-notion-mcp", "-h"]):
            from slack_to_notion.mcp_server import main
            main()  # 예외 없으면 통과


class TestFetchMessagesFieldFiltering:
    """fetch_messages 반환 필드 검증."""

    def test_only_allowed_fields_returned(self):
        """불필요 필드(blocks, reactions 등)가 제거되는지 확인."""
        import json
        env = {"SLACK_BOT_TOKEN": "xoxb-fake"}
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._slack_client", None), \
             patch("slack_to_notion.slack_client.WebClient") as mock_cls:
            mock_api = mock_cls.return_value
            mock_api.conversations_history.return_value = {
                "messages": [{
                    "ts": "1234567890.123456",
                    "user": "U001",
                    "text": "hello",
                    "blocks": [{"type": "rich_text"}],
                    "reactions": [{"name": "thumbsup"}],
                    "reply_count": 3,
                    "thread_ts": "1234567890.123456",
                }]
            }
            mock_api.users_info.return_value = {
                "user": {"profile": {"display_name": "kim", "real_name": ""}}
            }

            from slack_to_notion.mcp_server import fetch_messages
            result = json.loads(fetch_messages("C001", limit=1))

            msg = result[0]
            allowed = {"ts", "user", "user_name", "text", "reply_count", "thread_ts"}
            assert set(msg.keys()).issubset(allowed)
            assert "blocks" not in msg
            assert "reactions" not in msg
