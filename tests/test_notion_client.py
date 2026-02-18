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
            "id": "test-page-id",
            "url": "https://www.notion.so/test-page-id",
        }
        url = self.client.create_analysis_page("parent-id", "테스트 제목", [])
        assert url == "https://www.notion.so/test-page-id"

        call_kwargs = self.mock_api.pages.create.call_args[1]
        assert call_kwargs["parent"] == {"page_id": "parent-id"}
        assert call_kwargs["properties"]["title"]["title"][0]["text"]["content"] == "테스트 제목"

    def test_create_analysis_page_with_blocks(self):
        self.mock_api.pages.create.return_value = {
            "id": "page-id",
            "url": "https://notion.so/page",
        }
        blocks = [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}]
        self.client.create_analysis_page("parent-id", "제목", blocks)

        call_kwargs = self.mock_api.pages.create.call_args[1]
        assert call_kwargs["children"] == blocks

    def test_create_analysis_page_over_100_blocks(self):
        """블록이 100개 초과일 때 처음 100개로 생성 후 나머지를 append한다."""
        self.mock_api.pages.create.return_value = {
            "id": "new-page-id",
            "url": "https://notion.so/new-page",
        }
        blocks = [
            {"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}
            for _ in range(250)
        ]
        url = self.client.create_analysis_page("parent-id", "제목", blocks)
        assert url == "https://notion.so/new-page"

        # pages.create 는 처음 100개만
        create_kwargs = self.mock_api.pages.create.call_args[1]
        assert len(create_kwargs["children"]) == 100

        # blocks.children.append 는 2회: 100개 + 50개
        append_calls = self.mock_api.blocks.children.append.call_args_list
        assert len(append_calls) == 2
        assert append_calls[0][1]["block_id"] == "new-page-id"
        assert len(append_calls[0][1]["children"]) == 100
        assert len(append_calls[1][1]["children"]) == 50

    def test_create_analysis_page_exactly_100_blocks(self):
        """블록이 정확히 100개일 때 append를 호출하지 않는다."""
        self.mock_api.pages.create.return_value = {
            "id": "page-id",
            "url": "https://notion.so/page",
        }
        blocks = [
            {"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}
            for _ in range(100)
        ]
        self.client.create_analysis_page("parent-id", "제목", blocks)

        create_kwargs = self.mock_api.pages.create.call_args[1]
        assert len(create_kwargs["children"]) == 100
        self.mock_api.blocks.children.append.assert_not_called()

    def test_check_duplicate_pagination(self):
        """has_more=True 시 next_cursor를 사용해 다음 페이지를 조회한다."""
        # 첫 번째 응답: has_more=True, 찾는 페이지 없음
        first_response = {
            "results": [
                {"type": "child_page", "child_page": {"title": "다른 페이지"}},
            ],
            "has_more": True,
            "next_cursor": "cursor-abc",
        }
        # 두 번째 응답: has_more=False, 찾는 페이지 있음
        second_response = {
            "results": [
                {"type": "child_page", "child_page": {"title": "찾는 페이지"}},
            ],
            "has_more": False,
            "next_cursor": None,
        }
        self.mock_api.blocks.children.list.side_effect = [first_response, second_response]

        result = self.client.check_duplicate("page-id", "찾는 페이지")
        assert result is True

        calls = self.mock_api.blocks.children.list.call_args_list
        assert len(calls) == 2
        # 두 번째 호출에 start_cursor가 전달되어야 함
        assert calls[1][1]["start_cursor"] == "cursor-abc"

    def test_check_duplicate_pagination_not_found(self):
        """여러 페이지를 조회해도 없으면 False를 반환한다."""
        first_response = {
            "results": [{"type": "child_page", "child_page": {"title": "A"}}],
            "has_more": True,
            "next_cursor": "cursor-1",
        }
        second_response = {
            "results": [{"type": "child_page", "child_page": {"title": "B"}}],
            "has_more": False,
            "next_cursor": None,
        }
        self.mock_api.blocks.children.list.side_effect = [first_response, second_response]

        result = self.client.check_duplicate("page-id", "없는 페이지")
        assert result is False
        assert self.mock_api.blocks.children.list.call_count == 2

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

    def test_build_page_blocks_numbered_list(self):
        content = "1. 첫 번째\n2. 두 번째\n3. 세 번째"
        blocks = self.client.build_page_blocks(content)
        assert len(blocks) == 3
        for block in blocks:
            assert block["type"] == "numbered_list_item"
        assert blocks[0]["numbered_list_item"]["rich_text"][0]["text"]["content"] == "첫 번째"
        assert blocks[1]["numbered_list_item"]["rich_text"][0]["text"]["content"] == "두 번째"
        assert blocks[2]["numbered_list_item"]["rich_text"][0]["text"]["content"] == "세 번째"

    def test_build_page_blocks_code_block_no_language(self):
        content = "```\nprint('hello')\n```"
        blocks = self.client.build_page_blocks(content)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "plain text"
        assert blocks[0]["code"]["rich_text"][0]["text"]["content"] == "print('hello')"

    def test_build_page_blocks_code_block_with_language(self):
        content = "```python\ndef foo():\n    return 1\n```"
        blocks = self.client.build_page_blocks(content)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "python"
        assert "def foo():" in blocks[0]["code"]["rich_text"][0]["text"]["content"]

    def test_build_page_blocks_table_basic(self):
        content = "| 이름 | 나이 |\n|---|---|\n| 홍길동 | 30 |"
        blocks = self.client.build_page_blocks(content)
        assert len(blocks) == 1
        block = blocks[0]
        assert block["type"] == "table"
        assert block["table"]["table_width"] == 2
        assert block["table"]["has_column_header"] is True
        # 구분선 제외하면 2개 행
        assert len(block["table"]["children"]) == 2

    def test_build_page_blocks_table_header_row(self):
        content = "| 컬럼1 | 컬럼2 | 컬럼3 |\n|---|---|---|\n| A | B | C |"
        blocks = self.client.build_page_blocks(content)
        assert blocks[0]["table"]["table_width"] == 3
        header_row = blocks[0]["table"]["children"][0]
        assert header_row["table_row"]["cells"][0][0]["text"]["content"] == "컬럼1"
        assert header_row["table_row"]["cells"][1][0]["text"]["content"] == "컬럼2"
        assert header_row["table_row"]["cells"][2][0]["text"]["content"] == "컬럼3"

    def test_build_page_blocks_table_empty_cell(self):
        content = "| A |  | C |\n|---|---|---|\n| D | E | F |"
        blocks = self.client.build_page_blocks(content)
        header_row = blocks[0]["table"]["children"][0]
        # 빈 셀 허용
        assert header_row["table_row"]["cells"][1][0]["text"]["content"] == ""

    def test_build_page_blocks_table_no_separator(self):
        content = "| 이름 | 나이 |\n| 홍길동 | 30 |"
        blocks = self.client.build_page_blocks(content)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "table"
        assert len(blocks[0]["table"]["children"]) == 2

    # ── 에지 케이스 ──

    def test_build_page_blocks_empty_string(self):
        """빈 문자열 입력 시 빈 블록 리스트 반환."""
        blocks = self.client.build_page_blocks("")
        assert blocks == []

    def test_build_page_blocks_unclosed_code_block(self):
        """닫히지 않은 코드블록(``` 시작만 있고 끝 없음) — 코드 블록 하나 생성."""
        content = "```python\nprint('hello')\ndef foo():\n    return 1"
        blocks = self.client.build_page_blocks(content)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "python"
        assert "print('hello')" in blocks[0]["code"]["rich_text"][0]["text"]["content"]

    def test_build_page_blocks_table_unequal_column_counts(self):
        """테이블 행마다 컬럼 수가 다른 경우 — 최대 너비로 패딩."""
        # 헤더 3컬럼, 데이터 행 2컬럼
        content = "| A | B | C |\n|---|---|---|\n| D | E |"
        blocks = self.client.build_page_blocks(content)
        assert len(blocks) == 1
        block = blocks[0]
        assert block["type"] == "table"
        assert block["table"]["table_width"] == 3
        data_row = block["table"]["children"][1]
        # 짧은 행은 빈 셀로 패딩되어야 함
        assert len(data_row["table_row"]["cells"]) == 3
        assert data_row["table_row"]["cells"][2][0]["text"]["content"] == ""

    def test_build_page_blocks_only_whitespace_lines(self):
        """공백만 있는 라인은 모두 건너뜀 — 빈 블록 리스트 반환."""
        blocks = self.client.build_page_blocks("   \n\n  \n")
        assert blocks == []

    def test_build_page_blocks_unclosed_code_block_no_language(self):
        """언어 없이 닫히지 않은 코드블록 — 'plain text' 언어로 코드 블록 생성."""
        content = "```\nsome code\nmore code"
        blocks = self.client.build_page_blocks(content)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "plain text"
        assert "some code" in blocks[0]["code"]["rich_text"][0]["text"]["content"]


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
