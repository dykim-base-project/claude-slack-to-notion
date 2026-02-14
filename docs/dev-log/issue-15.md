# Issue #15: Claude Code 플러그인 표준 구조로 전환

## 메타 정보

| 항목 | 내용 |
|------|------|
| 이슈 | [#15](https://github.com/dykim-base-project/claude-slack-to-notion/issues/15) |
| 브랜치 | `refactor/15` |
| 날짜 | 2026-02-15 |
| 유형 | 리팩토링 |

## 배경

### 문제 인식

이 프로젝트는 "Claude Code 플러그인"으로 설계되었지만, 실제로는 플러그인 표준 구조를 갖추고 있지 않았다.

- `.claude-plugin/plugin.json` (플러그인 매니페스트) 없음
- `.mcp.json` (MCP 서버 설정) 없음
- `claude plugin add`로 설치 불가능한 상태
- `src/` 에 핵심 Python 코드가 있었지만 플러그인으로 연결되지 않음

기존 설치 방식은 `claude-devex`의 setup.sh를 통한 워크플로우 스킬 설치였는데, 이는 개발자 전용 도구이지 플러그인 사용자(비개발자)를 위한 것이 아니었다.

### 전환 동기

1. 비개발자가 `claude plugin add` 한 줄로 설치하고 바로 사용할 수 있어야 함
2. Python 환경 문제는 비개발자에게 치명적 — venv로 격리 필요
3. `src/`의 Slack 수집 코드를 MCP 도구로 노출해야 Claude가 직접 호출 가능

## 설계 결정

### 1. MCP 서버 방식 선택

Python 코드를 플러그인에 연결하는 방식으로 **MCP 서버**를 선택했다.

| 대안 | 장점 | 단점 | 선택 |
|------|------|------|:----:|
| MCP 서버 | Claude가 직접 도구 호출 가능, 자연어 통합 | MCP SDK 의존성 추가 | O |
| Skills | 슬래시 커맨드로 호출 | 자연어 통합 안됨, 비개발자에게 어려움 | X |
| Hooks | 이벤트 기반 자동 실행 | 이 프로젝트와 맞지 않음 | X |

### 2. venv 자동 부트스트랩

비개발자의 Python 환경 문제를 해결하기 위해:
- MCP 서버 최초 실행 시 `scripts/run-server.sh`가 자동으로 venv 생성
- 의존성 설치도 자동
- 에러 메시지는 한글로, 해결 방법까지 안내

### 3. macOS 우선 지원

- Windows 지원은 별도 이슈로 분리
- bash 스크립트 기반 부트스트랩

### 4. devex 분리

- 플러그인 사용자에게 devex는 불필요
- README에서 devex 관련 내용 전면 제거
- devex는 `.claude/` 디렉토리에서 개발자 전용으로만 유지

## 구현 내역

### 신규 파일

| 파일 | 역할 |
|------|------|
| `.claude-plugin/plugin.json` | 플러그인 매니페스트 |
| `.mcp.json` | MCP 서버 설정 (bash 부트스트랩 호출) |
| `scripts/run-server.sh` | python3 확인, venv 생성, 의존성 설치, 서버 실행 |
| `src/slack_to_notion/mcp_server.py` | MCP 서버 진입점 (Slack 도구 4개) |

### 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `pyproject.toml` | `mcp[cli]>=1.0.0` 의존성 추가 |
| `README.md` | 플러그인 설치 가이드로 전면 재작성 |

### MCP 도구 목록

| 도구 | 기능 | 매핑 대상 |
|------|------|-----------|
| `list_channels` | 채널 목록 조회 | `SlackClient.list_channels()` |
| `fetch_messages` | 채널 메시지 조회 | `SlackClient.fetch_channel_messages()` |
| `fetch_thread` | 스레드 조회 | `SlackClient.fetch_thread_replies()` |
| `fetch_channel_info` | 채널 정보 조회 | `SlackClient.fetch_channel_info()` |

## 트러블슈팅

(구현 중 발생한 이슈가 있으면 여기에 추가)

## 결과

- `claude plugin add`로 설치 가능한 표준 플러그인 구조 완성
- 비개발자가 Python 환경 걱정 없이 사용 가능
- Slack 수집 기능이 MCP 도구로 노출되어 Claude가 직접 호출 가능
