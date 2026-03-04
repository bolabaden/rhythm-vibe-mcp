from __future__ import annotations

from typing import TYPE_CHECKING

from rhythm_vibe_mcp.fallbacks import fallback_from_error, fallback_from_text

if TYPE_CHECKING:
    from rhythm_vibe_mcp.models import RobustMusicFallback
    from rhythm_vibe_mcp.server import MusicToolService


class MusicToolApplicationService:
    """Application-layer façade over server tool workflows.

    This layer is intentionally thin during scaffold phase and delegates to the
    existing runtime service implementation to preserve behavior.
    """

    def __init__(self, tool_service: MusicToolService) -> None:
        self._tool_service: MusicToolService = tool_service

    def healthcheck(self) -> str:
        return self._tool_service.healthcheck()

    def fetch_music_from_web(self, url: str) -> str:
        return self._tool_service.fetch_music_from_web(url)

    def convert_music(self, input_ref: str, output_format: str) -> str:
        return self._tool_service.convert_music(input_ref, output_format)

    def plan_music_conversion(self, input_format: str, output_format: str) -> str:
        return self._tool_service.plan_music_conversion(input_format, output_format)

    def audio_or_file_to_sheet(self, input_ref: str, prefer_output: str) -> str:
        return self._tool_service.audio_or_file_to_sheet(input_ref, prefer_output)

    def transpose_song(self, input_ref: str, semitones: int, output_format: str) -> str:
        return self._tool_service.transpose_song(input_ref, semitones, output_format)

    def normalize_reddit_music_text(self, text: str, title: str) -> str:
        return self._tool_service.normalize_reddit_music_text(text, title)

    def convert_text_notation_to_lily_or_fallback(
        self,
        text: str,
        target_format: str,
        title: str,
    ) -> str:
        return self._tool_service.convert_text_notation_to_lily_or_fallback(
            text,
            target_format,
            title,
        )

    def compose_story_lily(
        self,
        prompt: str,
        title: str,
        tempo_bpm: int,
        instrument: str,
        clef: str | None,
        midi_instrument: str | None,
        output_format: str,
    ) -> str:
        return self._tool_service.compose_story_lily(
            prompt,
            title,
            tempo_bpm,
            instrument,
            clef,
            midi_instrument,
            output_format,
        )

    def set_musescore_auth_token(self, token: str) -> str:
        return self._tool_service.set_musescore_auth_token(token)

    def musescore_api(
        self,
        endpoint: str,
        method: str,
        payload_json: str,
        base_url: str,
    ) -> str:
        return self._tool_service.musescore_api(
            endpoint,
            method,
            payload_json,
            base_url,
        )

    def batch_convert_audio_formats(self, input_ref: str) -> str:
        return self._tool_service.batch_convert_audio_formats(input_ref)

class ConversionPipelineService:
    """Scaffold for conversion orchestration extraction.

    This remains intentionally narrow in prompt 4; behavior will be migrated in
    later prompts.
    """

    def __init__(self, app_service: MusicToolApplicationService) -> None:
        self._app_service: MusicToolApplicationService = app_service

    def convert_music(self, input_ref: str, output_format: str) -> str:
        return self._app_service.convert_music(input_ref, output_format)

    def transpose_song(self, input_ref: str, semitones: int, output_format: str) -> str:
        return self._app_service.transpose_song(input_ref, semitones, output_format)


class FallbackService:
    """Scaffold for fallback orchestration extraction."""

    def from_text(self, text: str, title: str | None = None) -> RobustMusicFallback:
        return fallback_from_text(text, title=title)

    def from_error(
        self,
        *,
        title: str,
        warning: str,
        shorthand_text: str = "",
    ) -> RobustMusicFallback:
        return fallback_from_error(
            title=title,
            warning=warning,
            shorthand_text=shorthand_text,
        )
