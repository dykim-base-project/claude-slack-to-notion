# 설치 및 토큰 설정 가이드

이 문서는 claude-slack-to-notion 플러그인의 설치 방법과 API 토큰 발급 절차를 안내합니다.

## 설치 방법

### 방법 1: 대화형 설치 (권장)

터미널에 아래 명령어를 붙여넣으면 안내에 따라 토큰을 입력하고 자동으로 설치됩니다:

```bash
curl -sL https://raw.githubusercontent.com/dykim-base-project/claude-slack-to-notion/main/scripts/setup.sh | bash
```

스크립트가 토큰 형식을 검증하고 `claude mcp add`를 자동 실행합니다.

### 방법 2: 수동 등록 (고급)

아래 명령어로 MCP 서버를 등록할 때 환경변수를 함께 지정합니다:

```bash
claude mcp add slack-to-notion \
  --transport stdio \
  -e SLACK_USER_TOKEN=xoxp-your-token \
  -e NOTION_API_KEY=ntn_your-key \
  -e NOTION_PARENT_PAGE_URL=https://notion.so/your-page \
  -- uvx slack-to-notion-mcp
```

> `uvx`는 실행 시 패키지를 자동으로 다운로드하므로 별도 설치 과정이 없습니다. uv가 설치되어 있어야 합니다.

### 업데이트

**Claude Code CLI:**

```bash
# 방법 1: setup.sh (토큰 자동 재사용, 권장)
curl -sL https://raw.githubusercontent.com/dykim-base-project/claude-slack-to-notion/main/scripts/setup.sh | bash

# 방법 2: 수동 (영구 설치 제거 + 캐시 정리)
uv tool uninstall slack-to-notion-mcp 2>/dev/null; uv cache clean slack-to-notion-mcp --force
```

setup.sh는 기존 설치를 감지하면 자동으로 업데이트 모드로 전환됩니다.
기존 토큰은 자동으로 재사용되므로 토큰을 다시 입력하지 않아도 됩니다.

**Claude Desktop:**

Claude Desktop을 **완전히 종료**한 뒤 터미널에서 아래 명령어를 실행하세요:

```bash
uv tool uninstall slack-to-notion-mcp 2>/dev/null; uv cache clean slack-to-notion-mcp --force
```

이후 Claude Desktop을 다시 실행하면 최신 버전이 자동으로 다운로드됩니다.

> `uv tool uninstall`이 핵심입니다. `uv tool install`로 영구 설치된 환경이 있으면 `uvx`가 PyPI 최신 버전을 무시합니다.

### 설정 확인 및 수정

**설치 확인:**

```bash
claude mcp list
```

**토큰 수정:**

대화형 설치 스크립트를 다시 실행하면 기존 설정을 덮어씁니다.

```bash
curl -sL https://raw.githubusercontent.com/dykim-base-project/claude-slack-to-notion/main/scripts/setup.sh | bash
```

**삭제:**

```bash
claude mcp remove slack-to-notion
```

## API 토큰 설정

이 플러그인은 Slack과 Notion에 접근하기 위해 3개의 토큰이 필요합니다.
각 토큰은 한 번만 발급하면 계속 사용할 수 있습니다.

| 토큰 | 용도 | 형식 |
|------|------|------|
| `SLACK_USER_TOKEN` | Slack 채널 메시지 읽기 (권장) | `xoxp-`로 시작 |
| `SLACK_BOT_TOKEN` | Slack 채널 메시지 읽기 (팀 공유 시) | `xoxb-`로 시작 |
| `NOTION_API_KEY` | Notion 페이지 생성 | `ntn_` 또는 `secret_`로 시작 |
| `NOTION_PARENT_PAGE_URL` | 분석 결과가 저장될 Notion 페이지 | 페이지 링크 또는 32자 ID |

> `SLACK_USER_TOKEN`과 `SLACK_BOT_TOKEN` 중 **하나만 설정**하면 됩니다. 둘 다 설정하면 Bot 토큰이 사용됩니다.

### 1단계: Slack 토큰 발급

Slack 채널의 메시지를 읽어오려면 Slack App을 만들고 토큰을 발급받아야 합니다.
**사용자 토큰**과 **Bot 토큰**, 두 가지 방식이 있습니다.

