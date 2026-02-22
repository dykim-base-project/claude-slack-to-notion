#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# slack-to-notion-mcp 설치/업데이트 스크립트
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

# Python 버전 확인 (3.10 미만이면 경고)
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
  PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
  PYTHON_CMD="python"
fi

PYTHON_TOO_OLD=false
if [[ -n "$PYTHON_CMD" ]]; then
  PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
  PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
  PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
  if [[ "$PYTHON_MAJOR" -lt 3 ]] || { [[ "$PYTHON_MAJOR" -eq 3 ]] && [[ "$PYTHON_MINOR" -lt 10 ]]; }; then
    PYTHON_TOO_OLD=true
    print_warn "시스템 Python ${PYTHON_VERSION}이 감지되었습니다. (필요 버전: 3.10 이상)"
    echo "    uvx가 자동으로 Python 3.10을 사용하도록 설정합니다."
  else
    print_ok "Python ${PYTHON_VERSION} 확인"
  fi
else
  print_warn "Python이 설치되어 있지 않습니다. uvx가 자동으로 Python 3.10을 사용합니다."
  PYTHON_TOO_OLD=true
fi

# ============================================================
# 기존 설치 감지
# ============================================================
IS_UPDATE=false
if claude mcp list 2>/dev/null | grep -q "slack-to-notion"; then
  IS_UPDATE=true
fi

