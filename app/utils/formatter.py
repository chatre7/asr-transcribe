"""Response formatter matching example_response.json structure"""
from typing import Dict, List, Tuple
from datetime import datetime, timezone
import time
from app.config import settings


def format_transcription_response(
    filename: str,
    model_name: str,
    caller_result: Dict,
    agent_result: Dict
) -> Dict:
    """Format transcription results to match example_response.json structure

    Args:
        filename: Original filename
        model_name: Selected model name (typhoon/pathumma)
        caller_result: Transcription result for caller channel (left)
        agent_result: Transcription result for agent channel (right)

    Returns:
        Formatted response dict matching example_response.json
    """
    # Merge and sort segments from both channels
    all_segments = []

    # Add caller segments with channel label
    for segment in caller_result.get("segments", []):
        segment_copy = segment.copy()
        segment_copy["channel"] = "Caller"

        # Add channel to words
        for word in segment_copy.get("words", []):
            word["channel"] = "Caller"

        all_segments.append(segment_copy)

    # Add agent segments with channel label
    for segment in agent_result.get("segments", []):
        segment_copy = segment.copy()
        segment_copy["channel"] = "Agent"

        # Add channel to words
        for word in segment_copy.get("words", []):
            word["channel"] = "Agent"

        all_segments.append(segment_copy)

    # Optional chunking by fixed window with overlap, per channel.
    if settings.chunk_duration_sec and settings.chunk_duration_sec > 0:
        all_segments = _chunk_segments(all_segments)

    # Sort all segments by start time
    all_segments.sort(key=lambda x: x["start"])

    # Re-index segments
    for idx, segment in enumerate(all_segments):
        segment["id"] = idx

    # Build derived fields for example_response.json compatibility
    flattened_words = _flatten_words(all_segments)
    duration = _compute_duration(all_segments, flattened_words)
    language = _pick_language(caller_result, agent_result)
    transcript_text, transcript_simple_text = _build_transcript_text(all_segments)
    transcript_metadata = _build_transcript_metadata(language, duration)

    # Build response
    response = {
        "message": f"Successfully processed {filename}",
        "processing_status": "completed",
        "results": {
            "action": "unified_stereo_processed",
            "filename": filename,
            "status": "completed",
            "model_selection": {
                "chosen_model": model_name,
                "reasoning": "User selected model"
            },
            "transcription": {
                "segments": all_segments,
                "words": flattened_words,
                "language": language,
                "duration": duration
            },
            "json_structure": {
                "transcript": {
                    "text": transcript_text,
                    "simple_text": transcript_simple_text,
                    "segments": all_segments,
                    "words": flattened_words,
                    "metadata": transcript_metadata
                }
            },
            "process_json_result": {
                "status": "pending",
                "message": "Process_json integration pending"
            },
            "metadata": {
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "model_used": model_name,
                "auto_continue": True
            },
            "json_file_path": f"{filename}_unified_stereo.json"
        }
    }

    return response


def _chunk_segments(segments: List[Dict]) -> List[Dict]:
    duration = float(settings.chunk_duration_sec or 0)
    overlap = float(settings.chunk_overlap_sec or 0)
    step = duration - overlap

    if duration <= 0 or step <= 0:
        return segments

    # Flatten words per channel
    channel_words = {"Caller": [], "Agent": []}
    for segment in segments:
        channel = segment.get("channel")
        for word in segment.get("words", []):
            if channel in channel_words:
                channel_words[channel].append({
                    "word": word.get("word", ""),
                    "start": float(word.get("start", 0) or 0),
                    "end": float(word.get("end", 0) or 0),
                    "confidence": float(word.get("confidence", 0.95) or 0.95),
                })

    chunked = []
    for channel, words in channel_words.items():
        if not words:
            continue

        words.sort(key=lambda w: w["start"])
        end_time = max(w["end"] for w in words)
        seen = set()
        window_start = 0.0

        while window_start <= end_time:
            window_end = window_start + duration
            window_words = []
            for word in words:
                if word["start"] >= window_end:
                    break
                if word["end"] <= window_start:
                    continue
                key = (word["word"], round(word["start"], 3), round(word["end"], 3))
                if key in seen:
                    continue
                seen.add(key)
                window_words.append(word)

            if window_words:
                segment_text = " ".join(w["word"] for w in window_words).strip()
                chunked.append({
                    "id": 0,
                    "seek": 0,
                    "start": round(min(w["start"] for w in window_words), 3),
                    "end": round(max(w["end"] for w in window_words), 3),
                    "text": segment_text,
                    "channel": channel,
                    "words": [
                        {
                            "word": w["word"],
                            "start": round(w["start"], 3),
                            "end": round(w["end"], 3),
                            "confidence": round(w["confidence"], 2),
                            "channel": channel,
                        }
                        for w in window_words
                    ],
                })

            window_start += step

    return chunked if chunked else segments


def _flatten_words(segments: List[Dict]) -> List[Dict]:
    words = []
    for segment in segments:
        for word in segment.get("words", []):
            words.append({
                "word": word.get("word", ""),
                "start": float(word.get("start", 0) or 0),
                "end": float(word.get("end", 0) or 0),
                "confidence": float(word.get("confidence", 0.95) or 0.95),
                "channel": word.get("channel", segment.get("channel", ""))
            })
    return words


def _compute_duration(segments: List[Dict], words: List[Dict]) -> float:
    if words:
        return round(max(word["end"] for word in words), 3)
    if segments:
        return round(max(segment.get("end", 0) for segment in segments), 3)
    return 0.0


def _pick_language(caller_result: Dict, agent_result: Dict) -> str:
    for result in (caller_result, agent_result):
        language = result.get("language")
        if language:
            return language
    return "th"


def _build_transcript_text(segments: List[Dict]) -> Tuple[str, str]:
    lines = []
    simple_lines = []
    for segment in segments:
        start = float(segment.get("start", 0) or 0)
        end = float(segment.get("end", 0) or 0)
        channel = segment.get("channel", "")
        text = (segment.get("text") or "").strip()
        if not text:
            continue
        lines.append(f"[{start:.2f} --> {end:.2f}] [{channel}]: {text}")
        simple_lines.append(f"[{channel}]: {text}")
    return "\n".join(lines), "\n".join(simple_lines)


def _build_transcript_metadata(language: str, duration: float) -> Dict:
    now_ts = time.time()
    return {
        "is_stereo_merged": True,
        "language": language,
        "duration": duration,
        "processing_info": {
            "start_time": now_ts,
            "correction_passes": 0,
            "issues_detected": 0,
            "issues_fixed": 0,
            "rerun_performed": False,
            "end_time": now_ts,
            "total_duration": 0
        },
        "audio_info": {
            "channels": 2,
            "codec_name": "unknown",
            "sample_rate": settings.sample_rate,
            "duration": duration,
            "format_name": "wav",
            "size": "0"
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": "1.0"
    }
