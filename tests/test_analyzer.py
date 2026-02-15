"""분석 모듈 단위 테스트."""

import json
from pathlib import Path

import pytest

from slack_to_notion.analyzer import (
    ANALYSIS_GUIDE_EXAMPLES,
    format_messages_for_analysis,
    format_threads_for_analysis,
    get_analysis_guide,
    load_result,
    save_result,
)


class TestGetAnalysisGuide:
    """분석 안내 텍스트 테스트."""

    def test_contains_header(self):
        guide = get_analysis_guide()
        assert "어떤 방식으로 정리할까요" in guide

    def test_contains_examples(self):
        guide = get_analysis_guide()
        for example in ANALYSIS_GUIDE_EXAMPLES:
            assert example in guide

    def test_contains_tip(self):
        guide = get_analysis_guide()
        assert "팁:" in guide


class TestFormatMessagesForAnalysis:
    """메시지 포맷팅 테스트."""

    def test_basic_formatting(self):
        messages = [
            {"ts": "1739612400.000000", "user": "U001", "text": "안녕하세요"},
        ]
        result = format_messages_for_analysis(messages, "general")
        assert "Channel: general" in result
        assert "Message count: 1" in result
        assert "U001: 안녕하세요" in result

    def test_timestamp_conversion(self):
        messages = [
            {"ts": "1739612400.000000", "user": "U001", "text": "test"},
        ]
        result = format_messages_for_analysis(messages, "ch")
        # 타임스탬프가 사람이 읽을 수 있는 형식으로 변환
        assert "2025-02-15" in result or "2025-02-16" in result  # 시간대에 따라

    def test_invalid_timestamp(self):
        messages = [
            {"ts": "invalid", "user": "U001", "text": "test"},
        ]
        result = format_messages_for_analysis(messages, "ch")
        assert "invalid" in result  # 원본 타임스탬프 유지

    def test_reply_count(self):
        messages = [
            {"ts": "1739612400.000000", "user": "U001", "text": "토론", "reply_count": 5},
        ]
        result = format_messages_for_analysis(messages, "ch")
        assert "(replies: 5)" in result

    def test_no_reply_count(self):
        messages = [
            {"ts": "1739612400.000000", "user": "U001", "text": "일반"},
        ]
        result = format_messages_for_analysis(messages, "ch")
        assert "replies" not in result

    def test_empty_messages(self):
        result = format_messages_for_analysis([], "ch")
        assert "Message count: 0" in result

    def test_missing_fields(self):
        messages = [{}]
        result = format_messages_for_analysis(messages, "ch")
        assert "Unknown" in result


class TestFormatThreadsForAnalysis:
    """복수 스레드 포맷팅 테스트."""

    def test_basic_threads(self):
        threads = [
            {
                "thread_ts": "1739612400.000000",
                "messages": [
                    {"ts": "1739612400.000000", "user": "U001", "text": "스레드 주제"},
                    {"ts": "1739612401.000000", "user": "U002", "text": "답글 1"},
                ],
            },
            {
                "thread_ts": "1739612500.000000",
                "messages": [
                    {"ts": "1739612500.000000", "user": "U003", "text": "다른 스레드"},
                ],
            },
        ]
        result = format_threads_for_analysis(threads, "마케팅")
        assert "Channel: 마케팅" in result
        assert "Thread count: 2" in result
        assert "Total messages: 3" in result
        assert "Thread 1: 스레드 주제" in result
        assert "Thread 2: 다른 스레드" in result
        assert "U002: 답글 1" in result

    def test_empty_threads(self):
        result = format_threads_for_analysis([], "ch")
        assert "Thread count: 0" in result
        assert "Total messages: 0" in result

    def test_thread_with_empty_messages(self):
        threads = [{"thread_ts": "123", "messages": []}]
        result = format_threads_for_analysis(threads, "ch")
        assert "(빈 스레드)" in result

    def test_thread_message_timestamp_conversion(self):
        threads = [
            {
                "thread_ts": "1739612400.000000",
                "messages": [
                    {"ts": "1739612400.000000", "user": "U001", "text": "test"},
                ],
            },
        ]
        result = format_threads_for_analysis(threads, "ch")
        assert "2025-02-15" in result or "2025-02-16" in result


class TestSaveAndLoadResult:
    """분석 결과 저장/로드 테스트."""

    def test_save_and_load(self, tmp_path):
        data = {"summary": "테스트 요약", "tasks": []}
        filepath = tmp_path / "test_result.json"

        saved_path = save_result(data, filepath)
        assert saved_path.exists()

        loaded = load_result(filepath)
        assert loaded == data

    def test_save_creates_parent_dirs(self, tmp_path):
        data = {"key": "value"}
        filepath = tmp_path / "sub" / "dir" / "result.json"

        save_result(data, filepath)
        assert filepath.exists()

    def test_save_korean_content(self, tmp_path):
        data = {"요약": "한글 내용", "항목": ["가", "나", "다"]}
        filepath = tmp_path / "korean.json"

        save_result(data, filepath)
        loaded = load_result(filepath)
        assert loaded["요약"] == "한글 내용"

    def test_load_nonexistent_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_result(tmp_path / "nonexistent.json")
