"""Notion 페이지 생성 모듈.

notion-client를 사용하여 분석 결과를 Notion 페이지로 생성한다.
"""

import re
from urllib.parse import urlparse

from notion_client import Client
from notion_client.errors import APIResponseError


def extract_page_id(value: str) -> str:
    """Notion 페이지 URL 또는 ID에서 Page ID를 추출한다.

    지원 형식:
        - 전체 URL: https://www.notion.so/30829a38f6df80769e03d841eaad4f15?source=copy_link
        - 제목 포함 URL: https://www.notion.so/workspace/페이지제목-abc123def456...
        - 32자 ID: 30829a38f6df80769e03d841eaad4f15
        - UUID 형식: 30829a38-f6df-8076-9e03-d841eaad4f15
    """
    value = value.strip()

    # URL인 경우 경로에서 추출
    if value.startswith("http"):
        parsed = urlparse(value)
        path = parsed.path.strip("/")
        # 마지막 경로 세그먼트 사용
        segment = path.split("/")[-1] if "/" in path else path
    else:
        segment = value

    # 하이픈 제거 (UUID 형식 대응)
    cleaned = segment.replace("-", "")

    # 32자 hex 문자열 추출 (끝에서 32자)
    match = re.search(r"([0-9a-f]{32})$", cleaned)
    if match:
        return match.group(1)

    return value


