from __future__ import annotations

import pytest

from backend.services.python_code_executor import (
    ExecutionRequest,
    SecureExecutionUnavailable,
    get_secure_execution_backend,
)


def test_secure_container_rejects_direct_host_capability_access():
    try:
        backend = get_secure_execution_backend()
    except SecureExecutionUnavailable as error:
        pytest.skip(f"secure-container integration unavailable: {error}")

    attacks = [
        "import os",
        "__import__('os')",
        "open('/etc/passwd')",
        "import subprocess",
        "import socket",
        "open('/proc/1/root/etc/passwd')",
        "while True: pass",
    ]
    for index, attack in enumerate(attacks):
        request = ExecutionRequest(
            source_code=f"def probe():\n    {attack}\n    return True\n",
            callable_name="probe",
            test_cases=[{"expected": False}],
            timeout_seconds=1,
        )
        result = backend.execute(request)
        assert result.status != "passed", f"container allowed attack case {index}: {attack}"
