"""Pure-function tests for the Deepgram request/response handling in
app/services/consults.py. No database, no network — these can't be verified against a
live Deepgram response in this environment (no DEEPGRAM_API_KEY configured here), so
they pin down the parsing logic against Deepgram's documented, stable response shape
instead. Verify against a real recording before relying on this in production.
"""

from app.services.consults import (
    _majority_speaker,
    _parse_prerecorded_segments,
    build_deepgram_streaming_url,
    parse_deepgram_streaming_result,
)


# ── build_deepgram_streaming_url ─────────────────────────────────────────────

def test_streaming_url_includes_diarize_and_model():
    url = build_deepgram_streaming_url(sample_rate="16000", keyterms=[])
    assert "diarize=true" in url
    assert "sample_rate=16000" in url
    assert url.startswith("wss://api.deepgram.com/v1/listen?")


def test_streaming_url_includes_one_keyterm_param_per_term():
    url = build_deepgram_streaming_url(sample_rate="16000", keyterms=["metformin", "hypertension"])
    assert url.count("keyterm=") == 2
    assert "keyterm=metformin" in url
    assert "keyterm=hypertension" in url


def test_streaming_url_encodes_special_characters_in_keyterms():
    url = build_deepgram_streaming_url(sample_rate="16000", keyterms=["beta blocker"])
    assert "keyterm=beta%20blocker" in url


# ── _majority_speaker ─────────────────────────────────────────────────────────

def test_majority_speaker_maps_zero_to_doctor():
    assert _majority_speaker([{"speaker": 0}, {"speaker": 0}]) == "doctor"


def test_majority_speaker_maps_one_to_patient():
    assert _majority_speaker([{"speaker": 1}, {"speaker": 1}, {"speaker": 1}]) == "patient"


def test_majority_speaker_maps_other_ids_to_unknown():
    assert _majority_speaker([{"speaker": 2}]) == "unknown"


def test_majority_speaker_returns_unknown_for_no_words():
    assert _majority_speaker([]) == "unknown"


def test_majority_speaker_uses_majority_vote_when_words_disagree():
    words = [{"speaker": 0}, {"speaker": 1}, {"speaker": 0}]
    assert _majority_speaker(words) == "doctor"


# ── parse_deepgram_streaming_result ──────────────────────────────────────────

def test_parse_streaming_result_ignores_non_results_events():
    assert parse_deepgram_streaming_result({"type": "Metadata"}) is None


def test_parse_streaming_result_ignores_empty_transcript():
    data = {"type": "Results", "channel": {"alternatives": [{"transcript": "", "words": []}]}}
    assert parse_deepgram_streaming_result(data) is None


def test_parse_streaming_result_extracts_segment_fields():
    data = {
        "type": "Results",
        "is_final": True,
        "start": 1.5,
        "duration": 2.0,
        "channel": {
            "alternatives": [
                {
                    "transcript": "the patient reports chest pain",
                    "confidence": 0.92,
                    "words": [{"speaker": 0}, {"speaker": 0}],
                }
            ]
        },
    }
    segment = parse_deepgram_streaming_result(data)
    assert segment == {
        "speaker": "doctor",
        "start_ms": 1500,
        "end_ms": 3500,
        "text": "the patient reports chest pain",
        "confidence": 0.92,
        "is_final": False,
    }


def test_parse_streaming_result_is_final_is_always_false_regardless_of_deepgrams_own_flag():
    """is_final in this schema means "the batch pass replaced this" — a different
    concept from Deepgram's own per-utterance is_final (streaming-ASR "done refining
    this utterance", which arrives continuously throughout the recording). A live
    segment must never be stored as is_final=True, even when Deepgram's message says
    is_final: true, or it becomes indistinguishable from a genuine batch-pass result."""
    data = {
        "type": "Results",
        "is_final": True,
        "start": 0,
        "duration": 1,
        "channel": {"alternatives": [{"transcript": "hello", "confidence": 0.9, "words": []}]},
    }
    segment = parse_deepgram_streaming_result(data)
    assert segment["is_final"] is False


def test_parse_streaming_result_defaults_is_final_false_when_absent():
    data = {
        "type": "Results",
        "channel": {"alternatives": [{"transcript": "hello", "words": []}]},
    }
    segment = parse_deepgram_streaming_result(data)
    assert segment["is_final"] is False


# ── _parse_prerecorded_segments ──────────────────────────────────────────────

def test_prerecorded_segments_groups_consecutive_same_speaker_words():
    payload = {
        "results": {
            "channels": [
                {
                    "alternatives": [
                        {
                            "words": [
                                {"word": "hello", "start": 0.0, "end": 0.5, "speaker": 0, "confidence": 0.9},
                                {"word": "there", "start": 0.5, "end": 1.0, "speaker": 0, "confidence": 0.9},
                                {"word": "hi", "start": 1.0, "end": 1.3, "speaker": 1, "confidence": 0.95},
                            ]
                        }
                    ]
                }
            ]
        }
    }
    segments = _parse_prerecorded_segments(payload)
    assert len(segments) == 2
    assert segments[0]["speaker"] == "doctor"
    assert segments[0]["text"] == "hello there"
    assert segments[0]["start_ms"] == 0
    assert segments[0]["end_ms"] == 1000
    assert segments[1]["speaker"] == "patient"
    assert segments[1]["text"] == "hi"
    assert all(s["is_final"] is True for s in segments)


def test_prerecorded_segments_handles_malformed_payload_gracefully():
    assert _parse_prerecorded_segments({}) == []
    assert _parse_prerecorded_segments({"results": {}}) == []
    assert _parse_prerecorded_segments({"results": {"channels": []}}) == []


def test_prerecorded_segments_uses_punctuated_word_when_present():
    payload = {
        "results": {
            "channels": [
                {
                    "alternatives": [
                        {
                            "words": [
                                {"word": "hello", "punctuated_word": "Hello,", "start": 0.0, "end": 0.5, "speaker": 0},
                            ]
                        }
                    ]
                }
            ]
        }
    }
    segments = _parse_prerecorded_segments(payload)
    assert segments[0]["text"] == "Hello,"
