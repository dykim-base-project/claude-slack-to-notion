# claude-slack-to-notion

Slack 메시지/스레드를 분석하여 Notion 페이지로 정리하는 Claude Code 플러그인

## 목차

- [개요](#개요)
- [시작하기](#시작하기)
- [개발 과정](#개발-과정)
- [개발자 가이드](#개발자-가이드)
- [참고 자료](#참고-자료)
- [라이선스](#라이선스)

## 개요

`claude-slack-to-notion`은 Slack 채널의 대화 내용을 수집·분석하여 이슈/태스크로 구조화하고, Notion 페이지로 자동 정리하는 도구입니다.
정리된 Notion 페이지를 기반으로 팀 협업을 진행하는 워크플로우를 제공합니다.

### 주요 기능

- **Slack 채널 메시지/스레드 수집**: Slack API를 통해 채널 메시지 및 스레드 댓글 조회
- **메시지 분석 및 구조화**: AI 기반 내용 분석, 토픽 분류, 이슈/태스크 도출
- **Notion 페이지 자동 생성**: 분석된 이슈/태스크를 Notion 페이지로 작성하여 협업 기반 제공

### 데이터 흐름

```mermaid
graph LR
    A["Slack API"] -->|메시지/스레드 수집| B["MCP 도구"]
    B -->|포맷팅된 메시지| C["Claude Code"]
    C -->|분석 결과| D["Notion API"]
    D -->|페이지 생성| E["Notion 페이지"]
    E -->|협업 기반| F["팀 협업"]
```

1. MCP 도구로 Slack 채널 메시지 및 스레드 수집
2. 수집된 메시지를 분석용 텍스트로 포맷팅
3. Claude Code가 사용자 지정 방향에 따라 내용 분석
4. 분석 결과를 Notion 페이지로 자동 생성
5. 정리된 Notion 페이지를 기반으로 팀 협업 진행

## 시작하기

### 요구사항

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- [uv](https://docs.astral.sh/uv/) (macOS: `brew install uv` / 기타: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Slack 토큰 (Bot Token 또는 User Token 중 택 1)
- Notion API Key
- Notion Parent Page ID

### 설치

#### 방법 1: 마켓플레이스 설치 (권장)

```
/install-plugin slack-to-notion
```

> 마켓플레이스 등록 후 사용 가능합니다. 등록 전까지는 방법 2를 사용하세요.

#### 방법 2: 대화형 설치

터미널에 아래 명령어를 붙여넣으면 안내에 따라 토큰을 입력하고 자동으로 설치됩니다:

```bash
curl -sL https://raw.githubusercontent.com/dykim-base-project/claude-slack-to-notion/main/scripts/setup.sh | bash
```

스크립트가 토큰 형식을 검증하고 `claude mcp add`를 자동 실행합니다.
각 토큰 발급 방법은 아래 [API 토큰 설정](#api-토큰-설정)을 참고하세요.

#### 업데이트

이미 설치된 경우 동일한 명령으로 업데이트할 수 있습니다:

```bash
# 방법 1: setup.sh (토큰 자동 재사용)
curl -sL https://raw.githubusercontent.com/dykim-base-project/claude-slack-to-notion/main/scripts/setup.sh | bash

# 방법 2: uvx 직접 실행 (캐시 초기화 후 최신 버전)
uv cache clean slack-to-notion-mcp && uvx slack-to-notion-mcp@latest --help
```

setup.sh는 기존 설치를 감지하면 자동으로 업데이트 모드로 전환됩니다.
기존 토큰은 자동으로 재사용되므로 토큰을 다시 입력하지 않아도 됩니다.

#### 방법 3: 수동 등록 (고급)

아래 명령어로 MCP 서버를 등록할 때 환경변수를 함께 지정합니다:

```bash
claude mcp add slack-to-notion \
  --transport stdio \
  -e SLACK_BOT_TOKEN=xoxb-your-token \
  -e NOTION_API_KEY=secret_your-key \
  -e NOTION_PARENT_PAGE_ID=https://notion.so/your-page \
  -- uvx slack-to-notion-mcp
```

각 토큰 발급 방법은 아래 [API 토큰 설정](#api-토큰-설정)을 참고하세요.

> `uvx`는 실행 시 패키지를 자동으로 다운로드하므로 별도 설치 과정이 없습니다. uv가 설치되어 있어야 합니다.

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

### API 토큰 설정

이 플러그인은 Slack과 Notion에 접근하기 위해 3개의 토큰이 필요합니다.
각 토큰은 한 번만 발급하면 계속 사용할 수 있습니다.

| 토큰 | 용도 | 형식 |
|------|------|------|
| `SLACK_BOT_TOKEN` | Slack 채널 메시지 읽기 (권장) | `xoxb-`로 시작 |
| `SLACK_USER_TOKEN` | Slack 채널 메시지 읽기 (대안) | `xoxp-`로 시작 |
| `NOTION_API_KEY` | Notion 페이지 생성 | `ntn_` 또는 `secret_`로 시작 |
| `NOTION_PARENT_PAGE_ID` | 분석 결과가 저장될 Notion 페이지 | 페이지 링크 또는 32자 ID |

> `SLACK_BOT_TOKEN`과 `SLACK_USER_TOKEN` 중 **하나만 설정**하면 됩니다. 둘 다 설정하면 Bot 토큰이 사용됩니다.

#### 1단계: Slack 토큰 발급

Slack 채널의 메시지를 읽어오려면 Slack App을 만들고 토큰을 발급받아야 합니다.
**Bot 토큰**과 **사용자 토큰**, 두 가지 방식이 있습니다.

| | Bot 토큰 (권장) | 사용자 토큰 (대안) |
|---|---|---|
| 채널 접근 | 채널에 앱을 추가해야 함 | 본인이 참여한 채널에 바로 접근 |
| 설정 공유 | 한 명이 설정 후 `.env` 파일 공유 가능 | 각자 본인 토큰을 발급 |
| 지속성 | 채널이 있는 한 계속 동작 | 토큰 발급자가 워크스페이스를 떠나면 중단 |
| 적합한 경우 | 팀에서 함께 사용, 안정적 운영 | 혼자 빠르게 시작, 앱 추가가 어려운 채널 |

##### 방식 A: Bot 토큰 발급 (권장)

1. [Slack API](https://api.slack.com/apps) 페이지에 접속하여 로그인합니다.
2. **"Create New App"** 버튼 클릭 → **"From scratch"** 선택
3. App 이름(예: `slack-analyzer`)을 입력하고, 사용할 Workspace를 선택한 뒤 **"Create App"** 클릭
4. 왼쪽 메뉴에서 **"OAuth & Permissions"** 클릭
5. 아래로 스크롤하여 **"Bot Token Scopes"** 섹션에서 다음 4개 권한을 추가합니다:

| 스코프 | 설명 |
|--------|------|
| `channels:history` | 공개 채널의 메시지를 읽습니다 |
| `channels:read` | 채널 목록을 조회합니다 |
| `groups:history` | 비공개 채널의 메시지를 읽습니다 |
| `users:read` | 메시지 작성자의 이름을 확인합니다 |

> 비공개 채널 목록도 조회하려면 `groups:read` 스코프를 추가하세요. 없어도 공개 채널은 정상 동작합니다.

6. 페이지 상단으로 스크롤하여 **"Install to Workspace"** 클릭 → **"허용"** 클릭
7. **"Bot User OAuth Token"** 이 표시됩니다. 복사 버튼을 눌러 토큰을 복사합니다. (`xoxb-`로 시작하는 문자열)

> 스코프를 나중에 추가한 경우, **"Reinstall to Workspace"** 를 클릭해야 반영됩니다. 재설치해도 토큰 값은 변경되지 않습니다.

**Bot을 채널에 초대하기:**

Bot은 초대된 채널만 접근할 수 있습니다. 메시지를 수집할 각 채널에서 Bot을 초대하세요.

- 채널 상단의 채널 이름 클릭 → **"Integrations"** 탭 → **"Add apps"** → App 검색하여 추가

> 여러 채널에서 사용하려면 각 채널마다 Bot을 초대해야 합니다.

##### 방식 B: 사용자 토큰 발급 (대안)

채널에 앱을 추가하지 않고, 본인 계정의 권한으로 메시지를 읽는 방식입니다.
방식 A의 1~4단계까지 동일하게 Slack App을 생성한 뒤, 아래를 따르세요.

1. **"OAuth & Permissions"** 에서 아래로 스크롤하여 **"User Token Scopes"** 섹션에 다음 권한을 추가합니다:

| 스코프 | 설명 |
|--------|------|
| `channels:history` | 공개 채널의 메시지를 읽습니다 |
| `channels:read` | 채널 목록을 조회합니다 |
| `groups:history` | 비공개 채널의 메시지를 읽습니다 |
| `users:read` | 메시지 작성자의 이름을 확인합니다 |

2. 페이지 상단으로 스크롤하여 **"Install to Workspace"** 클릭 → **"허용"** 클릭

> 이미 방식 A로 앱을 설치한 경우, **"Reinstall to Workspace"** 버튼이 표시됩니다. 클릭하여 재설치해야 User Token Scopes가 반영됩니다. 재설치 후에도 토큰이 보이지 않으면 페이지를 새로고침하거나 **"Reinstall to Workspace"** 를 한 번 더 클릭하세요.

3. 설치(또는 재설치) 완료 후, 같은 **"OAuth & Permissions"** 페이지 상단의 **"OAuth Tokens for Your Workspace"** 섹션을 확인합니다. **"User OAuth Token"** 항목이 새로 표시됩니다. 복사 버튼을 눌러 토큰을 복사합니다. (`xoxp-`로 시작하는 문자열)

> 방식 A를 먼저 설정한 경우, Bot User OAuth Token(`xoxb-`)과 User OAuth Token(`xoxp-`) 두 개가 함께 표시됩니다. **User OAuth Token** 을 복사하세요.

> 사용자 토큰은 발급한 본인이 참여한 채널에만 접근할 수 있습니다. 본인이 워크스페이스를 떠나면 토큰이 무효화됩니다.

#### 2단계: Notion API Key 발급

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

#### 3단계: Notion 페이지 링크 복사

분석 결과가 저장될 Notion 페이지의 링크를 복사합니다.

1. 2단계에서 Integration을 연결한 Notion 페이지를 엽니다
2. 페이지 우측 상단의 **`...`** (점 3개) 버튼 클릭 → **"링크 복사"** 클릭
3. 복사된 링크를 4단계에서 환경변수 값으로 사용합니다

> Page ID가 자동으로 추출되므로 URL에서 ID를 직접 찾을 필요가 없습니다.

#### 4단계: 환경변수 설정

발급받은 3개 토큰을 환경변수로 설정합니다.

**대화형 설치 또는 수동 등록으로 설치한 경우:**

[설치 섹션](#설치)의 방법 2 또는 방법 3에서 `-e` 플래그로 환경변수를 함께 지정합니다. 발급받은 실제 토큰 값으로 교체하세요:

```bash
claude mcp add slack-to-notion \
  --transport stdio \
  -e SLACK_BOT_TOKEN=xoxb-1234-5678-abcdefgh \
  -e NOTION_API_KEY=secret_abc123def456... \
  -e NOTION_PARENT_PAGE_ID=https://www.notion.so/abc123def456...?source=copy_link \
  -- uvx slack-to-notion-mcp
```

> `NOTION_PARENT_PAGE_ID`에는 Notion 페이지 URL을 그대로 붙여넣으면 됩니다. Page ID가 자동으로 추출됩니다.

**로컬 개발 환경의 경우:**

레포 루트에 `.env` 파일을 생성합니다:

```bash
cp .env.example .env
# .env 파일을 편집기로 열어 토큰 값 입력
```

```
# 방식 A를 선택한 경우 (Bot 토큰)
SLACK_BOT_TOKEN=xoxb-1234-5678-abcdefgh                                          ← 1단계에서 복사한 값

# 방식 B를 선택한 경우 (사용자 토큰) — 둘 중 하나만 설정
# SLACK_USER_TOKEN=xoxp-1234-5678-abcdefgh                                       ← 1단계에서 복사한 값

NOTION_API_KEY=secret_abc123def456...                                              ← 2단계에서 복사한 값
NOTION_PARENT_PAGE_ID=https://www.notion.so/abc123def456...?source=copy_link       ← 3단계에서 복사한 링크
```

> `.env` 파일에는 토큰이 포함되어 있으므로 Git에 업로드되지 않도록 `.gitignore`에 이미 등록되어 있습니다.

### 사용 방법

Claude Code에서 자연어로 사용할 수 있습니다.

#### 사용 예시

```
Slack #general 채널 메시지 조회해줘
```

```
#design 채널의 최근 50개 메시지를 Notion에 정리해줘
```

```
이 스레드 내용을 주제별로 분류해서 Notion 페이지로 만들어줘
```

```
#backend 채널에서 이번 주 논의된 버그 이슈만 추려서 정리해줘
```

> 분석 방향은 사용자가 자유롭게 지정할 수 있습니다. 분석 방향 안내 도구로 예시를 확인할 수 있습니다.

### 제공 도구

**Slack 수집**

| 도구 | 설명 |
|------|------|
| `list_channels` | Slack 채널 목록 조회 |
| `fetch_messages` | 특정 채널의 메시지 조회 |
| `fetch_thread` | 특정 스레드의 전체 메시지 조회 |
| `fetch_threads` | 여러 스레드를 한 번에 수집하고 AI 분석용으로 포맷팅 |
| `fetch_channel_info` | 채널 상세 정보 조회 |

**분석**

| 도구 | 설명 |
|------|------|
| `get_analysis_guide_tool` | 분석 방향 안내 (예시 포함) |
| `format_messages` | 수집된 메시지를 AI 분석용 텍스트로 포맷팅 |

**Notion**

| 도구 | 설명 |
|------|------|
| `create_notion_page` | 분석 결과를 Notion 페이지로 생성 |
| `save_analysis_result` | 분석 결과를 로컬 JSON 파일로 백업 |

**커스터마이징**

| 도구 | 설명 |
|------|------|
| `save_preference_tool` | 사용자의 분석 선호도 저장 ("기억해줘", "앞으로 ~해줘") |
| `get_preferences` | 저장된 분석 선호도 조회 (분석 전 자동 참조) |
| `list_analysis_history` | 과거 분석 결과 히스토리 조회 ("지난번처럼 해줘") |

### 제약사항

- **API 토큰 관리**: Slack API 토큰, Notion API 키는 환경변수로 관리 (Git 추적 금지)
- **개인 메시지(DM) 제외**: 보안상 개인 DM 수집 지원하지 않음
- **API Rate Limit**: Slack/Notion API Rate Limit 고려 필요 (과도한 요청 시 제한 발생 가능)
- **채널 접근**: Bot 토큰 사용 시 채널에 앱 초대 필요, 사용자 토큰 사용 시 본인이 참여한 채널만 접근 가능

### 문제 해결

| 증상 | 원인 | 해결 방법 |
|------|------|-----------|
| 설치 후 첫 실행에서 플러그인이 인식되지 않음 | Claude Code CLI 설정 파일 캐시/타이밍 이슈 | `/exit`으로 종료 후 `claude`를 다시 실행하면 정상 동작합니다 |
| `uvx: command not found` | uv 미설치 | `brew install uv` 또는 [uv 설치 가이드](https://docs.astral.sh/uv/getting-started/installation/) 참고 |
| `No module named slack_to_notion` | 패키지 배포 전 | PyPI 배포 후 해결. 개발 중에는 `uvx --from . slack-to-notion-mcp` 사용 |
| `SLACK_BOT_TOKEN 또는 SLACK_USER_TOKEN 환경변수가 설정되지 않았습니다` | 환경변수 미설정 | [4단계: 환경변수 설정](#4단계-환경변수-설정) 참고 |
| `not_in_channel` 에러 (Bot 토큰) | Bot이 해당 채널에 초대되지 않음 | 채널 설정 → Integrations → Add apps에서 Bot 추가 ([방식 A](#방식-a-bot-토큰-발급-권장) 참고) |
| `not_in_channel` 에러 (사용자 토큰) | 해당 채널에 참여하지 않음 | Slack에서 채널에 참여한 뒤 다시 시도 |
| `invalid_auth` 에러 | 토큰이 잘못되었거나 만료됨 | [Slack API](https://api.slack.com/apps)에서 토큰 재확인 후 환경변수 수정 |
| `Notion API 키가 올바르지 않습니다` | Notion API Key가 잘못됨 | [Notion Integrations](https://www.notion.so/my-integrations)에서 Secret 재확인 |
| `Notion 페이지를 찾을 수 없습니다` | Integration이 페이지에 연결되지 않음 | [2단계](#2단계-notion-api-key-발급)의 "Integration을 Notion 페이지에 연결하기" 참고 |

## 개발 과정

이 프로젝트는 GitHub Issue + PR로 전체 히스토리를 관리합니다.
초기 구조(#6) → Slack 수집(#7) → 분석 모듈(#8) → Notion 연동(#9) → MCP 서버 통합(#21) → E2E 검증 및 리팩토링(#32) 순서로 진행되었으며, 각 단계의 의사결정은 Issue/PR에서 확인할 수 있습니다.

### 주요 의사결정

**Notion DB → 직접 페이지 생성으로 전환**

초기 설계에서는 Notion Database에 분석 결과를 저장하는 구조였습니다.
E2E 테스트 과정에서 Notion API가 한글 프로퍼티명을 정상 반환하지 않는 호환 이슈를 발견했고, DB 스키마 관리의 복잡도 대비 실사용 가치를 재평가했습니다.
Slack 대화 특성상 나이브하게 진행되는 스레드가 많아 지나친 체계화가 오히려 독이 될 수 있다고 판단하여, 상위 페이지 하위에 직접 페이지를 생성하는 방식으로 전환했습니다. DB 대시보드는 실사용 후 필요성이 검증되면 추가하는 방향으로 남겨두었습니다. (#32)

**비개발자 설정 가이드 — 직접 따라하며 검증**

README 설정 가이드를 작성한 뒤 실제로 처음부터 따라가며 검증했습니다.
그 과정에서 발견한 것들: Notion UI가 한글화되어 있어 영문 가이드가 무의미한 점, `/invite @봇이름`이 App에는 동작하지 않는 점, "notion" 단어가 Integration 이름에 사용 금지인 점, Notion 페이지 URL에서 32자 ID를 직접 추출하라는 안내가 비개발자에게 불친절한 점 등.
이를 반영하여 URL을 그대로 붙여넣으면 Page ID가 자동 추출되도록 코드를 수정하고, 가이드의 모든 UI 용어를 실제 화면 기준으로 교정했습니다. (#26, #32)

**복수 스레드 수집 — AI 분석 범위를 사용자가 제한**

채널의 모든 대화를 AI가 자동으로 연관성 판단하여 묶는 방식을 검토했으나, 할루시네이션 위험과 과도한 해석 가능성 때문에 채택하지 않았습니다.
대신 사용자가 연관 스레드를 직접 선택하면 플러그인이 수집·포맷하고, AI는 정리에만 집중하는 구조로 설계했습니다. 판단은 사람이, 실행은 AI가 맡는 역할 분리입니다. (#32)

<!-- 개발 과정에 대한 상세 포스팅은 추후 작성 예정입니다. -->

## 개발자 가이드

### 프로젝트 구조

```
claude-slack-to-notion/
├── .claude-plugin/
│   └── plugin.json                  # 플러그인 매니페스트
├── .mcp.json                        # MCP 서버 설정
├── scripts/
│   └── setup.sh                     # 대화형 설치 스크립트
├── src/
│   └── slack_to_notion/
│       ├── __init__.py              # 패키지 초기화
│       ├── __main__.py              # python -m 실행 지원
│       ├── mcp_server.py            # MCP 서버 (도구 제공)
│       ├── slack_client.py          # Slack API 연동
│       ├── analyzer.py              # AI 분석 엔진
│       └── notion_client.py         # Notion API 연동
├── tests/                           # 단위 테스트
├── pyproject.toml                   # Python 패키지 설정
├── CLAUDE.md                        # AI 협업 가이드
├── README.md
└── .gitignore
```

### 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.10+ |
| 빌드 시스템 | setuptools, wheel |
| Slack 연동 | slack_sdk >= 3.27.0 |
| Notion 연동 | notion-client >= 2.2.0 |
| MCP 서버 | mcp[cli] >= 1.0.0 |
| 개발 도구 | pytest, ruff |

### 로컬 개발 환경

```bash
git clone https://github.com/dykim-base-project/claude-slack-to-notion.git
cd claude-slack-to-notion
uv sync --dev
```

실행:

```bash
# MCP 서버 직접 실행
uv run slack-to-notion-mcp

# 또는 모듈로 실행
uv run python -m slack_to_notion
```

### 기여 방법

이슈 및 PR은 [GitHub 레포지토리](https://github.com/dykim-base-project/claude-slack-to-notion)에서 관리합니다.
개발 프로세스(Git Flow, 브랜치 전략, 커밋 컨벤션)는 [CLAUDE.md](./CLAUDE.md)를 참고하세요.

## 참고 자료

- [Slack API Documentation](https://api.slack.com/docs)
- [Notion API Documentation](https://developers.notion.com/)
- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)

## 라이선스

MIT