class NotionClientError(Exception):
    """Notion API 호출 중 발생한 에러."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


def _parse_inline_markdown(text: str) -> list[dict]:
    """인라인 마크다운을 Notion rich_text 세그먼트 리스트로 변환.

    지원 문법 (단일 레벨, 중첩 미지원):
        - [텍스트](url) → 링크
        - **텍스트** → 볼드
        - *텍스트* → 이탤릭 (단독, 볼드가 아닌 경우)
        - `텍스트` → 인라인 코드
        - ~~텍스트~~ → 취소선
    """
    # 볼드(**) 먼저 매칭하여 이탤릭(*)과 구분
    pattern = re.compile(
        r"(\[([^\]]+)\]\(([^)]+)\))"  # 링크: [text](url)
        r"|(\*\*(.+?)\*\*)"           # 볼드: **text**
        r"|(\*(.+?)\*)"               # 이탤릭: *text*
        r"|(~~(.+?)~~)"               # 취소선: ~~text~~
        r"|(`([^`]+?)`)"              # 인라인 코드: `text`
    )

    segments: list[dict] = []
    last_end = 0

    for m in pattern.finditer(text):
        start = m.start()
        # 매치 전 평문 추가
        if start > last_end:
            plain = text[last_end:start]
            segments.append({"type": "text", "text": {"content": plain}})

        if m.group(2) is not None:
            # 링크
            link_text = m.group(2)
            link_url = m.group(3)
            segments.append({
                "type": "text",
                "text": {"content": link_text, "link": {"url": link_url}},
            })
        elif m.group(5) is not None:
            # 볼드
            segments.append({
                "type": "text",
                "text": {"content": m.group(5)},
                "annotations": {"bold": True},
            })
        elif m.group(7) is not None:
            # 이탤릭
            segments.append({
                "type": "text",
                "text": {"content": m.group(7)},
                "annotations": {"italic": True},
            })
        elif m.group(9) is not None:
            # 취소선
            segments.append({
                "type": "text",
                "text": {"content": m.group(9)},
                "annotations": {"strikethrough": True},
            })
        elif m.group(11) is not None:
            # 인라인 코드
            segments.append({
                "type": "text",
                "text": {"content": m.group(11)},
                "annotations": {"code": True},
            })

        last_end = m.end()

    # 나머지 평문 추가
    if last_end < len(text):
        segments.append({"type": "text", "text": {"content": text[last_end:]}})

    return segments if segments else [{"type": "text", "text": {"content": text}}]


def split_rich_text(text: str, max_len: int = 2000) -> list[dict]:
    """텍스트를 Notion rich_text 세그먼트 리스트로 분할.

    인라인 마크다운(링크, 볼드, 이탤릭, 코드, 취소선)을 파싱하여
    각 세그먼트에 적절한 annotations/link를 설정한다.
    각 세그먼트의 content는 max_len(기본 2000자)을 초과하지 않도록 분할한다.
    """
    if not text:
        return [{"type": "text", "text": {"content": " "}}]

    parsed = _parse_inline_markdown(text)

    # 각 세그먼트의 content가 max_len을 초과하면 분할
    result: list[dict] = []
    for seg in parsed:
        content = seg["text"]["content"]
        if len(content) <= max_len:
            result.append(seg)
        else:
            # 긴 세그먼트를 max_len 단위로 분할 (annotations/link 유지)
            for i in range(0, len(content), max_len):
                chunk = content[i : i + max_len]
                new_seg: dict = {"type": "text", "text": {"content": chunk}}
                if "link" in seg["text"]:
                    new_seg["text"]["link"] = seg["text"]["link"]
                if "annotations" in seg:
                    new_seg["annotations"] = seg["annotations"]
                result.append(new_seg)

    return result


class NotionClient:
    """Notion API 클라이언트."""

    def __init__(self, api_key: str):
        self.client = Client(auth=api_key)

    def _format_error_message(self, error: APIResponseError) -> str:
        """APIResponseError를 사용자 친화적 한글 메시지로 변환."""
        code = error.code
        if code in ("unauthorized", "invalid_api_key"):
            return "Notion API 키가 올바르지 않습니다. NOTION_API_KEY 값을 확인하세요. 토큰은 ntn_ 또는 secret_로 시작해야 합니다."
        elif code == "object_not_found":
            return "Notion 페이지를 찾을 수 없습니다. Integration이 해당 페이지에 연결되어 있는지 확인하세요."
        elif code == "restricted_resource":
            return "해당 Notion 페이지에 접근 권한이 없습니다. Integration 연결을 확인하세요."
        elif code == "validation_error":
            return "Notion 요청이 올바르지 않습니다. NOTION_PARENT_PAGE_URL이 유효한 페이지 링크인지 확인하세요."
        else:
            return f"예상치 못한 오류가 발생했습니다 ({code}). 문제가 지속되면 README.md를 참고하세요."

    def check_duplicate(self, parent_page_id: str, title: str) -> bool:
        """상위 페이지 하위에서 동일 제목의 페이지가 있는지 확인.

        하위 페이지가 100개 초과인 경우에도 pagination으로 전체 조회한다.
        """
        try:
            cursor = None
            while True:
                kwargs: dict = {"block_id": parent_page_id}
                if cursor:
                    kwargs["start_cursor"] = cursor
                response = self.client.blocks.children.list(**kwargs)
                for block in response.get("results", []):
                    if block["type"] == "child_page":
                        page_title = block.get("child_page", {}).get("title", "")
                        if page_title == title:
                            return True
                if not response.get("has_more"):
                    break
                cursor = response.get("next_cursor")
            return False
        except APIResponseError as e:
            raise NotionClientError(self._format_error_message(e)) from e

    def create_analysis_page(
        self,
        parent_page_id: str,
        title: str,
        blocks: list[dict],
    ) -> str:
        """상위 페이지 하위에 분석 결과 페이지를 생성.

        Notion API는 children 배열 최대 100개 제한이 있으므로,
        100개 초과 시 처음 100개로 페이지를 생성한 뒤 나머지를 100개씩 분할하여 append한다.
        """
        _BLOCK_LIMIT = 100
        try:
            first_batch = blocks[:_BLOCK_LIMIT]
            response = self.client.pages.create(
                parent={"page_id": parent_page_id},
                properties={
                    "title": {
                        "title": [{"type": "text", "text": {"content": title}}]
                    },
                },
                children=first_batch,
            )
            page_id = response["id"]
            # 100개 초과분을 100개씩 분할하여 append
            remaining = blocks[_BLOCK_LIMIT:]
            for i in range(0, len(remaining), _BLOCK_LIMIT):
                batch = remaining[i : i + _BLOCK_LIMIT]
                self.client.blocks.children.append(
                    block_id=page_id,
                    children=batch,
                )
            return response["url"]
        except APIResponseError as e:
            raise NotionClientError(self._format_error_message(e)) from e

    def build_page_blocks(self, content_text: str) -> list[dict]:
        """자유 형식 텍스트를 Notion 블록으로 변환."""
        blocks = []
        lines = content_text.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 코드블록: ``` 으로 시작
            if stripped.startswith("```"):
                language = stripped[3:].strip() or "plain text"
                code_lines = []
                i += 1
                while i < len(lines):
                    code_line = lines[i]
                    if code_line.strip().startswith("```"):
                        i += 1
                        break
                    code_lines.append(code_line)
                    i += 1
                code_content = "\n".join(code_lines)
                blocks.append(
                    {
                        "object": "block",
                        "type": "code",
                        "code": {
                            "rich_text": split_rich_text(code_content),
                            "language": language,
                        },
                    }
                )
                continue

            # 마크다운 테이블: | 로 시작하는 연속 라인
            if stripped.startswith("|"):
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i].strip())
                    i += 1

                # 구분선 행 제거 (|---|---| 패턴)
                data_lines = [
                    l for l in table_lines
                    if not re.match(r"^\|[\s\-:|]+\|", l)
                ]

                if data_lines:
                    rows = []
                    table_width = 0
                    for row_line in data_lines:
                        # 양 끝 | 제거 후 셀 파싱
                        inner = row_line.strip("|")
                        cells = [cell.strip() for cell in inner.split("|")]
                        table_width = max(table_width, len(cells))
                        rows.append(cells)

                    # 모든 행의 셀 수를 table_width에 맞게 패딩
                    children = []
                    for cells in rows:
                        padded = cells + [""] * (table_width - len(cells))
                        children.append(
                            {
                                "type": "table_row",
                                "table_row": {
                                    "cells": [
                                        [{"type": "text", "text": {"content": cell}}]
                                        for cell in padded
                                    ]
                                },
                            }
                        )

                    blocks.append(
                        {
                            "object": "block",
                            "type": "table",
                            "table": {
                                "table_width": table_width,
                                "has_column_header": True,
                                "has_row_header": False,
                                "children": children,
                            },
                        }
                    )
                continue

            if not stripped:
                i += 1
                continue

            if stripped.startswith("# "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {"rich_text": split_rich_text(stripped[2:])},
                    }
                )
            elif stripped.startswith("## "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {"rich_text": split_rich_text(stripped[3:])},
                    }
                )
            elif stripped.startswith("### "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {"rich_text": split_rich_text(stripped[4:])},
                    }
                )
            elif stripped == "---":
                blocks.append({"object": "block", "type": "divider", "divider": {}})
            elif stripped.startswith("- ") or stripped.startswith("* "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": split_rich_text(stripped[2:])
                        },
                    }
                )
            elif re.match(r"^\d+\. ", stripped):
                # 번호 목록: "1. ", "2. " 등
                content = re.sub(r"^\d+\. ", "", stripped)
                blocks.append(
                    {
                        "object": "block",
                        "type": "numbered_list_item",
                        "numbered_list_item": {
                            "rich_text": split_rich_text(content)
                        },
                    }
                )
            else:
                blocks.append(
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": split_rich_text(stripped)},
                    }
                )

            i += 1

        return blocks
