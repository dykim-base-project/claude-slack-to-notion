# claude-slack-to-notion

Slack 메시지를 AI로 분석하여 Notion 페이지로 정리하는 Claude 플러그인

## 이게 뭔가요?

Slack 채널의 대화를 자동으로 수집하고, 원하는 방향으로 분석하여 Notion 페이지로 만들어줍니다.
회의록 정리, 이슈 추출, 주제별 분류 등 분석 방향은 자유롭게 지정할 수 있습니다.

```mermaid
graph LR
    A["Slack 채널"] -->|메시지 수집| B["Claude"]
    B -->|AI 분석| C["Notion 페이지"]
```

## 설치

사용하는 환경에 맞는 방법을 선택하세요.

### Claude Desktop 앱 (일반 사용자)

Claude Desktop 앱을 사용하고 있다면 아래 순서대로 진행하세요.

**1단계: uv 설치 (처음 한 번만)**

이 플러그인은 [uv](https://docs.astral.sh/uv/)라는 도구가 필요합니다. 이미 설치했다면 2단계로 넘어가세요.

1. **터미널**을 엽니다 (Spotlight에서 "터미널" 검색, 또는 `응용 프로그램 > 유틸리티 > 터미널`)
2. 아래 명령어를 복사해서 터미널에 붙여넣고 Enter를 누릅니다:
   ```
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. 설치가 끝나면 터미널을 **닫았다가 다시 엽니다**
4. 아래 명령어를 붙여넣고 Enter를 누릅니다. 출력된 경로를 **복사**해두세요:
   ```
   which uvx
   ```
   `/Users/사용자이름/.local/bin/uvx` 같은 경로가 나옵니다. 이 경로를 2단계에서 사용합니다.

> `which uvx`에서 아무것도 나오지 않으면 터미널을 닫고 다시 열어보세요.
> 그래도 안 되면 `$HOME/.local/bin/uvx` 경로를 직접 사용하세요.

**2단계: 설정 파일 열기**

1. Claude Desktop 앱 좌측 상단의 **계정 아이콘**을 클릭합니다
2. **설정**을 클릭합니다 (단축키: `⌘ + ,`)
3. 왼쪽 메뉴 하단 **데스크톱 앱** 섹션에서 **개발자**를 클릭합니다
4. **구성 편집**을 클릭하면 Finder에서 설정 파일(`claude_desktop_config.json`)이 열립니다
5. 이 파일을 **텍스트 편집기**로 엽니다 (파일을 우클릭 → 다음으로 열기 → 텍스트 편집기)

**3단계: 설정 붙여넣기**

파일의 기존 내용을 **전부 지우고** 아래 내용을 붙여넣습니다.
두 군데를 수정하세요:

- `여기에-uvx-경로-붙여넣기` → 1단계에서 복사한 uvx 경로로 교체
- `토큰값을-여기에-입력` → 실제 토큰으로 교체 ([토큰 발급 가이드](docs/setup-guide.md#api-토큰-설정))

```json
{
  "mcpServers": {
    "slack-to-notion": {
      "command": "여기에-uvx-경로-붙여넣기",
      "args": ["--refresh", "slack-to-notion-mcp"],
      "env": {
        "SLACK_USER_TOKEN": "xoxp-토큰값을-여기에-입력",
        "NOTION_API_KEY": "토큰값을-여기에-입력",
        "NOTION_PARENT_PAGE_URL": "https://www.notion.so/페이지-링크를-여기에-붙여넣기"
      }
    }
  }
}
```

예시 (uvx 경로가 `/Users/hong/.local/bin/uvx`인 경우):

```json
{
  "mcpServers": {
    "slack-to-notion": {
      "command": "/Users/hong/.local/bin/uvx",
      "args": ["--refresh", "slack-to-notion-mcp"],
      "env": {
        "SLACK_USER_TOKEN": "xoxp-1234-5678-abcd",
        "NOTION_API_KEY": "ntn_또는secret_로시작하는토큰",
        "NOTION_PARENT_PAGE_URL": "https://www.notion.so/My-Page-abc123"
      }
    }
  }
}
```

> 팀에서 공유하려면 `SLACK_USER_TOKEN` 대신 `SLACK_BOT_TOKEN`(`xoxb-`)을 사용할 수 있습니다.
> 자세한 내용은 [토큰 발급 가이드](docs/setup-guide.md#api-토큰-설정)를 참고하세요.

**4단계: Claude Desktop 재시작**

파일을 저장(`⌘ + S`)하고 Claude Desktop을 **완전히 종료**(Dock에서 우클릭 → 종료)한 뒤 다시 실행합니다.

정상 연결 시: 입력창 우측 하단에 도구 아이콘(🔧)이 나타납니다.

> 재시작해도 오류가 나오면 [문제 해결 가이드](docs/troubleshooting.md)를 확인하세요.

### Claude Code CLI (개발자)

터미널에 아래 명령어를 붙여넣으세요. 안내에 따라 토큰을 입력하면 자동으로 설치됩니다:

```bash
curl -sL https://raw.githubusercontent.com/dykim-base-project/claude-slack-to-notion/main/scripts/setup.sh | bash
```

> 토큰 발급이 처음이라면 [설치 및 토큰 설정 가이드](docs/setup-guide.md)를 참고하세요.

## 사용법

Claude에게 자연어로 말하면 됩니다. 아래 예시를 그대로 복사해서 사용하세요:

```
Slack 채널 목록 보여줘
```

```
#general 채널의 최근 메시지를 Notion에 회의록으로 정리해줘
```

```
#backend 채널에서 이번 주 논의된 버그 이슈만 추려서 정리해줘
```

```
이 스레드 내용을 주제별로 분류해서 Notion 페이지로 만들어줘
```

> 분석 방향은 자유롭게 지정할 수 있습니다. "요약해줘", "액션 아이템만 뽑아줘", "결정사항 위주로 정리해줘" 등 원하는 대로 요청하세요.

## 문제가 생겼나요?

[문제 해결 가이드](docs/troubleshooting.md)를 확인하세요.

## 더 알아보기

- [설치 및 토큰 설정 가이드](docs/setup-guide.md) — 토큰 발급, 업데이트, 수동 설치
- [제공 도구 목록](docs/tools.md) — 플러그인이 제공하는 12개 MCP 도구
- [개발자 가이드](docs/development.md) — 프로젝트 구조, 기술 스택, CI/CD, 기여 방법
- [개발 과정](docs/decisions.md) — 주요 의사결정 히스토리

## 라이선스

MIT
