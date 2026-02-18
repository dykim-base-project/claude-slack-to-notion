#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# slack-to-notion-mcp 설치 스크립트
# 사용법: curl -sL URL | bash
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

GUIDE_URL="https://github.com/dykim-base-project/claude-slack-to-notion#api-토큰-설정"

print_step() {
  echo -e "\n${BLUE}▶ $1${NC}"
}

print_ok() {
  echo -e "${GREEN}✓ $1${NC}"
}

print_warn() {
  echo -e "${YELLOW}⚠ $1${NC}"
}

print_err() {
  echo -e "${RED}✗ $1${NC}"
}

# ============================================================
# 헤더
# ============================================================
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     slack-to-notion-mcp 설치 마법사              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Slack 메시지를 Notion 페이지로 정리해주는"
echo "  Claude Code 플러그인을 설치합니다."
echo ""

# ============================================================
# 전제조건 확인
# ============================================================
print_step "전제조건 확인 중..."

if ! command -v claude &> /dev/null; then
  print_err "Claude CLI가 설치되어 있지 않습니다."
  echo "    설치 방법: https://docs.anthropic.com/ko/docs/claude-code"
  exit 1
fi
print_ok "Claude CLI 확인"

if ! command -v uvx &> /dev/null; then
  print_err "uvx (uv)가 설치되어 있지 않습니다."
  echo "    설치 방법: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi
print_ok "uvx 확인"

# ============================================================
# 토큰 입력 안내
# ============================================================
echo ""
echo "  API 토큰이 필요합니다. 아직 발급받지 않으셨다면:"
echo -e "  ${BLUE}${GUIDE_URL}${NC}"
echo ""

# ============================================================
# [1/3] Slack 토큰
# ============================================================
print_step "[1/3] Slack 토큰 입력"
echo "  Bot 토큰(xoxb-...) 또는 User 토큰(xoxp-...)을 입력하세요."

while true; do
  printf "  Slack 토큰: "
  read -r slack_token < /dev/tty

  if [[ "$slack_token" == xoxb-* ]]; then
    slack_env_name="SLACK_BOT_TOKEN"
    print_ok "Bot 토큰 확인 (환경변수: SLACK_BOT_TOKEN)"
    break
  elif [[ "$slack_token" == xoxp-* ]]; then
    slack_env_name="SLACK_USER_TOKEN"
    print_ok "User 토큰 확인 (환경변수: SLACK_USER_TOKEN)"
    break
  else
    print_err "올바른 형식이 아닙니다. xoxb- 또는 xoxp- 로 시작해야 합니다."
    echo "    토큰 발급 가이드: ${GUIDE_URL}"
  fi
done

# ============================================================
# [2/3] Notion API Key
# ============================================================
print_step "[2/3] Notion API Key 입력"
echo "  Notion Integration에서 발급받은 Internal Integration Token을 입력하세요."
echo "  (secret_로 시작하는 값)"

while true; do
  printf "  Notion API Key: "
  read -r notion_api_key < /dev/tty

  if [[ "$notion_api_key" == secret_* ]]; then
    print_ok "Notion API Key 확인"
    break
  else
    print_err "올바른 형식이 아닙니다. secret_ 로 시작해야 합니다."
    echo "    토큰 발급 가이드: ${GUIDE_URL}"
  fi
done

# ============================================================
# [3/3] Notion 페이지 링크
# ============================================================
print_step "[3/3] Notion 페이지 링크 입력"
echo "  분석 결과를 저장할 Notion 페이지 URL 또는 페이지 ID를 입력하세요."

while true; do
  printf "  Notion 페이지 링크: "
  read -r notion_page < /dev/tty

  if [[ -n "$notion_page" ]]; then
    print_ok "Notion 페이지 확인"
    break
  else
    print_err "페이지 링크를 입력해주세요."
  fi
done

# ============================================================
# claude mcp add 실행
# ============================================================
print_step "플러그인 설치 중..."
echo ""

claude mcp add slack-to-notion \
  --transport stdio \
  -e "${slack_env_name}=${slack_token}" \
  -e "NOTION_API_KEY=${notion_api_key}" \
  -e "NOTION_PARENT_PAGE_ID=${notion_page}" \
  -- uvx slack-to-notion-mcp

# ============================================================
# 완료 안내
# ============================================================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     설치 완료!                                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${GREEN}slack-to-notion-mcp 플러그인이 설치되었습니다.${NC}"
echo ""
echo "  📁 설정 저장 위치:"
echo "     ~/.claude.json → mcpServers 섹션"
echo ""
echo "  🔧 토큰 수정 방법:"
echo "     1) ~/.claude.json 파일을 직접 편집"
echo "     2) 이 스크립트를 다시 실행"
echo ""
echo "  💬 사용 예시 (Claude Code에서):"
echo '     "소셜 채널의 오늘 메시지를 Notion으로 정리해줘"'
echo '     "개발 채널 스레드 분석해서 이슈로 만들어줘"'
echo ""
echo -e "  ${BLUE}자세한 사용법: ${GUIDE_URL}${NC}"
echo ""