# ============================================================
# 업데이트 모드
# ============================================================
if [[ "$IS_UPDATE" == "true" ]]; then
  echo ""
  echo -e "${YELLOW}╔══════════════════════════════════════════════════╗${NC}"
  echo -e "${YELLOW}║     기존 설치가 감지되었습니다                   ║${NC}"
  echo -e "${YELLOW}╚══════════════════════════════════════════════════╝${NC}"
  echo ""
  echo "  이미 설치된 플러그인이 감지되었습니다. 업데이트를 진행합니다."
  echo ""

  # 기존 설정에서 토큰 읽기 시도
  existing_slack_token=""
  existing_slack_env_name=""
  existing_notion_api_key=""
  existing_notion_page=""

  # Claude Code CLI 설정 파일에서 토큰 추출
  # .claude.json: projects > {경로} > mcpServers > slack-to-notion > env
  if [[ -f "$HOME/.claude.json" ]]; then
    token_data=$(python3 -c "
import json, sys
try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    # Claude Code CLI: projects > {path} > mcpServers 탐색
    for proj in data.get('projects', {}).values():
        servers = proj.get('mcpServers', {})
        if isinstance(servers, dict) and 'slack-to-notion' in servers:
            env = servers['slack-to-notion'].get('env', {})
            slack = env.get('SLACK_BOT_TOKEN', env.get('SLACK_USER_TOKEN', ''))
            notion = env.get('NOTION_API_KEY', '')
            page = env.get('NOTION_PARENT_PAGE_ID', '')
            print(f'{slack}\n{notion}\n{page}')
            sys.exit(0)
    print('\n\n')
except:
    print('\n\n')
" "$HOME/.claude.json" 2>/dev/null || echo -e "\n\n")

    existing_slack_token=$(echo "$token_data" | sed -n '1p')
    existing_notion_api_key=$(echo "$token_data" | sed -n '2p')
    existing_notion_page=$(echo "$token_data" | sed -n '3p')

    if [[ -n "$existing_slack_token" ]]; then
      if [[ "$existing_slack_token" == xoxb-* ]]; then
        existing_slack_env_name="SLACK_BOT_TOKEN"
      else
        existing_slack_env_name="SLACK_USER_TOKEN"
      fi
    fi
  fi

  # 폴백: Claude Desktop / .mcp.json 설정 파일 탐색
  if [[ -z "$existing_slack_token" ]]; then
    MCP_JSON_PATHS=(
      "$HOME/.claude/claude_desktop_config.json"
      "$HOME/.config/claude/claude_desktop_config.json"
      "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
      ".mcp.json"
    )

    for mcp_path in "${MCP_JSON_PATHS[@]}"; do
      if [[ -f "$mcp_path" ]]; then
        token_data=$(python3 -c "
import json, sys
try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    servers = data.get('mcpServers', data.get('mcp', {}).get('servers', {}))
    server = servers.get('slack-to-notion', {})
    env = server.get('env', {})
    slack = env.get('SLACK_BOT_TOKEN', env.get('SLACK_USER_TOKEN', ''))
    notion = env.get('NOTION_API_KEY', '')
    page = env.get('NOTION_PARENT_PAGE_ID', '')
    print(f'{slack}\n{notion}\n{page}')
except:
    print('\n\n')
" "$mcp_path" 2>/dev/null || echo -e "\n\n")

        existing_slack_token=$(echo "$token_data" | sed -n '1p')
        existing_notion_api_key=$(echo "$token_data" | sed -n '2p')
        existing_notion_page=$(echo "$token_data" | sed -n '3p')

        if [[ -n "$existing_slack_token" ]]; then
          if [[ "$existing_slack_token" == xoxb-* ]]; then
            existing_slack_env_name="SLACK_BOT_TOKEN"
          else
            existing_slack_env_name="SLACK_USER_TOKEN"
          fi
          break
        fi
      fi
    done
  fi

  print_step "기존 플러그인 제거 중..."
  if claude mcp remove slack-to-notion 2>/dev/null; then
    print_ok "기존 플러그인 제거 완료"
  else
    print_warn "기존 플러그인 제거 건너뜀 (이미 제거되었거나 접근 불가)"
  fi

  print_step "기존 환경 정리 중..."
  # 영구 설치(uv tool install)가 있으면 제거 — uvx 버전 갱신을 차단하는 원인
  if uv tool list 2>/dev/null | grep -q "slack-to-notion-mcp"; then
    uv tool uninstall slack-to-notion-mcp 2>/dev/null || true
    print_ok "기존 영구 설치 제거 완료"
  fi
  uv cache clean slack-to-notion-mcp --force 2>/dev/null || true
  print_ok "캐시 정리 완료"
fi

# ============================================================
# 토큰 입력 안내
# ============================================================
if [[ "$IS_UPDATE" == "false" ]]; then
  echo ""
  echo "  API 토큰이 필요합니다. 아직 발급받지 않으셨다면:"
  echo -e "  ${BLUE}${GUIDE_URL}${NC}"
  echo ""
fi

# ============================================================
# [1/3] Slack 토큰
# ============================================================
print_step "[1/3] Slack 토큰 입력"

if [[ "$IS_UPDATE" == "true" && -n "$existing_slack_token" ]]; then
  # 기존 토큰 재사용
  slack_token="$existing_slack_token"
  slack_env_name="$existing_slack_env_name"
  masked="${slack_token:0:10}...${slack_token: -4}"
  print_ok "기존 토큰 재사용 (${masked}) — 변경하려면 나중에 스크립트를 다시 실행하세요."
elif [[ "$IS_UPDATE" == "true" ]]; then
  print_warn "기존 Slack 토큰을 자동으로 찾지 못했습니다. 토큰을 다시 입력해주세요."
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
else
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
fi

# ============================================================
# [2/3] Notion API Key
# ============================================================
print_step "[2/3] Notion API Key 입력"

if [[ "$IS_UPDATE" == "true" && -n "$existing_notion_api_key" ]]; then
  notion_api_key="$existing_notion_api_key"
  masked="${notion_api_key:0:10}...${notion_api_key: -4}"
  print_ok "기존 API Key 재사용 (${masked}) — 변경하려면 나중에 스크립트를 다시 실행하세요."
elif [[ "$IS_UPDATE" == "true" ]]; then
  print_warn "기존 Notion API Key를 자동으로 찾지 못했습니다. 다시 입력해주세요."
  echo "  Notion Integration에서 발급받은 Internal Integration Token을 입력하세요."
  echo "  (ntn_ 또는 secret_로 시작하는 값)"

  while true; do
    printf "  Notion API Key: "
    read -r notion_api_key < /dev/tty

    if [[ "$notion_api_key" == ntn_* ]] || [[ "$notion_api_key" == secret_* ]]; then
      print_ok "Notion API Key 확인"
      break
    else
      print_err "올바른 형식이 아닙니다. ntn_ 또는 secret_ 로 시작해야 합니다."
      echo "    토큰 발급 가이드: ${GUIDE_URL}"
    fi
  done
else
  echo "  Notion Integration에서 발급받은 Internal Integration Token을 입력하세요."
  echo "  (ntn_ 또는 secret_로 시작하는 값)"

  while true; do
    printf "  Notion API Key: "
    read -r notion_api_key < /dev/tty

    if [[ "$notion_api_key" == ntn_* ]] || [[ "$notion_api_key" == secret_* ]]; then
      print_ok "Notion API Key 확인"
      break
    else
      print_err "올바른 형식이 아닙니다. ntn_ 또는 secret_ 로 시작해야 합니다."
      echo "    토큰 발급 가이드: ${GUIDE_URL}"
    fi
  done
fi

# ============================================================
# [3/3] Notion 페이지 링크
# ============================================================
print_step "[3/3] Notion 페이지 링크 입력"

if [[ "$IS_UPDATE" == "true" && -n "$existing_notion_page" ]]; then
  notion_page="$existing_notion_page"
  print_ok "기존 페이지 링크 재사용 — 변경하려면 나중에 스크립트를 다시 실행하세요."
elif [[ "$IS_UPDATE" == "true" ]]; then
  print_warn "기존 Notion 페이지 링크를 자동으로 찾지 못했습니다. 다시 입력해주세요."
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
else
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
fi

# ============================================================
# claude mcp add 실행
# ============================================================
if [[ "$IS_UPDATE" == "true" ]]; then
  print_step "플러그인 재설치 중..."
else
  print_step "플러그인 설치 중..."
fi
echo ""

if [[ "$PYTHON_TOO_OLD" == "true" ]]; then
  claude mcp add slack-to-notion \
    --transport stdio \
    -e "${slack_env_name}=${slack_token}" \
    -e "NOTION_API_KEY=${notion_api_key}" \
    -e "NOTION_PARENT_PAGE_ID=${notion_page}" \
    -- uvx --python 3.10 slack-to-notion-mcp
else
  claude mcp add slack-to-notion \
    --transport stdio \
    -e "${slack_env_name}=${slack_token}" \
    -e "NOTION_API_KEY=${notion_api_key}" \
    -e "NOTION_PARENT_PAGE_ID=${notion_page}" \
    -- uvx slack-to-notion-mcp
fi

# ============================================================
# 완료 안내
# ============================================================
echo ""
if [[ "$IS_UPDATE" == "true" ]]; then
  echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║     업데이트 완료!                                ║${NC}"
  echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "  ${GREEN}업데이트가 완료되었습니다.${NC}"
else
  echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║     설치 완료!                                    ║${NC}"
  echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "  ${GREEN}slack-to-notion-mcp 플러그인이 설치되었습니다.${NC}"
fi
echo ""
echo -e "  ${YELLOW}[참고] 처음 실행 시 플러그인이 인식되지 않으면${NC}"
echo -e "  ${YELLOW}       Claude Code를 종료(/exit) 후 다시 시작해주세요.${NC}"
echo ""
echo "  설치 확인:"
echo "     claude mcp list"
echo ""
echo "  토큰 수정:"
echo "     이 스크립트를 다시 실행하세요."
echo ""
echo "  삭제:"
echo "     claude mcp remove slack-to-notion"
echo ""
echo "  사용 예시 (Claude Code에서):"
echo '     "소셜 채널의 오늘 메시지를 Notion으로 정리해줘"'
echo '     "개발 채널 스레드 분석해서 이슈로 만들어줘"'
echo ""
echo -e "  ${BLUE}자세한 사용법: ${GUIDE_URL}${NC}"
echo ""
