# 문제 해결

## 자주 발생하는 문제

| 증상 | 원인 | 해결 방법 |
|------|------|-----------|
| 설치 후 첫 실행에서 플러그인이 인식되지 않음 | Claude Code CLI 캐시 이슈 | `/exit`으로 종료 후 `claude`를 다시 실행 |
| `uvx: command not found` | uv 미설치 | `brew install uv` 또는 [uv 설치 가이드](https://docs.astral.sh/uv/getting-started/installation/) 참고 |
| `No module named slack_to_notion` | 패키지 설치 안 됨 | `uv cache clean slack-to-notion-mcp && uvx slack-to-notion-mcp@latest --help` |
| `SLACK_BOT_TOKEN 또는 SLACK_USER_TOKEN 환경변수가 설정되지 않았습니다` | 환경변수 미설정 | [설치 가이드](setup-guide.md#4단계-환경변수-설정) 참고 |
| `not_in_channel` 에러 (Bot 토큰) | Bot이 채널에 초대되지 않음 | 채널 설정 → Integrations → Add apps에서 Bot 추가 |
| `not_in_channel` 에러 (사용자 토큰) | 해당 채널에 참여하지 않음 | Slack에서 채널에 참여한 뒤 다시 시도 |
| `invalid_auth` 에러 | 토큰이 잘못되었거나 만료됨 | [Slack API](https://api.slack.com/apps)에서 토큰 재확인 |
| `Notion API 키가 올바르지 않습니다` | Notion API Key가 잘못됨 | [Notion Integrations](https://www.notion.so/my-integrations)에서 Secret 재확인 |
| `Notion 페이지를 찾을 수 없습니다` | Integration이 페이지에 연결되지 않음 | [설치 가이드](setup-guide.md#2단계-notion-api-key-발급)의 "Integration을 Notion 페이지에 연결하기" 참고 |

## 제약사항

- **API 토큰 관리**: Slack API 토큰, Notion API 키는 환경변수로 관리 (Git 추적 금지)
- **개인 메시지(DM) 제외**: 보안상 개인 DM 수집 지원하지 않음
- **API Rate Limit**: Slack/Notion API Rate Limit 고려 필요 (과도한 요청 시 제한 발생 가능)
- **채널 접근**: Bot 토큰 사용 시 채널에 앱 초대 필요, 사용자 토큰 사용 시 본인이 참여한 채널만 접근 가능
