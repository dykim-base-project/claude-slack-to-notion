# 문제 해결

## 자주 발생하는 문제

| 증상 | 원인 | 해결 방법 |
|------|------|-----------|
| 설치 후 첫 실행에서 플러그인이 인식되지 않음 | Claude Code CLI 캐시 이슈 | `/exit`으로 종료 후 `claude`를 다시 실행 |
| `spawn uvx ENOENT` (Claude Desktop) | Claude Desktop이 uvx 경로를 찾지 못함 | 아래 [Claude Desktop에서 uvx를 찾지 못하는 경우](#claude-desktop에서-uvx를-찾지-못하는-경우) 참고 |
| `uvx: command not found` (터미널) | uv 미설치 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` 실행 후 터미널 재시작 |
| `No module named slack_to_notion` | 패키지 설치 안 됨 | `uv cache clean slack-to-notion-mcp && uvx slack-to-notion-mcp@latest --help` |
| `SLACK_BOT_TOKEN 또는 SLACK_USER_TOKEN 환경변수가 설정되지 않았습니다` | 환경변수 미설정 | [설치 가이드](setup-guide.md#4단계-환경변수-설정) 참고 |
| `not_in_channel` 에러 (Bot 토큰) | Bot이 채널에 초대되지 않음 | 채널 설정 → Integrations → Add apps에서 Bot 추가 |
| `not_in_channel` 에러 (사용자 토큰) | 해당 채널에 참여하지 않음 | Slack에서 채널에 참여한 뒤 다시 시도 |
| `invalid_auth` 에러 | 토큰이 잘못되었거나 만료됨 | [Slack API](https://api.slack.com/apps)에서 토큰 재확인 |
| `Notion API 키가 올바르지 않습니다` | Notion API Key가 잘못됨 | [Notion Integrations](https://www.notion.so/my-integrations)에서 Secret 재확인 |
| `Notion 페이지를 찾을 수 없습니다` | Integration이 페이지에 연결되지 않음 | [설치 가이드](setup-guide.md#2단계-notion-api-key-발급)의 "Integration을 Notion 페이지에 연결하기" 참고 |

## Claude Desktop에서 uvx를 찾지 못하는 경우

Claude Desktop은 일반 앱이라 터미널의 PATH 설정(`~/.zshrc` 등)을 읽지 못합니다.
터미널에서 `uvx`가 정상 동작해도 Claude Desktop에서는 `spawn uvx ENOENT` 오류가 발생할 수 있습니다.

**해결 방법: uvx 절대 경로 사용**

1. 터미널을 열고 아래 명령어를 실행합니다:
   ```
   which uvx
   ```
2. 출력된 경로(예: `/Users/사용자이름/.local/bin/uvx`)를 복사합니다
3. `claude_desktop_config.json`에서 `"command"` 값을 절대 경로로 변경합니다:
   ```json
   "command": "/Users/사용자이름/.local/bin/uvx"
   ```
4. Claude Desktop을 재시작합니다

> `which uvx`에서 아무것도 나오지 않으면 uv가 설치되지 않은 것입니다.
> `curl -LsSf https://astral.sh/uv/install.sh | sh` 로 설치한 뒤 터미널을 재시작하세요.

## 제약사항

- **API 토큰 관리**: Slack API 토큰, Notion API 키는 환경변수로 관리 (Git 추적 금지)
- **개인 메시지(DM) 제외**: 보안상 개인 DM 수집 지원하지 않음
- **API Rate Limit**: Slack/Notion API Rate Limit 고려 필요 (과도한 요청 시 제한 발생 가능)
- **채널 접근**: Bot 토큰 사용 시 채널에 앱 초대 필요, 사용자 토큰 사용 시 본인이 참여한 채널만 접근 가능
