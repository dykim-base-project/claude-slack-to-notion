#!/bin/bash
set -e

# PLUGIN_ROOT: 스크립트 위치 기준 상위 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PLUGIN_ROOT"

# 1. python3 존재 확인
if ! command -v python3 &> /dev/null; then
    echo "[오류] python3이 설치되지 않았습니다." >&2
    echo "설치 방법:" >&2
    echo "  macOS: brew install python3" >&2
    echo "  또는: https://www.python.org/downloads/" >&2
    exit 1
fi

# 2. .venv 존재 확인 및 생성
if [ ! -d ".venv" ]; then
    echo "최초 실행: 환경을 설정하고 있습니다..." >&2
    python3 -m venv .venv

    if ! .venv/bin/pip install -e . >&2; then
        echo "[오류] 패키지 설치에 실패했습니다." >&2
        echo "네트워크 연결을 확인하거나, 관리자에게 문의하세요." >&2
        exit 1
    fi
fi

# 3. 패키지 설치 상태 검증 (venv는 있지만 패키지가 없는 경우 대비)
if ! .venv/bin/python -c "import slack_to_notion" 2>/dev/null; then
    echo "패키지를 재설치합니다..." >&2
    if ! .venv/bin/pip install -e . >&2; then
        echo "[오류] 패키지 재설치에 실패했습니다." >&2
        exit 1
    fi
fi

# 4. MCP 서버 실행 (stdout은 MCP 프로토콜 통신용)
exec .venv/bin/python -m slack_to_notion.mcp_server
