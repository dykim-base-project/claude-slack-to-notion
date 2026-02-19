# 제공 도구

claude-slack-to-notion이 Claude Code에 제공하는 MCP 도구 목록입니다.
별도로 호출할 필요 없이, 자연어로 요청하면 Claude Code가 적절한 도구를 자동 선택합니다.

## Slack 수집

| 도구 | 설명 |
|------|------|
| `list_channels` | Slack 채널 목록 조회 |
| `fetch_messages` | 특정 채널의 메시지 조회 |
| `fetch_thread` | 특정 스레드의 전체 메시지 조회 |
| `fetch_threads` | 여러 스레드를 한 번에 수집하고 AI 분석용으로 포맷팅 |
| `fetch_channel_info` | 채널 상세 정보 조회 |

## 분석

| 도구 | 설명 |
|------|------|
| `get_analysis_guide_tool` | 분석 방향 안내 (예시 포함) |
| `format_messages` | 수집된 메시지를 AI 분석용 텍스트로 포맷팅 |

## Notion

| 도구 | 설명 |
|------|------|
| `create_notion_page` | 분석 결과를 Notion 페이지로 생성 |
| `save_analysis_result` | 분석 결과를 로컬 JSON 파일로 백업 |

## 커스터마이징

| 도구 | 설명 |
|------|------|
| `save_preference_tool` | 사용자의 분석 선호도 저장 ("기억해줘", "앞으로 ~해줘") |
| `get_preferences` | 저장된 분석 선호도 조회 (분석 전 자동 참조) |
| `list_analysis_history` | 과거 분석 결과 히스토리 조회 ("지난번처럼 해줘") |
