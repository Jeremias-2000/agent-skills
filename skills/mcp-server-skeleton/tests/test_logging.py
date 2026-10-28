import json
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.mcp.infra.logging import LOGGING_CONF, load_logging_config
from app.mcp.infra.logging.json_formatter import JsonFormatter


def test_load_logging_config_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_logging_config(tmp_path / "missing.conf")


def test_load_logging_config_emits_json_on_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    load_logging_config()
    logger = logging.getLogger("tests.test_logging")
    logger.info("hello %s", "world")

    captured = capsys.readouterr()
    assert captured.out == ""
    lines = [line for line in captured.err.splitlines() if line.strip()]
    assert lines, "expected at least one log line on stderr"

    record = json.loads(lines[-1])
    assert record["level"] == "INFO"
    assert record["name"] == "tests.test_logging"
    assert record["message"] == "hello world"
    assert record["function"] == "test_load_logging_config_emits_json_on_stderr"
    assert record["line"] > 0
    assert record["file"] == "test_logging.py"
    assert "time" in record
    assert "exception" not in record


def test_json_formatter_includes_exception() -> None:
    formatter = JsonFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.getLogger("tests.test_logging").makeRecord(
            name="tests.test_logging",
            level=logging.ERROR,
            fn=__file__,
            lno=0,
            msg="failed",
            args=(),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(formatter.format(record))
    assert payload["level"] == "ERROR"
    assert "ValueError: boom" in payload["exception"]


def test_json_formatter_includes_request_id_when_present() -> None:
    formatter = JsonFormatter()
    record = logging.getLogger("tests.test_logging").makeRecord(
        name="tests.test_logging",
        level=logging.INFO,
        fn=__file__,
        lno=0,
        msg="with request",
        args=(),
        exc_info=None,
        extra={"request_id": "42"},
    )

    payload = json.loads(formatter.format(record))
    assert payload["request_id"] == "42"


def test_logging_conf_exists() -> None:
    assert LOGGING_CONF.is_file()
