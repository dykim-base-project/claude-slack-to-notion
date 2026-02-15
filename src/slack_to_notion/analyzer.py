"""메시지 분석 및 구조화 모듈.

수집된 메시지를 AI 분석용으로 포맷팅하고, 분석 결과를 로컬에 백업한다.
분석 기준과 정리 방식은 플러그인 사용자가 자유롭게 지정한다.
"""

import json
from pathlib import Path
from datetime import datetime


# 사용자에게 분석 방향을 안내할 때 제시하는 예시
ANALYSIS_GUIDE_EXAMPLES = [
    "회의 결정사항 위주로 정리해줘",
    "액션 아이템만 뽑아서 담당자별로 정리해줘",
    "주제별로 분류하고 각 주제의 핵심 내용을 요약해줘",
    "버그 리포트와 기능 요청을 분리해서 정리해줘",
    "타임라인 순서로 논의 흐름을 정리해줘",
]


def get_analysis_guide() -> str:
    """사용자에게 보여줄 분석 방향 안내 텍스트."""
    lines = [
        "이 스레드를 어떤 방식으로 정리할까요?",
        "자유롭게 입력하시면 그 방향에 맞춰 정리합니다.",
        "",
        "입력 예시:",
    ]
    for example in ANALYSIS_GUIDE_EXAMPLES:
        lines.append(f"  - {example}")
    lines.append("")
    lines.append("팁: 구체적일수록 원하는 결과에 가까워집니다.")
    lines.append('  예) "지난주 논의 중 미해결 건만 추려서 우선순위 매겨줘"')
    return "\n".join(lines)


def format_messages_for_analysis(messages: list[dict], channel_name: str) -> str:
    """Slack 메시지 리스트를 AI 분석용 텍스트로 변환."""
    context_lines = [
        f"Channel: {channel_name}",
        f"Message count: {len(messages)}",
        "",
        "Messages:",
        "",
    ]

    message_lines = []
    for msg in messages:
        ts = msg.get("ts", "")
        user = msg.get("user", "Unknown")
        text = msg.get("text", "")
        reply_count = msg.get("reply_count", 0)

        try:
            dt = datetime.fromtimestamp(float(ts))
            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            timestamp_str = ts

        msg_line = f"[{timestamp_str}] {user}: {text}"
        if reply_count > 0:
            msg_line += f" (replies: {reply_count})"

        message_lines.append(msg_line)

    return "\n".join(context_lines + message_lines)


def format_threads_for_analysis(
    threads: list[dict],
    channel_name: str,
) -> str:
    """복수 스레드 메시지를 AI 분석용 텍스트로 변환.

    Args:
        threads: 스레드 목록. 각 항목은 {"thread_ts": str, "messages": list[dict]}
        channel_name: 채널 이름

    Returns:
        AI 분석용 포맷 텍스트
    """
    total_messages = sum(len(t["messages"]) for t in threads)
    context_lines = [
        f"Channel: {channel_name}",
        f"Thread count: {len(threads)}",
        f"Total messages: {total_messages}",
        "",
    ]

    for i, thread in enumerate(threads, 1):
        messages = thread["messages"]
        # 첫 메시지를 스레드 주제로 사용
        topic = messages[0].get("text", "(내용 없음)") if messages else "(빈 스레드)"
        context_lines.append(f"--- Thread {i}: {topic} ---")
        context_lines.append("")

        for msg in messages:
            ts = msg.get("ts", "")
            user = msg.get("user", "Unknown")
            text = msg.get("text", "")

            try:
                dt = datetime.fromtimestamp(float(ts))
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                timestamp_str = ts

            context_lines.append(f"[{timestamp_str}] {user}: {text}")

        context_lines.append("")

    return "\n".join(context_lines)


def save_result(data: dict, path: Path) -> Path:
    """분석 결과를 JSON 파일로 로컬 저장 (백업/캐시)."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return path


def load_result(path: Path) -> dict:
    """로컬 JSON 파일에서 분석 결과 로드."""
    if not path.exists():
        raise FileNotFoundError(f"분석 결과 파일을 찾을 수 없습니다: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
