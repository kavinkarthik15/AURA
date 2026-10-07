from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
import threading
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict

_EXECUTION_RUNNER = r"""
import json
import sys

request = json.loads(sys.stdin.read())
namespace = {
    "__builtins__": {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "float": float,
        "int": int,
        "len": len,
        "list": list,
        "max": max,
        "min": min,
        "range": range,
        "reversed": reversed,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "zip": zip,
    }
}
try:
    code = compile(request["source"], "<participant-submission>", "exec")
except SyntaxError as error:
    sys.stdout.write(json.dumps({"status": "syntax_error", "tests_passed": 0, "tests_failed": 0}))
    raise SystemExit(0)
try:
    exec(code, namespace, namespace)
except BaseException:
    sys.stdout.write(json.dumps({"status": "runtime_error", "tests_passed": 0, "tests_failed": 0}))
    raise SystemExit(0)
target = namespace.get(request["callable_name"])
if not callable(target):
    sys.stdout.write(json.dumps({"status": "runtime_error", "tests_passed": 0, "tests_failed": 0}))
    raise SystemExit(0)
passed_count = 0
for case in request["test_cases"]:
    try:
        actual = target(*case.get("args", []), **case.get("kwargs", {}))
    except BaseException:
        sys.stdout.write(json.dumps({"status": "runtime_error", "tests_passed": passed_count, "tests_failed": 1}))
        raise SystemExit(0)
    if actual != case.get("expected"):
        sys.stdout.write(json.dumps({"status": "test_failed", "tests_passed": passed_count, "tests_failed": 1}))
        raise SystemExit(0)
    passed_count += 1
sys.stdout.write(json.dumps({"status": "passed", "tests_passed": passed_count, "tests_failed": 0}))
"""


class SecureExecutionUnavailable(RuntimeError):
    pass


class CodeExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: str
    tests_passed: int = 0
    tests_failed: int = 0
    timed_out: bool = False
    syntax_error: bool = False
    runtime_error: bool = False
    security_error: bool = False
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class ExecutionRequest:
    source_code: str
    callable_name: str
    test_cases: list[dict[str, Any]]
    timeout_seconds: float


class CodeExecutionBackend:
    def execute(self, request: ExecutionRequest) -> CodeExecutionResult:
        raise NotImplementedError

    def health_check(self) -> bool:
        raise NotImplementedError


def _validate_request(request: ExecutionRequest) -> bool:
    return (
        isinstance(request.source_code, str)
        and isinstance(request.callable_name, str)
        and bool(request.callable_name)
        and isinstance(request.test_cases, list)
        and bool(request.test_cases)
        and isinstance(request.timeout_seconds, (int, float))
        and not isinstance(request.timeout_seconds, bool)
        and request.timeout_seconds > 0
    )


def _payload(request: ExecutionRequest) -> str:
    return json.dumps(
        {
            "source": request.source_code,
            "callable_name": request.callable_name,
            "test_cases": request.test_cases,
        }
    )


def _execute_process(
    command: list[str],
    request: ExecutionRequest,
    *,
    env: dict[str, str] | None,
    output_limit_bytes: int = 16_384,
    timeout_cap_seconds: float = 5.0,
) -> CodeExecutionResult:
    if not _validate_request(request):
        return CodeExecutionResult(status="invalid_request")
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    outputs: dict[str, bytearray] = {"stdout": bytearray(), "stderr": bytearray()}
    output_exceeded = threading.Event()

    def drain(name: str, stream: Any) -> None:
        while True:
            chunk = stream.read(1024)
            if not chunk:
                break
            encoded = chunk.encode("utf-8", errors="replace")
            available = output_limit_bytes - len(outputs[name])
            if available > 0:
                outputs[name].extend(encoded[:available])
            if len(encoded) > available:
                output_exceeded.set()
                try:
                    process.kill()
                except OSError:
                    pass
                break

    readers = [
        threading.Thread(target=drain, args=("stdout", process.stdout), daemon=True),
        threading.Thread(target=drain, args=("stderr", process.stderr), daemon=True),
    ]
    for reader in readers:
        reader.start()
    try:
        assert process.stdin is not None
        process.stdin.write(_payload(request))
        process.stdin.close()
        process.wait(timeout=min(float(request.timeout_seconds), timeout_cap_seconds))
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        return CodeExecutionResult(status="timeout", timed_out=True)
    except OSError as error:
        process.kill()
        process.wait()
        return CodeExecutionResult(status="backend_error", stderr=str(error)[:output_limit_bytes])
    finally:
        for reader in readers:
            reader.join(timeout=1)

    stdout = outputs["stdout"].decode("utf-8", errors="replace")
    stderr = outputs["stderr"].decode("utf-8", errors="replace")
    if output_exceeded.is_set():
        return CodeExecutionResult(
            status="output_limit_exceeded",
            security_error=True,
            stdout=stdout,
            stderr=stderr,
        )
    if process.returncode != 0:
        return CodeExecutionResult(status="execution_failed", runtime_error=True, stdout=stdout, stderr=stderr)
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return CodeExecutionResult(status="invalid_worker_response", security_error=True, stdout=stdout, stderr=stderr)
    status = payload.get("status")
    return CodeExecutionResult(
        status=status if status in {"passed", "test_failed", "syntax_error", "runtime_error"} else "invalid_worker_response",
        tests_passed=int(payload.get("tests_passed", 0)),
        tests_failed=int(payload.get("tests_failed", 0)),
        syntax_error=status == "syntax_error",
        runtime_error=status == "runtime_error",
        stdout=stdout,
        stderr=stderr,
    )