| | 사용자 토큰 (권장) | Bot 토큰 (팀 공유 시) |
|---|---|---|
| 채널 접근 | 본인이 참여한 채널에 바로 접근 | 채널에 앱을 추가해야 함 |
| 설정 난이도 | 토큰 발급만 하면 끝 | 토큰 발급 + 채널마다 앱 초대 필요 |
| 설정 공유 | 각자 본인 토큰을 발급 | 한 명이 설정 후 `.env` 파일 공유 가능 |
| 지속성 | 토큰 발급자가 워크스페이스를 떠나면 중단 | 채널이 있는 한 계속 동작 |
| 적합한 경우 | 혼자 빠르게 시작 | 팀에서 함께 사용, 안정적 운영 |

#### 방식 A: 사용자 토큰 발급 (권장)

본인 계정의 권한으로 메시지를 읽는 방식입니다. 채널에 앱을 추가할 필요 없이, 토큰만 발급하면 바로 사용할 수 있습니다.

1. [Slack API](https://api.slack.com/apps) 페이지에 접속하여 로그인합니다.
2. **"Create New App"** 버튼 클릭 → **"From scratch"** 선택
3. App 이름(예: `slack-analyzer`)을 입력하고, 사용할 Workspace를 선택한 뒤 **"Create App"** 클릭
4. 왼쪽 메뉴에서 **"OAuth & Permissions"** 클릭
5. 아래로 스크롤하여 **"User Token Scopes"** 섹션에서 다음 4개 권한을 추가합니다:

| 스코프 | 설명 |
|--------|------|
| `channels:history` | 공개 채널의 메시지를 읽습니다 |
| `channels:read` | 채널 목록을 조회합니다 |
| `groups:history` | 비공개 채널의 메시지를 읽습니다 |
| `users:read` | 메시지 작성자의 이름을 확인합니다 |

6. 페이지 상단으로 스크롤하여 **"Install to Workspace"** 클릭 → **"허용"** 클릭
7. **"User OAuth Token"** 이 표시됩니다. 복사 버튼을 눌러 토큰을 복사합니다. (`xoxp-`로 시작하는 문자열)

> 스코프를 나중에 추가한 경우, **"Reinstall to Workspace"** 를 클릭해야 반영됩니다. 재설치해도 토큰 값은 변경되지 않습니다.

> 사용자 토큰은 발급한 본인이 참여한 채널에만 접근할 수 있습니다. 본인이 워크스페이스를 떠나면 토큰이 무효화됩니다.

#### 방식 B: Bot 토큰 발급 (팀 공유 시)

팀에서 하나의 토큰을 공유하려면 Bot 토큰을 사용합니다.
방식 A의 1~4단계까지 동일하게 Slack App을 생성한 뒤, 아래를 따르세요.

1. **"OAuth & Permissions"** 에서 아래로 스크롤하여 **"Bot Token Scopes"** 섹션에 다음 권한을 추가합니다:

| 스코프 | 설명 |
|--------|------|
| `channels:history` | 공개 채널의 메시지를 읽습니다 |
| `channels:read` | 채널 목록을 조회합니다 |
| `groups:history` | 비공개 채널의 메시지를 읽습니다 |
| `users:read` | 메시지 작성자의 이름을 확인합니다 |

> 비공개 채널 목록도 조회하려면 `groups:read` 스코프를 추가하세요. 없어도 공개 채널은 정상 동작합니다.

2. 페이지 상단으로 스크롤하여 **"Install to Workspace"** 클릭 → **"허용"** 클릭

> 이미 방식 A로 앱을 설치한 경우, **"Reinstall to Workspace"** 버튼이 표시됩니다. 클릭하여 재설치해야 Bot Token Scopes가 반영됩니다.

3. 설치(또는 재설치) 완료 후, 같은 **"OAuth & Permissions"** 페이지 상단의 **"OAuth Tokens for Your Workspace"** 섹션을 확인합니다. **"Bot User OAuth Token"** 항목이 표시됩니다. 복사 버튼을 눌러 토큰을 복사합니다. (`xoxb-`로 시작하는 문자열)

**Bot을 채널에 초대하기:**

Bot은 초대된 채널만 접근할 수 있습니다. 메시지를 수집할 각 채널에서 Bot을 초대하세요.

- 채널 상단의 채널 이름 클릭 → **"Integrations"** 탭 → **"Add apps"** → App 검색하여 추가

> 여러 채널에서 사용하려면 각 채널마다 Bot을 초대해야 합니다.

### 2단계: Notion API Key 발급

Notion Integration은 분석 결과를 Notion 페이지로 작성하는 역할을 합니다.

1. [Notion 내 API 통합](https://www.notion.so/my-integrations) 페이지에 접속하여 로그인합니다.
2. **"새 API 통합 만들기"** 버튼 클릭
3. **"통합 유형"** 에서 **"내부"** 를 선택합니다 (팀 워크스페이스 내부에서만 사용)
4. 다음 항목을 입력합니다:
   - **이름**: Integration 이름 (예: `slack-analyzer`)
   - **연결된 워크스페이스**: 사용할 Notion 워크스페이스 선택
5. **"저장"** 클릭
6. **"내부 통합 시크릿"** 이 표시됩니다. **"표시"** → 복사 버튼을 눌러 토큰을 복사합니다. (`ntn_` 또는 `secret_`로 시작하는 문자열)

> 시크릿 조회 시 400 에러가 발생하면 **시크릿 브라우징(incognito)** 모드에서 다시 시도하세요. 브라우저 캐시나 확장 프로그램이 간섭할 수 있습니다.

**Integration을 Notion 페이지에 연결하기:**

Integration은 연결된 페이지만 접근할 수 있습니다. 분석 결과를 저장할 페이지에 Integration을 연결하세요.

1. Notion에서 분석 결과를 저장할 페이지를 엽니다 (새 페이지를 만들어도 됩니다)
2. 페이지 우측 상단의 **`...`** (점 3개) 버튼 클릭
3. **"연결"** 항목에서 위에서 만든 Integration 이름(예: `slack-analyzer`)을 검색하여 선택
4. **"확인"** 클릭

### 3단계: Notion 페이지 링크 복사

분석 결과가 저장될 Notion 페이지의 링크를 복사합니다.

1. 2단계에서 Integration을 연결한 Notion 페이지를 엽니다
2. 페이지 우측 상단의 **`...`** (점 3개) 버튼 클릭 → **"링크 복사"** 클릭
3. 복사된 링크를 설치 시 환경변수 값으로 사용합니다

> Page ID가 자동으로 추출되므로 URL에서 ID를 직접 찾을 필요가 없습니다.

### 4단계: 환경변수 설정

발급받은 3개 토큰을 환경변수로 설정합니다.

**대화형 설치 또는 수동 등록으로 설치한 경우:**

설치 시 `-e` 플래그로 환경변수를 함께 지정합니다. 발급받은 실제 토큰 값으로 교체하세요:

```bash
claude mcp add slack-to-notion \
  --transport stdio \
  -e SLACK_USER_TOKEN=xoxp-1234-5678-abcdefgh \
  -e NOTION_API_KEY=ntn_abc123def456... \
  -e NOTION_PARENT_PAGE_URL=https://www.notion.so/abc123def456...?source=copy_link \
  -- uvx slack-to-notion-mcp
```

> `NOTION_PARENT_PAGE_URL`에는 Notion 페이지 URL을 그대로 붙여넣으면 됩니다. Page ID가 자동으로 추출됩니다.

**로컬 개발 환경의 경우:**

레포 루트에 `.env` 파일을 생성합니다:

```bash
cp .env.example .env
# .env 파일을 편집기로 열어 토큰 값 입력
```

```
# 방식 A를 선택한 경우 (사용자 토큰)
SLACK_USER_TOKEN=xoxp-1234-5678-abcdefgh                                          ← 1단계에서 복사한 값

# 방식 B를 선택한 경우 (Bot 토큰) — 둘 중 하나만 설정
# SLACK_BOT_TOKEN=xoxb-1234-5678-abcdefgh                                        ← 1단계에서 복사한 값

NOTION_API_KEY=ntn_abc123def456...                                                 ← 2단계에서 복사한 값
NOTION_PARENT_PAGE_URL=https://www.notion.so/abc123def456...?source=copy_link       ← 3단계에서 복사한 링크
```

> `.env` 파일에는 토큰이 포함되어 있으므로 Git에 업로드되지 않도록 `.gitignore`에 이미 등록되어 있습니다.
