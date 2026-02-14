"""Notion 페이지 생성 모듈.

notion-client를 사용하여 분석 결과를 Notion 페이지로 생성한다.
"""

from datetime import date

from notion_client import Client
from notion_client.errors import APIResponseError


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

    def get_or_create_database(self, parent_page_id: str) -> str:
        """parent_page_id 하위에서 'Slack 분석' DB를 찾거나 생성."""
        try:
            # 하위 블록 검색
            blocks = self.client.blocks.children.list(block_id=parent_page_id)
            for block in blocks.get("results", []):
                if block["type"] == "child_database":
                    title_list = block.get("child_database", {}).get("title", [])
                    if title_list and title_list[0].get("plain_text") == "Slack 분석":
                        return block["id"]

            # DB 생성
            response = self.client.databases.create(
                parent={"type": "page_id", "page_id": parent_page_id},
                title=[{"type": "text", "text": {"content": "Slack 분석"}}],
                properties={
                    "제목": {"title": {}},
                    "채널명": {"rich_text": {}},
                    "분석기간": {"rich_text": {}},
                    "생성일": {"date": {}},
                },
            )
            return response["id"]
        except APIResponseError as e:
            raise NotionClientError(self._format_error_message(e)) from e

    def check_duplicate(self, database_id: str, channel_name: str, period: str) -> bool:
        """DB에서 동일 채널명/분석기간 페이지가 있는지 확인."""
        try:
            response = self.client.databases.query(
                database_id=database_id,
                filter={
                    "and": [
                        {"property": "채널명", "rich_text": {"equals": channel_name}},
                        {"property": "분석기간", "rich_text": {"equals": period}},
                    ]
                },
            )
            return len(response.get("results", [])) > 0
        except APIResponseError as e:
            raise NotionClientError(self._format_error_message(e)) from e

    def create_analysis_page(
        self,
        database_id: str,
        title: str,
        channel_name: str,
        period: str,
        blocks: list[dict],
    ) -> str:
        """DB에 분석 페이지 생성."""
        try:
            response = self.client.pages.create(
                parent={"database_id": database_id},
                properties={
                    "제목": {"title": [{"type": "text", "text": {"content": title}}]},
                    "채널명": {
                        "rich_text": [
                            {"type": "text", "text": {"content": channel_name}}
                        ]
                    },
                    "분석기간": {
                        "rich_text": [{"type": "text", "text": {"content": period}}]
                    },
                    "생성일": {"date": {"start": date.today().isoformat()}},
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