class RestrictedDevelopmentExecutor(CodeExecutionBackend):
    """Development/test-only executor. It is not approved for untrusted submissions."""

    def execute(self, request: ExecutionRequest) -> CodeExecutionResult:
        result = _execute_process(
            [sys.executable, "-I", "-S", "-c", _EXECUTION_RUNNER],
            request,
            env={},
        )
        return result.model_copy(update={"status": f"NOT_APPROVED_FOR_UNTRUSTED_CODE:{result.status}"})

    def health_check(self) -> bool:
        return True


class DockerContainerExecutor(CodeExecutionBackend):
    """Docker execution with strict container settings; requires a digest-pinned worker image."""

    def __init__(self, image: str, *, docker_executable: str = "docker") -> None:
        if not re.fullmatch(r".+@sha256:[0-9a-f]{64}", image):
            raise ValueError("secure worker image must be pinned by digest")
        self.image = image
        self.docker_executable = docker_executable

    def _command(self, container_name: str, worker_args: list[str]) -> list[str]:
        return [
            self.docker_executable,
            "run",
            "--rm",
            "--interactive",
            "--name",
            container_name,
            "--network",
            "none",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=16m",
            "--user",
            "65534:65534",
            "--memory",
            "128m",
            "--cpus",
            "0.5",
            "--pids-limit",
            "32",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--security-opt",
            "seccomp=default",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            self.image,
            *worker_args,
        ]

    def execute(self, request: ExecutionRequest) -> CodeExecutionResult:
        if not _validate_request(request):
            return CodeExecutionResult(status="invalid_request")
        container_name = f"aura-assessment-{secrets.token_hex(8)}"
        result = _execute_process(
            self._command(container_name, ["python", "-I", "-S", "-c", _EXECUTION_RUNNER]),
            request,
            env={},
        )
        if result.timed_out or result.security_error:
            try:
                subprocess.run(
                    [self.docker_executable, "kill", container_name],
                    capture_output=True,
                    timeout=2,
                    env={},
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
        return result

    def health_check(self) -> bool:
        container_name = f"aura-health-{secrets.token_hex(8)}"
        try:
            result = subprocess.run(
                self._command(
                    container_name,
                    ["python", "-I", "-S", "-c", "print('AURA_SECURE_WORKER_READY')"],
                ),
                input="",
                capture_output=True,
                text=True,
                timeout=15,
                env={},
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0 and "AURA_SECURE_WORKER_READY" in result.stdout


def get_secure_execution_backend() -> DockerContainerExecutor:
    image = os.environ.get("AURA_SECURE_EXECUTION_IMAGE")
    if not image:
        raise SecureExecutionUnavailable(
            "secure code execution is unavailable: AURA_SECURE_EXECUTION_IMAGE is not configured"
        )
    backend = DockerContainerExecutor(image)
    if not backend.health_check():
        raise SecureExecutionUnavailable("secure code execution backend health check failed")
    return backend


def execute_python_contract(
    submitted: str,
    contract: dict[str, Any],
    *,
    mode: str = "DEVELOPMENT_RESTRICTED",
    backend: CodeExecutionBackend | None = None,
) -> bool:
    callable_name = contract.get("callable_name")
    cases = contract.get("test_cases")
    timeout_seconds = contract.get("timeout_seconds", 1.0)
    request = ExecutionRequest(submitted, callable_name, cases, timeout_seconds)
    if not _validate_request(request):
        return False
    if mode == "SECURE_CONTAINER":
        backend = backend or get_secure_execution_backend()
    elif mode == "DEVELOPMENT_RESTRICTED":
        backend = backend or RestrictedDevelopmentExecutor()
    else:
        raise ValueError(f"unsupported code execution mode: {mode}")
    result = backend.execute(request)
    if mode == "DEVELOPMENT_RESTRICTED" and not result.status.startswith("NOT_APPROVED_FOR_UNTRUSTED_CODE"):
        raise RuntimeError("development executor result is missing its untrusted-code warning")
    return result.status.endswith(":passed") if mode == "DEVELOPMENT_RESTRICTED" else result.status == "passed"
