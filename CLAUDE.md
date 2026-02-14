# CLAUDE.md

AI 기반 프로젝트 협업 가이드 (범용)

## 작업 방식

**AI-Native Development (Spec-Driven Workflow)**

```
spec(Markdown) → implement(AI) → review → commit → PR → merge
```

마크다운 명세를 기반으로 AI 에이전트가 구현하며, 커밋/푸시는 사용자 검토 후에만 수행합니다.

## Git Flow

```
main ────────────────●─────
       \            /
        feature/12 ─
```

### 브랜치 전략

| 브랜치 | 용도 |
|--------|------|
| `main` | 배포 가능한 상태 |
| `feature/{번호}` | 기능 개발 |
| `fix/{번호}` | 버그 수정 |
| `docs/{번호}` | 문서 작업 |
| `refactor/{번호}` | 리팩토링 |
| `chore/{번호}` | 기타 |

> 브랜치명은 `{타입}/{이슈번호}`로 통일한다. 이슈 내용은 변경될 수 있으므로 설명을 붙이지 않는다.

### 작업 플로우

1. **이슈 생성**: `/github-issue`로 이슈 생성 + 브랜치 자동 생성
2. **작업 및 커밋**: 기능 단위로 커밋
3. **푸시**: 원격에 브랜치 푸시
4. **PR 생성**: `/github-pr`로 PR (타겟 브랜치: `main`)
5. **리뷰 및 머지**: 승인 후 머지

### 커밋 전 필수 확인

- [ ] 변경 파일 목록 확인
- [ ] 커밋 메시지 사용자 승인
- [ ] 브랜치 확인

## 워크플로우

```
Issue → Spec → Implement → Commit → PR
```

| 단계 | 스킬 | 설명 |
|------|------|------|
| 이슈 | `/github-issue` | GitHub 이슈 생성, 라벨 매핑, 브랜치 자동 생성 |
| 명세 | `/spec` | 요구사항 분석, 아키텍처 설계, 다이어그램 |
| 구현 | `/implement` | 설계 문서 기반 코드 구현 |
| 커밋 | `/commit` | diff 리뷰, 커밋 메시지 제안, 커밋 |
| PR | `/github-pr` | PR 생성, 이슈 연결 |

> 스킬 상세: [.claude/README.md](./.claude/README.md)

### 자연어 요청 시 워크플로우

수정 요청을 자연어로 받은 경우, `/cycle` 스킬로 전체 사이클을 안내한다.

| 모드 | 사용법 | 설명 |
|------|--------|------|
| 개별 실행 | `/github-issue`, `/spec` 등 | 단계별 수동 실행 |
| 전체 사이클 | `/cycle` | 이슈 탐색 → 플랜 → 구현 → 리뷰 → PR → 검증 → 완료 |

## 핵심 규칙

1. **명세 우선**: 코드 작성 전 명세 문서 먼저
2. **사용자 승인**: 커밋/푸시는 사용자 요청 시에만
3. **동기화 유지**: 문서와 코드는 항상 일치
4. **멱등성 검증**: 작업 완료 후 가이드 기준 검증

## 다이어그램

| 용도 | 도구 |
|------|------|
| 플로우, 시퀀스, 구조도 | Mermaid (README 임베딩) |
| 클래스, ERD 등 상세 | PlantUML + SVG |

PlantUML 사용 시: `example.puml` → `example.svg` 필수 생성

## 커밋 컨벤션

### 형식

```
타입: 수정내용 요약

* 상세 내용 1
* 상세 내용 2
```

### 타입

| 타입 | 용도 |
|------|------|
| init | 초기 설정 |
| feat | 새 기능 |
| fix | 버그 수정 |
| docs | 문서 |
| refactor | 리팩토링 |
| chore | 기타 |

### 예시

```
feat: Slack 메시지 파싱 모듈 추가

* 채널 메시지 조회 API 연동
* 스레드 메시지 수집 기능 구현
```

## 설정 파일

| 파일 | 범위 | Git |
|------|------|-----|
| `.claude/settings.json` | 공통 설정 | 추적 |
| `.claude/settings.local.json` | 로컬 전용 | 무시 |
| `.claude/skills/` | 워크플로우 스킬 (`/spec`, `/implement`, `/commit` 등) | 추적 |

## 프로젝트별 커스텀

프로젝트 전용 설정이 필요하면:

- `CLAUDE.md` 하단에 프로젝트 고유 규칙 추가
- `README.md`에 기술 스택, 디렉토리 구조, 실행 방법 등 작성
- `.claude/settings.local.json`에 로컬 전용 설정 추가

---

## 이 프로젝트 (claude-slack-to-notion)

Slack 메시지/스레드를 분석하여 이슈/태스크로 구조화하고, Notion 페이지로 정리하는 도구입니다.

### 개요

| 구분 | 내용 |
|------|------|
| 목적 | Slack 메시지/스레드 → AI 분석 → Notion 페이지 정리 및 협업 |
| 형태 | Claude Code 플러그인 |
| 리모트 | `https://github.com/dykim-base-project/claude-slack-to-notion.git` |

### Git Flow (이 레포)

```
main ────────────────●─────
       \            /
        feature/12 ─
```

- `develop` 브랜치 없음 (소규모 도구 레포)
- PR 타겟: `main` 직접
- 이슈 사이클 동일 적용: `/github-issue` → `/spec` → `/implement` → `/commit` → `/github-pr`

### GitHub 작업 방식

- `gh` CLI 토큰 기반 작업
- 토큰 위치: `.claude/.gh-token`
- 커밋 계정: `idean3885` / `dykimDev3885@gmail.com`

### 플러그인 관리

- claude-devex 플러그인 기반 이슈 사이클 워크플로우 사용
- 플러그인 버전은 `.claude/.devex-version`으로 관리
- 업데이트: `curl -sL https://raw.githubusercontent.com/dykim-base-project/claude-devex/main/setup.sh | bash -s -- --update`
