from __future__ import annotations

import sys

import pytest

from backend.services.python_code_executor import (
    DockerContainerExecutor,
    ExecutionRequest,
    RestrictedDevelopmentExecutor,
    SecureExecutionUnavailable,
    _execute_process,
    execute_python_contract,
)


def test_development_executor_explicitly_marks_untrusted_code_unapproved():
    executor = RestrictedDevelopmentExecutor()
    request = ExecutionRequest(
        source_code="def add(a, b): return a + b",
        callable_name="add",
        test_cases=[{"args": [2, 3], "expected": 5}],
        timeout_seconds=1,
    )
    result = executor.execute(request)
    assert result.status == "NOT_APPROVED_FOR_UNTRUSTED_CODE:passed"
    syntax = executor.execute(
        ExecutionRequest("def add(a, b)\n return 5", "add", [{"args": [2, 3], "expected": 5}], 1)
    )
    runtime = executor.execute(
        ExecutionRequest(
            "def add(a, b): raise ValueError('bad')",
            "add",
            [{"args": [2, 3], "expected": 5}],
            1,
        )
    )
    timeout = executor.execute(
        ExecutionRequest(
            "def add(a, b):\n while True: pass",
            "add",
            [{"args": [2, 3], "expected": 5}],
            0.1,
        )
    )
    assert syntax.syntax_error is True
    assert runtime.runtime_error is True
    assert timeout.timed_out is True


def test_secure_mode_fails_closed_without_configured_container(monkeypatch):
    monkeypatch.delenv("AURA_SECURE_EXECUTION_IMAGE", raising=False)
    with pytest.raises(SecureExecutionUnavailable, match="not configured"):
        execute_python_contract(
            "def add(a, b): return a + b",
            {
                "callable_name": "add",
                "test_cases": [{"args": [2, 3], "expected": 5}],
                "timeout_seconds": 1,
            },
            mode="SECURE_CONTAINER",
        )


def test_docker_executor_requires_digest_pinned_image():
    with pytest.raises(ValueError, match="pinned by digest"):
        DockerContainerExecutor("python:3.13-alpine")


def test_worker_output_is_bounded():
    result = _execute_process(
        [sys.executable, "-I", "-S", "-c", "import sys; sys.stdout.write('x' * 1000000)"],
        ExecutionRequest("pass", "pass", [{"expected": True}], 2),
        env={},
        output_limit_bytes=1024,
    )
    assert result.status == "output_limit_exceeded"
    assert result.security_error is True
    assert len(result.stdout.encode("utf-8")) <= 1024
