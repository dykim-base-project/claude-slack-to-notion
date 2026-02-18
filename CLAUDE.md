# CLAUDE.md

AI 기반 프로젝트 협업 가이드 (범용)

## 작업 방식

**AI-Native Development (Spec-Driven Workflow)**

```
spec(Markdown) → implement(AI) → review → commit → PR → merge
```

마크다운 명세를 기반으로 AI 에이전트가 구현하며, 커밋/푸시는 사용자 검토 후에만 수행합니다.

## Git Flow

브랜치 전략, 작업 플로우 상세는 각 스킬 호출 시 안내됩니다.

> 브랜치명은 `{타입}/{이슈번호}`로 통일한다. 이슈 내용은 변경될 수 있으므로 설명을 붙이지 않는다.

### 커밋 전 필수 확인

- [ ] 변경 파일 목록 확인
- [ ] 커밋 메시지 사용자 승인
- [ ] 브랜치 확인

## 워크플로우

```
Issue → Spec → Implement → Commit → PR
```

스킬 상세: [.claude/README.md](./.claude/README.md)

수정 요청을 자연어로 받은 경우, `/cycle` 스킬로 전체 사이클을 안내한다.

## 핵심 규칙

1. **명세 우선**: 코드 작성 전 명세 문서 먼저
2. **사용자 승인**: 커밋/푸시는 사용자 요청 시에만
3. **동기화 유지**: 문서와 코드는 항상 일치
4. **멱등성 검증**: 작업 완료 후 가이드 기준 검증

## 검증

작업 완료 후 검증 수준을 구분하여 토큰 효율성과 정확도를 균형있게 유지한다.

| 수준 | 적용 시점 | 방법 | 비용 |
|------|-----------|------|------|
| 자가 검증 | 매번 | 체크리스트 기반 직접 확인 | 없음 |
| 비판적 검증 | 새로운 기준/규칙 수립, 아키텍처 결정 시 | 근거 유효성, 범주 오류, 실무 적용성 재검토 | 높음 |

일반 구현/문서 작업은 자가 검증만으로 충분하다. 비판적 검증은 의사결정의 근거가 중요한 경우에만 적용한다.

## 다이어그램

| 용도 | 도구 |
|------|------|
| 플로우, 시퀀스, 구조도 | Mermaid (README 임베딩) |
| 클래스, ERD 등 상세 | PlantUML + SVG |

PlantUML 사용 시: `example.puml` → `example.svg` 필수 생성

## 커밋 컨벤션

`/commit` 스킬 호출 시 컨벤션이 자동 적용됩니다.

타입: `init`, `feat`, `fix`, `docs`, `refactor`, `chore`

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
- 업데이트: `curl -sL https://raw.githubusercontent.com/idean3885/claude-devex/main/setup.sh | bash -s -- --update`

### 배치 작업 효율화 규칙

다중 이슈를 워크트리로 병렬 처리할 때 적용한다.

#### 워크트리 환경 사전 준비

에이전트 위임 **전에** 오케스트레이터가 워크트리 환경을 직접 준비한다:

```bash
cd {워크트리} && uv pip install pytest --quiet 2>&1 | tail -1
```

에이전트 프롬프트에 `pytest는 이미 설치되어 있습니다.` 를 명시하여 환경 문제 해결에 턴을 소비하지 않도록 한다.

#### 세션 상태 파일

3건 이상의 이슈를 배치 처리할 때 `.claude/session-state.md`를 작성하여 중단 시 상태를 복원한다:

```markdown
# 배치 작업 상태
- 완료: #79 (PR #82 MERGED), #80 (PR #83 MERGED)
- 진행중: #85 (커밋 완료, PR 대기)
- 대기: #86, #91
```

- 각 이슈 Phase 전환 시 상태 파일 갱신
- Stop hook 재개 시 이 파일을 먼저 읽어 상태 복원
- 배치 완료 후 상태 파일 삭제

#### 순차 머지 패턴

병렬 작업 후 PR 머지는 반드시 순차 처리한다:

```
fetch → rebase → (충돌 시 해결) → force push → merge → 다음 PR
```

- `2>&1 || true` 패턴으로 Stop hook 중단 방지
- 충돌 없는 PR은 연속 처리, 충돌 발생 시에만 수동 개입
