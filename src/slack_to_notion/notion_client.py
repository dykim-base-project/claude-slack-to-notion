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


def split_rich_text(text: str, max_len: int = 2000) -> list[dict]:
    """텍스트를 Notion rich_text 세그먼트 리스트로 분할."""
    if not text:
        return [{"type": "text", "text": {"content": " "}}]

    chunks = []
    for i in range(0, len(text), max_len):
        chunk = text[i : i + max_len]
        chunks.append({"type": "text", "text": {"content": chunk}})
    return chunks


class NotionClient:
    """Notion API 클라이언트."""

    def __init__(self, api_key: str):
        self.client = Client(auth=api_key)

    def _format_error_message(self, error: APIResponseError) -> str:
        """APIResponseError를 사용자 친화적 한글 메시지로 변환."""
        code = error.code
        if code in ("unauthorized", "invalid_api_key"):
            return "Notion API 키가 올바르지 않습니다. .env 파일의 NOTION_API_KEY를 확인하세요."
        elif code == "object_not_found":
            return "Notion 페이지를 찾을 수 없습니다. Integration이 해당 페이지에 연결되어 있는지 확인하세요."
        elif code == "restricted_resource":
            return "해당 Notion 페이지에 접근 권한이 없습니다. Integration 연결을 확인하세요."
        else:
            return f"Notion API 오류가 발생했습니다: {code}. 자세한 내용은 README.md를 참고하세요."

    def check_duplicate(self, parent_page_id: str, title: str) -> bool:
        """상위 페이지 하위에서 동일 제목의 페이지가 있는지 확인."""
        try:
            blocks = self.client.blocks.children.list(block_id=parent_page_id)
            for block in blocks.get("results", []):
                if block["type"] == "child_page":
                    page_title = block.get("child_page", {}).get("title", "")
                    if page_title == title:
                        return True
            return False
        except APIResponseError as e:
            raise NotionClientError(self._format_error_message(e)) from e

    def create_analysis_page(
        self,
        parent_page_id: str,
        title: str,
        blocks: list[dict],
    ) -> str:
        """상위 페이지 하위에 분석 결과 페이지를 생성."""
        try:
            response = self.client.pages.create(
                parent={"page_id": parent_page_id},
                properties={
                    "title": {
                        "title": [{"type": "text", "text": {"content": title}}]
                    },
                },
                children=blocks,
            )
            return response["url"]
        except APIResponseError as e:
            raise NotionClientError(self._format_error_message(e)) from e

    def build_page_blocks(self, content_text: str) -> list[dict]:
        """자유 형식 텍스트를 Notion 블록으로 변환."""
        blocks = []
        lines = content_text.split("\n")

        for line in lines:
            stripped = line.strip()
            if not stripped:
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
            else:
                blocks.append(
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": split_rich_text(stripped)},
                    }
                )

        return blocks
