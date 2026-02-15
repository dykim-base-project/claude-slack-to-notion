"""MCP 서버 도구 단위 테스트."""

from unittest.mock import MagicMock, patch

import pytest


class TestCreateNotionPage:
    """create_notion_page 도구 테스트."""

    def _call_tool(self, title, content, env_vars=None):
        """create_notion_page를 환경변수와 mock으로 호출."""
        env = {
            "NOTION_API_KEY": "fake-key",
            "NOTION_PARENT_PAGE_ID": "https://www.notion.so/abc123def456abc123def456abc123de?source=copy_link",
        }
        if env_vars:
            env.update(env_vars)

        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._notion_client", None), \
             patch("slack_to_notion.notion_client.Client") as mock_cls:
            mock_api = mock_cls.return_value
            mock_api.blocks.children.list.return_value = {"results": []}
            mock_api.pages.create.return_value = {"url": "https://notion.so/created-page"}

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
            "NOTION_PARENT_PAGE_ID": "abc123def456abc123def456abc123de",
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
            assert "NOTION_PARENT_PAGE_ID" in result
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


class TestCreateNotionPageBlockConversion:
    """페이지 생성 시 블록 변환이 올바르게 전달되는지 테스트."""

    def test_blocks_passed_to_api(self):
        env = {
            "NOTION_API_KEY": "fake-key",
            "NOTION_PARENT_PAGE_ID": "abc123def456abc123def456abc123de",
        }
        with patch.dict("os.environ", env, clear=False), \
             patch("slack_to_notion.mcp_server._notion_client", None), \
             patch("slack_to_notion.notion_client.Client") as mock_cls:
            mock_api = mock_cls.return_value
            mock_api.blocks.children.list.return_value = {"results": []}
            mock_api.pages.create.return_value = {"url": "https://notion.so/page"}

            from slack_to_notion.mcp_server import create_notion_page
            create_notion_page("제목", "# 헤딩\n- 항목")

            call_kwargs = mock_api.pages.create.call_args[1]
            children = call_kwargs["children"]
            assert len(children) == 2
            assert children[0]["type"] == "heading_1"
            assert children[1]["type"] == "bulleted_list_item"
