# claude-slack-to-notion

Slack 메시지/스레드를 분석하여 Notion 페이지로 정리하는 Claude Code 플러그인

## 목차

- [개요](#개요)
- [시작하기](#시작하기)
- [개발 철학](#개발-철학)
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
    D -->|페이지 생성| E["Notion Database"]
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
- Python 3.10 이상 (macOS: `brew install python3`)
- Slack Bot Token
- Notion API Key
- Notion Parent Page ID

### 설치

```bash
# 로컬 클론 후 설치
git clone https://github.com/dykim-base-project/claude-slack-to-notion.git
claude --plugin-dir ./claude-slack-to-notion
```

> 최초 실행 시 Python 환경(venv)이 자동으로 설정됩니다.
> 현재 **macOS/Linux**만 지원합니다.

### API 토큰 설정

이 플러그인은 Slack과 Notion에 접근하기 위해 3개의 토큰이 필요합니다.
각 토큰은 한 번만 발급하면 계속 사용할 수 있습니다.

| 토큰 | 용도 | 형식 |
|------|------|------|
| `SLACK_BOT_TOKEN` | Slack 채널 메시지 읽기 | `xoxb-`로 시작 |
| `NOTION_API_KEY` | Notion 페이지 생성 | `secret_`로 시작 |
| `NOTION_PARENT_PAGE_ID` | 분석 결과가 저장될 Notion 페이지 | 32자 영숫자 |

#### 1단계: Slack Bot Token 발급

Slack Bot은 채널의 메시지를 읽어오는 역할을 합니다.
Bot이 **초대된 채널**의 메시지만 읽을 수 있으므로, 사용할 채널에 Bot을 초대해야 합니다.

1. [Slack API](https://api.slack.com/apps) 페이지에 접속하여 로그인합니다.
2. **"Create New App"** 버튼 클릭 → **"From scratch"** 선택
3. App 이름(예: `slack-to-notion`)을 입력하고, 사용할 Workspace를 선택한 뒤 **"Create App"** 클릭
4. 왼쪽 메뉴에서 **"OAuth & Permissions"** 클릭
5. 아래로 스크롤하여 **"Bot Token Scopes"** 섹션에서 다음 4개 권한을 추가합니다:

| 스코프 | 설명 |
|--------|------|
| `channels:history` | 공개 채널의 메시지를 읽습니다 |
| `channels:read` | 채널 목록을 조회합니다 |
| `groups:history` | 비공개 채널의 메시지를 읽습니다 |
| `users:read` | 메시지 작성자의 이름을 확인합니다 |

6. 페이지 상단으로 스크롤하여 **"Install to Workspace"** 클릭 → **"허용"** 클릭
7. **"Bot User OAuth Token"** 이 표시됩니다. 복사 버튼을 눌러 토큰을 복사합니다. (`xoxb-`로 시작하는 문자열)

**Bot을 채널에 초대하기:**

Bot은 초대된 채널만 접근할 수 있습니다. 메시지를 수집할 각 채널에서 Bot을 초대하세요.

- **방법 1**: 채널 메시지 입력창에 `/invite @slack-to-notion` 입력 (App 이름으로 검색)
- **방법 2**: 채널 상단의 채널 이름 클릭 → **"Integrations"** 탭 → **"Add apps"** → App 검색하여 추가

> 여러 채널에서 사용하려면 각 채널마다 Bot을 초대해야 합니다.

#### 2단계: Notion API Key 발급

Notion Integration은 분석 결과를 Notion 페이지로 작성하는 역할을 합니다.

1. [Notion Integrations](https://www.notion.so/my-integrations) 페이지에 접속하여 로그인합니다.
2. **"New integration"** 버튼 클릭
3. 다음 항목을 입력합니다:
   - **Name**: Integration 이름 (예: `slack-to-notion`)
   - **Associated workspace**: 사용할 Notion 워크스페이스 선택
4. **"Capabilities"** 섹션에서 다음이 체크되어 있는지 확인합니다:
   - Read content
   - Update content
   - Insert content
5. **"Submit"** 클릭
6. **"Internal Integration Secret"** 이 표시됩니다. **"Show"** → **"Copy"** 버튼을 눌러 토큰을 복사합니다. (`secret_`로 시작하는 문자열)

**Integration을 Notion 페이지에 연결하기:**

Integration은 연결된 페이지만 접근할 수 있습니다. 분석 결과를 저장할 페이지에 Integration을 연결하세요.

1. Notion에서 분석 결과를 저장할 페이지를 엽니다 (새 페이지를 만들어도 됩니다)
2. 페이지 우측 상단의 **`...`** (점 3개) 버튼 클릭
3. **"Connect to"** 항목에서 위에서 만든 Integration 이름(예: `slack-to-notion`)을 검색하여 선택
4. **"Confirm"** 클릭

#### 3단계: Notion Parent Page ID 확인

분석 결과가 저장될 Notion 페이지의 ID를 확인합니다.

1. 2단계에서 Integration을 연결한 Notion 페이지를 **브라우저**에서 엽니다
2. 주소창의 URL을 확인합니다. 형식은 다음과 같습니다:

```
https://www.notion.so/워크스페이스/페이지제목-abc1234567890def1234567890abcdef
                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                              이 32자가 Page ID 입니다
```

3. URL 마지막의 **32자리 영숫자 문자열**을 복사합니다 (하이픈 `-` 뒤의 부분)

> URL에 `?v=...` 같은 추가 파라미터가 붙어 있다면, `?` 앞까지만 사용합니다.

#### 4단계: 환경변수 설정

발급받은 3개 토큰을 환경변수로 설정합니다. 프로젝트 폴더에 `.env` 파일을 만드는 방법을 권장합니다.

**터미널에서 다음 명령어를 실행합니다:**

```bash
# 프로젝트 폴더로 이동
cd claude-slack-to-notion

# .env.example 파일을 복사하여 .env 파일 생성
cp .env.example .env
```

**생성된 `.env` 파일을 텍스트 편집기로 열어 토큰 값을 입력합니다:**

```bash
# macOS 기본 편집기로 열기
open -e .env

# 또는 VS Code로 열기
code .env
```

**`.env` 파일 내용을 다음과 같이 수정합니다:**

```
SLACK_BOT_TOKEN=xoxb-1234-5678-abcdefgh     ← 1단계에서 복사한 값
NOTION_API_KEY=secret_abc123def456...         ← 2단계에서 복사한 값
NOTION_PARENT_PAGE_ID=abc1234567890def...     ← 3단계에서 복사한 값
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

### 제약사항

- **플랫폼**: macOS/Linux만 지원 (Windows 지원 예정)
- **API 토큰 관리**: Slack API 토큰, Notion API 키는 환경변수로 관리 (Git 추적 금지)
- **개인 메시지(DM) 제외**: 보안상 개인 DM 수집 지원하지 않음
- **API Rate Limit**: Slack/Notion API Rate Limit 고려 필요 (과도한 요청 시 제한 발생 가능)
- **Bot 권한**: Slack Bot이 조회할 채널에 미리 초대되어 있어야 함

### 문제 해결

| 증상 | 원인 | 해결 방법 |
|------|------|-----------|
| `[오류] python3이 설치되지 않았습니다.` | Python 3 미설치 | macOS: `brew install python3` |
| `SLACK_BOT_TOKEN 환경변수가 설정되지 않았습니다` | `.env` 파일 미생성 또는 토큰 미입력 | [4단계: 환경변수 설정](#4단계-환경변수-설정) 참고 |
| `not_in_channel` 에러 | Bot이 해당 채널에 초대되지 않음 | 채널에서 `/invite @봇이름` 실행 ([1단계](#1단계-slack-bot-token-발급)의 "Bot을 채널에 초대하기" 참고) |
| `invalid_auth` 에러 | 토큰이 잘못되었거나 만료됨 | [Slack API](https://api.slack.com/apps)에서 Bot Token 재확인 후 `.env` 파일 수정 |
| `Notion API 키가 올바르지 않습니다` | Notion API Key가 잘못됨 | [Notion Integrations](https://www.notion.so/my-integrations)에서 Secret 재확인 |
| `Notion 페이지를 찾을 수 없습니다` | Integration이 페이지에 연결되지 않음 | [2단계](#2단계-notion-api-key-발급)의 "Integration을 Notion 페이지에 연결하기" 참고 |
| `패키지 설치에 실패했습니다` | 네트워크 문제 또는 Python 버전 | 네트워크 확인 + Python 3.10 이상인지 확인 |

## 개발 철학

### AI-Native Development

이 프로젝트는 마크다운 명세를 먼저 작성하고, AI 에이전트가 구현하는 워크플로우를 따릅니다(spec → implement → review → commit).
AI를 단순 코드 생성기가 아닌 워크플로우 진행자로 활용하며, 개발자는 판단과 지시 역할을 담당합니다.
Claude Code 플러그인 형태로 만든 이유는 개발자의 기존 도구 체인(CLI)에 자연스럽게 통합되어 개발 속도를 높일 수 있기 때문입니다.

### 이슈 사이클 기반 개발

프로젝트는 별도 문서(Wiki, Confluence 등) 없이 GitHub Issue + PR로 히스토리를 관리합니다.
이슈 단위로 작업을 추적하며, 각 이슈마다 예상 시간을 기록하고, 실행 후 실제 소요 시간과 결과를 기록합니다.
예상과 실제의 간극을 분석하여 다음 사이클에 학습을 반영하는 방식으로 팀의 추정 능력을 개선합니다.
이슈와 PR이 축적되면 자연스럽게 블로그 포스팅이나 포트폴리오 소재로 활용할 수 있습니다.
실제로 Slack 메시지 수집(#10) → 분석 모듈(#13) → 플러그인 구조 전환(#15) → Notion 연동(#16)으로 점진적 구현된 과정을 추적할 수 있습니다.

### 비판적 사고

AI 출력을 무비판적으로 수용하지 않습니다.
과장된 주장, 미동작 케이스, 미확인 진행을 방지하기 위해 검증 루프를 거칩니다.
플래닝 강제화 → 비판적 검토 → 교차 검증 → 실행의 단계적 접근으로 품질을 보장합니다.

### 설계 원칙

- **비개발자 우선**: 자동 환경 설정(venv 자동 생성), 한글 에러 메시지 제공
- **모듈 독립성**: 최소 의존성, 단일 책임 (slack_client, analyzer, notion_client 각각 독립)
- **MCP 서버 기반 자연어 통합**: Claude Code에서 자연어로 도구를 호출하는 인터페이스

## 개발자 가이드

### 프로젝트 구조

```
claude-slack-to-notion/
├── .claude-plugin/
│   └── plugin.json                  # 플러그인 매니페스트
├── .mcp.json                        # MCP 서버 설정
├── scripts/
│   └── run-server.sh                # 자동 환경 설정 스크립트
├── src/
│   └── slack_to_notion/
│       ├── __init__.py              # 패키지 초기화
│       ├── mcp_server.py            # MCP 서버 (도구 제공)
│       ├── slack_client.py          # Slack API 연동
│       ├── analyzer.py              # AI 분석 엔진
│       ├── notion_client.py         # Notion API 연동
│       └── config.py                # 설정 관리
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
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
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

미정
