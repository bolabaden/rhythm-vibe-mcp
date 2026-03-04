from __future__ import annotations

from types import SimpleNamespace

from rhythm_vibe_mcp import cli, server


def test_parse_key_value_arguments_coerces_json_types() -> None:
    parsed = cli._parse_key_value_arguments(
        [
            "semitones=2",
            "enabled=true",
            "name=Theme",
            "ratio=0.5",
        ]
    )
    assert parsed["semitones"] == 2
    assert parsed["enabled"] is True
    assert parsed["name"] == "Theme"
    assert parsed["ratio"] == 0.5


def test_parse_call_arguments_merges_json_and_key_values() -> None:
    args = SimpleNamespace(
        json_args='{"output_format":"pdf","semitones":1}',
        arg=["semitones=3", "title=Song"],
    )
    parsed = cli._parse_call_arguments(args)
    assert parsed["output_format"] == "pdf"
    assert parsed["semitones"] == 3
    assert parsed["title"] == "Song"


def test_server_parameters_uses_default_server_args() -> None:
    args = SimpleNamespace(
        server_command="python",
        server_arg=[],
        server_cwd="C:/tmp",
    )
    params = cli._server_parameters(args)
    assert params.command == "python"
    assert params.args == ["-m", "rhythm_vibe_mcp.server", "--transport", "stdio"]
    assert str(params.cwd) == "C:/tmp"


def test_server_main_maps_http_alias_to_streamable_http(monkeypatch) -> None:
    calls: list[str] = []
    fake_mcp = SimpleNamespace(
        settings=SimpleNamespace(host=None, port=None),
        run=lambda transport: calls.append(transport),
    )
    monkeypatch.setattr(server, "mcp", fake_mcp)

    server.main(["--transport", "http", "--host", "0.0.0.0", "--port", "9001"])

    assert fake_mcp.settings.host == "0.0.0.0"
    assert fake_mcp.settings.port == 9001
    assert calls == ["streamable-http"]


def test_server_main_supports_sse_transport(monkeypatch) -> None:
    calls: list[str] = []
    fake_mcp = SimpleNamespace(
        settings=SimpleNamespace(host=None, port=None),
        run=lambda transport: calls.append(transport),
    )
    monkeypatch.setattr(server, "mcp", fake_mcp)

    server.main(["--transport", "sse"])

    assert calls == ["sse"]
