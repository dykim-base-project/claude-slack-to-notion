"""Notion 클라이언트 단위 테스트."""

from unittest.mock import MagicMock, patch

import pytest

from slack_to_notion.notion_client import (
    NotionClient,
    NotionClientError,
    extract_page_id,
    split_rich_text,
)


# ──────────────────────────────────────────────
# extract_page_id
# ──────────────────────────────────────────────


class TestExtractPageId:
    """URL/ID에서 Page ID 추출 테스트."""

    def test_full_url_with_query(self):
        url = "https://www.notion.so/30829a38f6df80769e03d841eaad4f15?source=copy_link"
        assert extract_page_id(url) == "30829a38f6df80769e03d841eaad4f15"

    def test_full_url_without_query(self):
        url = "https://www.notion.so/30829a38f6df80769e03d841eaad4f15"
        assert extract_page_id(url) == "30829a38f6df80769e03d841eaad4f15"

    def test_url_with_workspace_and_title(self):
        url = "https://www.notion.so/workspace/My-Page-30829a38f6df80769e03d841eaad4f15"
        assert extract_page_id(url) == "30829a38f6df80769e03d841eaad4f15"

    def test_raw_32char_id(self):
        assert extract_page_id("30829a38f6df80769e03d841eaad4f15") == "30829a38f6df80769e03d841eaad4f15"

    def test_uuid_format(self):
        assert extract_page_id("30829a38-f6df-8076-9e03-d841eaad4f15") == "30829a38f6df80769e03d841eaad4f15"

    def test_whitespace_stripped(self):
        assert extract_page_id("  30829a38f6df80769e03d841eaad4f15  ") == "30829a38f6df80769e03d841eaad4f15"

    def test_invalid_returns_original(self):
        assert extract_page_id("not-a-valid-id") == "not-a-valid-id"


# ──────────────────────────────────────────────
# split_rich_text
# ──────────────────────────────────────────────


class TestSplitRichText:
    """Notion rich_text 분할 테스트."""

    def test_empty_text(self):
        result = split_rich_text("")
        assert len(result) == 1
        assert result[0]["text"]["content"] == " "

    def test_short_text(self):
        result = split_rich_text("hello")
        assert len(result) == 1
        assert result[0]["text"]["content"] == "hello"

    def test_long_text_splits(self):
        text = "a" * 5000
        result = split_rich_text(text, max_len=2000)
        assert len(result) == 3
        assert len(result[0]["text"]["content"]) == 2000
        assert len(result[1]["text"]["content"]) == 2000
        assert len(result[2]["text"]["content"]) == 1000


# ──────────────────────────────────────────────
# NotionClient
# ──────────────────────────────────────────────


class TestNotionClient:
    """NotionClient 단위 테스트."""

    def setup_method(self):
        with patch("slack_to_notion.notion_client.Client"):
            self.client = NotionClient("fake-api-key")
            self.mock_api = self.client.client

    def test_check_duplicate_found(self):
        self.mock_api.blocks.children.list.return_value = {
            "results": [
                {
                    "type": "child_page",
                    "child_page": {"title": "[마케팅] 분석 결과 - 2026-02-15"},
                },
            ]
        }
        assert self.client.check_duplicate("page-id", "[마케팅] 분석 결과 - 2026-02-15") is True

    def test_check_duplicate_not_found(self):
        self.mock_api.blocks.children.list.return_value = {
            "results": [
                {
                    "type": "child_page",
                    "child_page": {"title": "다른 페이지"},
                },
            ]
        }
        assert self.client.check_duplicate("page-id", "[마케팅] 분석 결과") is False

    def test_check_duplicate_empty(self):
        self.mock_api.blocks.children.list.return_value = {"results": []}
        assert self.client.check_duplicate("page-id", "제목") is False

    def test_check_duplicate_ignores_non_page_blocks(self):
        self.mock_api.blocks.children.list.return_value = {
            "results": [
                {"type": "paragraph"},
                {"type": "child_database", "child_database": {"title": "DB"}},
            ]
        }
        assert self.client.check_duplicate("page-id", "제목") is False

    def test_create_analysis_page_success(self):
        self.mock_api.pages.create.return_value = {
            "url": "https://www.notion.so/test-page-id"
        }
        url = self.client.create_analysis_page("parent-id", "테스트 제목", [])
        assert url == "https://www.notion.so/test-page-id"

        call_kwargs = self.mock_api.pages.create.call_args[1]
        assert call_kwargs["parent"] == {"page_id": "parent-id"}
        assert call_kwargs["properties"]["title"]["title"][0]["text"]["content"] == "테스트 제목"

    def test_create_analysis_page_with_blocks(self):
        self.mock_api.pages.create.return_value = {"url": "https://notion.so/page"}
        blocks = [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}]
        self.client.create_analysis_page("parent-id", "제목", blocks)

        call_kwargs = self.mock_api.pages.create.call_args[1]
        assert call_kwargs["children"] == blocks

    def test_build_page_blocks_heading1(self):
        blocks = self.client.build_page_blocks("# 제목")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_1"

    def test_build_page_blocks_heading2(self):
        blocks = self.client.build_page_blocks("## 소제목")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_2"

    def test_build_page_blocks_heading3(self):
        blocks = self.client.build_page_blocks("### 하위제목")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_3"

    def test_build_page_blocks_bullet_dash(self):
        blocks = self.client.build_page_blocks("- 항목")
        assert blocks[0]["type"] == "bulleted_list_item"

    def test_build_page_blocks_bullet_asterisk(self):
        blocks = self.client.build_page_blocks("* 항목")
        assert blocks[0]["type"] == "bulleted_list_item"

    def test_build_page_blocks_divider(self):
        blocks = self.client.build_page_blocks("---")
        assert blocks[0]["type"] == "divider"

    def test_build_page_blocks_paragraph(self):
        blocks = self.client.build_page_blocks("일반 텍스트")
        assert blocks[0]["type"] == "paragraph"

    def test_build_page_blocks_skips_empty_lines(self):
        blocks = self.client.build_page_blocks("# 제목\n\n본문")
        assert len(blocks) == 2

    def test_build_page_blocks_mixed_content(self):
        content = """# 분석 결과

## 요약
내용 요약입니다.

- 항목 1
- 항목 2

### 세부사항
세부 내용입니다.

---
끝."""
        blocks = self.client.build_page_blocks(content)
        types = [b["type"] for b in blocks]
        assert types == [
            "heading_1",
            "heading_2",
            "paragraph",
            "bulleted_list_item",
            "bulleted_list_item",
            "heading_3",
            "paragraph",
            "divider",
            "paragraph",
        ]


class TestNotionClientErrorFormatting:
    """에러 메시지 변환 테스트."""

    def setup_method(self):
        with patch("slack_to_notion.notion_client.Client"):
            self.client = NotionClient("fake-api-key")

    def _make_error(self, code: str):
        error = MagicMock()
        error.code = code
        return error

    def test_unauthorized(self):
        msg = self.client._format_error_message(self._make_error("unauthorized"))
        assert "API 키가 올바르지 않습니다" in msg

    def test_object_not_found(self):
        msg = self.client._format_error_message(self._make_error("object_not_found"))
        assert "페이지를 찾을 수 없습니다" in msg

    def test_restricted_resource(self):
        msg = self.client._format_error_message(self._make_error("restricted_resource"))
        assert "접근 권한이 없습니다" in msg

    def test_unknown_error(self):
        msg = self.client._format_error_message(self._make_error("rate_limited"))
        assert "rate_limited" in msg
