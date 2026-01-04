"""Response formatter matching example_response.json structure"""
from typing import Dict, List


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

    # Sort all segments by start time
    all_segments.sort(key=lambda x: x["start"])

    # Re-index segments
    for idx, segment in enumerate(all_segments):
        segment["id"] = idx

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
                "segments": all_segments
            }
        }
    }

    return response
