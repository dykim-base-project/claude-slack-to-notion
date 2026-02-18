# Issue #56: uvx 배포 아키텍처 전환

## 메타 정보

| 항목 | 내용 |
|------|------|
| 이슈 | [#56](https://github.com/dykim-base-project/claude-slack-to-notion/issues/56) |
| 브랜치 | `feat/56` |
| 날짜 | 2026-02-18 |
| 유형 | 아키텍처 전환 |

## 배경

### 문제 인식

#49 비개발자 E2E 테스트를 계획하면서, 현재 설치 경로가 비개발자에게 불가능하다는 것을 확인했다.

현행 방식의 문제:
- `git clone` → Python 3.10+ 설치 → venv 생성 → pip install → `.env` 설정 → `--plugin-dir` 지정
- 비개발자에게 Python 환경 설정은 진입 장벽
- `--plugin-dir`은 세션 한정이라 매번 지정해야 함
- `run-server.sh`가 venv 자동 설정을 해주지만, 그 전제가 `git clone`

### 현황 분석: 공식 마켓플레이스 플러그인 패턴

Claude Code 공식 플러그인(mcp-server-git 등)이 사용하는 3가지 패턴을 조사했다.

| 패턴 | 예시 | 특징 |
|------|------|------|
| HTTP 원격 서버 | Sentry, Linear | 서버 운영 필요, 소규모 프로젝트에 과도 |
| npx / uvx | mcp-server-git, mcp-server-fetch | 패키지 레지스트리에서 자동 다운로드·실행 |
| 번들 스크립트 | 일부 커뮤니티 플러그인 | bash/node로 직접 실행, 의존성 관리 복잡 |

npx(Node) / uvx(Python)가 "패키지 레지스트리 기반 자동 실행" 패턴으로, 공식 MCP 서버가 채택한 표준이다.

## 설계 결정

### 옵션 비교

| 옵션 | 설명 | 장점 | 단점 |
|------|------|------|------|
| **A. uvx (선택)** | PyPI 배포 + `uvx slack-to-notion-mcp` | 공식 패턴, 원커맨드 실행, uv 생태계 | PyPI 배포 필요 |
| B. pip + source | `pip install git+https://...` | PyPI 불필요 | 글로벌 pip 오염, venv 필요 |
| C. HTTP 원격 | 서버 호스팅 | 설치 없음 | 서버 운영 비용, 과도한 구조 |
| D. 현행 유지 | bash + run-server.sh | 변경 없음 | 비개발자 설치 불가능 |

### 선택 이유: uvx

1. **공식 패턴 준수**: `mcp-server-git`(Anthropic 공식)이 정확히 이 구조
2. **사용자 경험**: `uv`만 설치하면 `uvx slack-to-notion-mcp` 한 줄로 실행
3. **자동 의존성 관리**: 가상환경 생성·패키지 설치를 uvx가 자동 처리
4. **크로스 플랫폼**: macOS/Linux/Windows 모두 지원 (기존 bash 스크립트는 macOS/Linux만)

## 구현 내역

### 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `pyproject.toml` | `[project.scripts]` 진입점 추가, PyPI 메타데이터(이름, 라이선스, 작성자, URL) 보강 |
| `src/slack_to_notion/mcp_server.py` | `main()` 함수 추출 — uvx 진입점으로 사용 |
| `src/slack_to_notion/__main__.py` | **신규** — `python -m slack_to_notion` 지원 |
| `.mcp.json` | `bash` → `uvx` 커맨드 전환 |
| `README.md` | 설치 가이드를 uvx 기반으로 개편, 요구사항에서 Python → uv 전환 |
| `.github/workflows/pypi-publish.yml` | **신규** — v* 태그 시 자동 PyPI 배포 |

### 핵심 변경점

**진입점 체인:**
```
uvx slack-to-notion-mcp
  → pyproject.toml [project.scripts]
    → slack_to_notion.mcp_server:main()
      → mcp.run()
```

**패키지명 변경:** `slack-to-notion` → `slack-to-notion-mcp`
- PyPI에서 MCP 서버임을 명시
- `uvx slack-to-notion-mcp`로 실행 시 패키지명이 곧 명령어

### 변경하지 않은 것

| 항목 | 이유 |
|------|------|
| `scripts/run-server.sh` | 레거시 하위 호환. 추후 별도 이슈로 정리 |
| `plugin.json` | 구조 변경 없음 |
| `config.py` | 환경변수 검증 로직 변경 불필요 |
| 빌드 백엔드 (setuptools) | hatchling 전환은 선택사항, 이번 범위 외 |

## 결과

### 변경 전 (사용자 경험)

```bash
# 6단계 필요
git clone https://github.com/dykim-base-project/claude-slack-to-notion.git
cd claude-slack-to-notion
cp .env.example .env
# .env 편집...
cd ~/my-project
claude --plugin-dir ~/claude-slack-to-notion  # 매 세션마다
```

### 변경 후 (사용자 경험)

```bash
# 2단계로 축소
brew install uv  # 최초 1회
claude mcp add slack-to-notion -- uvx slack-to-notion-mcp  # 최초 1회
# 이후 자동 실행
```

> uvx 전환 과정의 생태계 분석과 Java 개발자 관점은 [블로그 시리즈](https://idean3885.github.io/posts/building-first-tool-with-ai/)에서 다룬다.
