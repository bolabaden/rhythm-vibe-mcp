from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Protocol

if TYPE_CHECKING:
    from rhythm_vibe_mcp.models import MusicArtifact, ToolResult


class ConversionContext:
    """Mutable state carried through route-based conversion execution."""

    __slots__ = (
        "original_input_path",
        "current_path",
        "source_format",
        "target_format",
        "route",
        "collected_artifacts",
    )

    def __init__(
        self,
        original_input_path: Path,
        current_path: Path,
        source_format: str,
        target_format: str,
        route: tuple[str, ...] = (),
        collected_artifacts: list[MusicArtifact] | None = None,
    ) -> None:
        self.original_input_path = original_input_path
        self.current_path = current_path
        self.source_format = source_format
        self.target_format = target_format
        self.route = route
        self.collected_artifacts = collected_artifacts or []


class ConversionStep(Protocol):
    """Protocol for conversion steps in the conversion pipeline."""

    identifier: ClassVar[str]

    def run(self, input_path: Path, output_format: str) -> ToolResult:
        ...
