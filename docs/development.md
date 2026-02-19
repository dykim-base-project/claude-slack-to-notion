# 개발자 가이드

## 프로젝트 구조

```
claude-slack-to-notion/
├── .claude-plugin/
│   └── plugin.json                  # 플러그인 매니페스트
├── .github/workflows/
│   ├── auto-tag.yml                 # 버전 태그 자동 생성
│   └── pypi-publish.yml             # PyPI 자동 배포
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
├── docs/                            # 상세 문서
├── pyproject.toml                   # Python 패키지 설정
├── CLAUDE.md                        # AI 협업 가이드
├── README.md
└── .gitignore
```

## 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.10+ |
| 빌드 시스템 | setuptools, wheel |
| Slack 연동 | slack_sdk >= 3.27.0 |
| Notion 연동 | notion-client >= 2.2.0 |
| MCP 서버 | mcp[cli] >= 1.0.0 |
| 개발 도구 | pytest, ruff |

## 로컬 개발 환경

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

## CI/CD

### 배포 파이프라인

`pyproject.toml`의 version을 변경하여 main에 머지하면 자동으로 PyPI까지 배포됩니다.

```
pyproject.toml version 변경 → main push
  → auto-tag.yml (v{version} 태그 생성)
    → pypi-publish.yml (PyPI 배포)
```

- **auto-tag.yml**: `pyproject.toml` 변경 감지 → 버전 태그 자동 생성
  - `AUTO_TAG_PAT` 시크릿 사용 (GITHUB_TOKEN은 다른 워크플로우를 트리거하지 않으므로 PAT 필요)
  - PAT 권한: `repo` scope, 만료 시 [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)에서 갱신
- **pypi-publish.yml**: `v*` 태그 push 감지 → 테스트 실행 → PyPI 배포
  - `PYPI_API_TOKEN` 시크릿 사용

## 기여 방법

이슈 및 PR은 [GitHub 레포지토리](https://github.com/dykim-base-project/claude-slack-to-notion)에서 관리합니다.
개발 프로세스(Git Flow, 브랜치 전략, 커밋 컨벤션)는 [CLAUDE.md](../CLAUDE.md)를 참고하세요.

## 참고 자료

- [Slack API Documentation](https://api.slack.com/docs)
- [Notion API Documentation](https://developers.notion.com/)
- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
