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

### Desktop Extension 설치 (권장)

`.mcpb` 파일을 사용하면 JSON 수동 편집 없이 원클릭으로 설치할 수 있습니다.

**사전 준비: 토큰 발급** (처음 한 번만)

설치 시 아래 3개의 값이 필요합니다. 미리 준비해두세요:

| 항목 | 발급 방법 | 형식 |
|------|-----------|------|
| Slack User Token | [api.slack.com/apps](https://api.slack.com/apps) → 앱 선택 → OAuth & Permissions → User OAuth Token | `xoxp-...` |
| Notion API Key | [notion.so/profile/integrations](https://www.notion.so/profile/integrations) → 새 API 통합 생성 | `ntn_...` |
| Notion Page URL | 결과를 저장할 Notion 페이지 → 우측 상단 **공유** → **링크 복사** | `https://www.notion.so/...` |

> 토큰 발급이 처음이라면 [설치 및 토큰 설정 가이드](docs/setup-guide.md)에서 스크린샷과 함께 단계별로 안내합니다.

**설치**

1. [GitHub Releases](https://github.com/dykim-base-project/claude-slack-to-notion/releases)에서 최신 `slack-to-notion-mcp.mcpb` 파일을 다운로드합니다
2. 다운로드한 `.mcpb` 파일을 **더블클릭**합니다
3. Claude Desktop이 열리며 토큰 입력 화면이 나타납니다 — 위에서 준비한 3개의 값을 붙여넣으세요
4. **확장 활성화**: 설치 후 **설정**(`⌘ + ,`) → **Extensions** → `Slack to Notion` 항목의 **토글을 켜주세요** (설치 직후에는 비활성화 상태입니다)
5. 설치 완료! 입력창 우측 하단에 도구 아이콘이 나타나면 정상입니다

> 업데이트할 때도 새 `.mcpb` 파일을 다운로드하여 동일하게 설치하면 됩니다.

### 수동 설치 (고급)

JSON 설정 파일을 직접 편집하는 방법입니다. Desktop Extension 설치가 안 되는 경우에 사용하세요.

<details>
<summary>수동 설치 방법 보기</summary>

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

정상 연결 시: 입력창 우측 하단에 도구 아이콘이 나타납니다.

> 재시작해도 오류가 나오면 [문제 해결 가이드](docs/troubleshooting.md)를 확인하세요.

</details>

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

## 활용 팁

### 분석 스타일 기억시키기

매번 분석 방향을 설명하는 대신, 한 번만 알려주면 다음부터 자동으로 적용됩니다:

```
앞으로 회의록은 결정사항과 액션 아이템 위주로 정리해줘. 기억해줘.
```

```
Slack 메시지 정리할 때 항상 날짜별로 묶어서 정리해줘. 기억해줘.
```

이렇게 말하면 선호도가 저장되어, 이후 분석 시 자동으로 반영됩니다.

### 분석 결과 고도화하기

한 번에 완벽한 결과를 기대하기보다, 대화를 이어가며 다듬어 보세요:

```
이 회의록에서 후속 조치가 필요한 항목만 따로 뽑아줘
```

```
방금 정리한 내용에서 담당자별로 다시 분류해줘
```

### 멘션된 스레드 분석 요청하기

멘션은 보통 논의 끝에 CC나 확인 요청으로 달리므로, 멘션된 댓글만 보면 맥락을 놓칩니다.

```
이 스레드에서 내가 멘션된 맥락을 파악해서, 내가 알아야 할 내용과 해야 할 일을 정리해줘
```

## 문제가 생겼나요?

[문제 해결 가이드](docs/troubleshooting.md)를 확인하세요.

## 더 알아보기

- [설치 및 토큰 설정 가이드](docs/setup-guide.md) — 토큰 발급, 업데이트, 수동 설치
- [제공 도구 목록](docs/tools.md) — 플러그인이 제공하는 12개 MCP 도구
- [개발자 가이드](docs/development.md) — 프로젝트 구조, 기술 스택, CI/CD, 기여 방법
- [개발 과정](docs/decisions.md) — 주요 의사결정 히스토리

## 라이선스

MIT
