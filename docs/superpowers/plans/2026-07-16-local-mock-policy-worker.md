# Local Mock Policy Worker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first independently runnable subsystem: a local HTTP policy worker that loads one deterministic backend at startup, validates SO-101 observations, and returns typed action chunks.

**Architecture:** The worker owns policy loading and inference but never owns a robot, camera, serial port, action queue, or task lifecycle. Milestone 1 begins with a deterministic CPU-only backend so the HTTP contract and model lifecycle can be tested before the simulator and edge agent are added in their own plans.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, Pydantic 2, HTTPX, pytest, Ruff, MyPy, Hatchling.

## Global Constraints

- Use test-driven development: run every new test before and after its implementation.
- End every task with one behavior-focused commit and all existing tests passing.
- Use a `src` package layout and strict Pydantic request validation.
- Load the backend exactly once during FastAPI lifespan startup.
- Keep the worker deterministic and CPU-only in this plan.
- Do not add PyTorch, LeRobot, camera, serial-port, robot, ROS 2, C++, Rust, CUDA, or cloud dependencies.
- Do not commit virtual environments, caches, build output, model weights, or generated results.
- Before every commit run `python -m pytest -q`, `python -m ruff check .`, `python -m mypy src`, and `git diff --check`.

---

## File Map

```text
so101-policy-platform/
|-- pyproject.toml                         # package metadata, dependencies, tools, commands
|-- src/so101_policy_platform/
|   |-- __init__.py                        # package version
|   |-- contracts.py                       # JSON request and response schema
|   |-- policy_backend.py                  # inference backend boundary
|   |-- mock_policy.py                     # deterministic teaching backend
|   `-- policy_worker.py                   # FastAPI lifecycle and HTTP routes
|-- tests/
|   |-- unit/
|   |   |-- test_package.py
|   |   |-- test_contracts.py
|   |   `-- test_mock_policy.py
|   `-- integration/
|       `-- test_policy_worker.py
`-- docs/milestones/
    `-- 01-local-mock-policy-worker.md     # process map and runnable request
```

## Task 1: Bootstrap the Installable Python Package

**Files:**

- Create: `pyproject.toml`
- Create: `src/so101_policy_platform/__init__.py`
- Create: `tests/unit/test_package.py`
- Modify: `.gitignore`
- Modify: `README.md`

**Interfaces:**

- Consumes: Python 3.12 from the developer environment.
- Produces: importable package `so101_policy_platform` with `__version__: str` and three console-script entry points used by later plans.

- [ ] **Step 1: Write the failing package test**

Create `tests/unit/test_package.py`:

```python
import so101_policy_platform


def test_package_exposes_version() -> None:
    assert so101_policy_platform.__version__ == "0.1.0"
```

- [ ] **Step 2: Run the test and verify the package is absent**

Run:

```bash
python -m pytest -q tests/unit/test_package.py
```

Expected: test collection fails with `ModuleNotFoundError: No module named 'so101_policy_platform'`.

- [ ] **Step 3: Add complete package metadata**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.27,<2"]
build-backend = "hatchling.build"

[project]
name = "so101-policy-platform"
version = "0.1.0"
description = "A learning-first policy serving platform for the SO-101 robot arm"
readme = "README.md"
requires-python = ">=3.12,<3.13"
dependencies = [
  "fastapi>=0.115,<1",
  "httpx>=0.27,<1",
  "pydantic>=2.9,<3",
  "uvicorn>=0.30,<1",
]

[project.optional-dependencies]
dev = [
  "build>=1.2,<2",
  "mypy>=1.11,<2",
  "pytest>=8.3,<9",
  "ruff>=0.6,<1",
]

[project.scripts]
so101ctl = "so101_policy_platform.cli:main"
so101-policy-worker = "so101_policy_platform.policy_worker:main"
so101-edge-agent = "so101_policy_platform.edge_api:main"

[tool.hatch.build.targets.wheel]
packages = ["src/so101_policy_platform"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true
packages = ["so101_policy_platform"]
mypy_path = "src"
```

The CLI and edge-agent script targets intentionally point to modules added by later plans. They reserve stable command names; this plan only runs `so101-policy-worker`.

- [ ] **Step 4: Add the package initializer**

Create `src/so101_policy_platform/__init__.py`:

```python
"""SO-101 policy serving platform."""

__version__ = "0.1.0"
```

- [ ] **Step 5: Extend repository ignores**

Append these lines to `.gitignore`, keeping its existing entries:

```gitignore
.venv/
.mypy_cache/
.pytest_cache/
.ruff_cache/
__pycache__/
*.egg-info/
dist/
results/*.json
```

- [ ] **Step 6: Update the README status and setup command**

Replace `Status: design review before implementation planning.` with:

````markdown
Status: Milestone 1 implementation is planned, beginning with the local mock
policy worker.

## Development Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```
````

- [ ] **Step 7: Install and run complete verification**

Run:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m ruff check .
python -m mypy src
git diff --check
```

Expected: `1 passed`; Ruff, MyPy, and `git diff --check` exit with code 0.

- [ ] **Step 8: Commit the package bootstrap**

```bash
git add pyproject.toml src/so101_policy_platform/__init__.py tests/unit/test_package.py .gitignore README.md
git commit -m "chore: bootstrap Python platform package"
```

## Task 2: Define Strict Inference Contracts

**Files:**

- Create: `src/so101_policy_platform/contracts.py`
- Create: `tests/unit/test_contracts.py`

**Interfaces:**

- Consumes: Pydantic 2.
- Produces: `ActionStep`, `InferenceRequest`, `InferenceResponse`, and `StageTimings`, used by the backend and HTTP worker.

- [ ] **Step 1: Write complete contract tests**

Create `tests/unit/test_contracts.py`:

```python
import pytest
from pydantic import ValidationError

from so101_policy_platform.contracts import (
    ActionStep,
    InferenceRequest,
    InferenceResponse,
    StageTimings,
)


def valid_request_data() -> dict[str, object]:
    return {
        "request_id": "req-000042",
        "task_id": "task-000007",
        "robot_id": "so101-main",
        "instruction": "Pick up the red cube",
        "captured_at_ns": 1_784_222_700_000_000_000,
        "deadline_ms": 150,
        "images": {"front": "base64-jpeg-bytes"},
        "joint_positions": [0.0, 0.1, -0.2, 0.3, 0.4, 0.5],
        "gripper_position": 0.75,
    }


def test_request_accepts_one_so101_observation() -> None:
    request = InferenceRequest.model_validate(valid_request_data())

    assert request.request_id == "req-000042"
    assert request.joint_positions == (0.0, 0.1, -0.2, 0.3, 0.4, 0.5)
    assert request.images == {"front": "base64-jpeg-bytes"}


def test_request_requires_six_joint_positions() -> None:
    data = valid_request_data()
    data["joint_positions"] = [0.0, 0.1]

    with pytest.raises(ValidationError, match="joint_positions"):
        InferenceRequest.model_validate(data)


@pytest.mark.parametrize("instruction", ["", "   "])
def test_request_rejects_blank_instruction(instruction: str) -> None:
    data = valid_request_data()
    data["instruction"] = instruction

    with pytest.raises(ValidationError, match="instruction"):
        InferenceRequest.model_validate(data)


def test_request_rejects_unknown_fields() -> None:
    data = valid_request_data()
    data["unrecognized"] = True

    with pytest.raises(ValidationError, match="unrecognized"):
        InferenceRequest.model_validate(data)


def test_action_requires_six_joint_positions() -> None:
    with pytest.raises(ValidationError, match="joint_positions"):
        ActionStep(joint_positions=(0.0, 0.1), gripper_position=0.5)


@pytest.mark.parametrize("gripper_position", [-0.01, 1.01])
def test_action_rejects_gripper_outside_normalized_range(gripper_position: float) -> None:
    with pytest.raises(ValidationError, match="gripper_position"):
        ActionStep(
            joint_positions=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            gripper_position=gripper_position,
        )


def test_response_requires_at_least_one_action() -> None:
    with pytest.raises(ValidationError, match="actions"):
        InferenceResponse(
            request_id="req-000042",
            model_id="mock-so101-policy",
            model_revision="deterministic-v1",
            actions=[],
            timings_ms=StageTimings(
                queue=0.0,
                preprocess=0.0,
                forward=0.1,
                postprocess=0.0,
                total=0.1,
            ),
        )


def test_response_serializes_to_json_compatible_values() -> None:
    response = InferenceResponse(
        request_id="req-000042",
        model_id="mock-so101-policy",
        model_revision="deterministic-v1",
        actions=[
            ActionStep(
                joint_positions=(0.01, 0.11, -0.19, 0.30, 0.39, 0.49),
                gripper_position=0.72,
            )
        ],
        termination_probability=None,
        timings_ms=StageTimings(
            queue=0.0,
            preprocess=1.2,
            forward=8.4,
            postprocess=0.5,
            total=10.1,
        ),
    )

    payload = response.model_dump(mode="json")

    assert payload["actions"][0]["joint_positions"] == [0.01, 0.11, -0.19, 0.3, 0.39, 0.49]
    assert payload["timings_ms"]["total"] == 10.1
```

- [ ] **Step 2: Run tests and verify the contract module is absent**

Run:

```bash
python -m pytest -q tests/unit/test_contracts.py
```

Expected: collection fails with `ModuleNotFoundError: No module named 'so101_policy_platform.contracts'`.

- [ ] **Step 3: Implement all contract types**

Create `src/so101_policy_platform/contracts.py`:

```python
"""Validated data shared across the policy-serving boundary."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

JointPositions = tuple[float, float, float, float, float, float]
NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictModel(BaseModel):
    """Reject fields that are not part of the service contract."""

    model_config = ConfigDict(extra="forbid")


class ActionStep(StrictModel):
    """One normalized SO-101 action in execution order."""

    joint_positions: JointPositions
    gripper_position: float = Field(ge=0.0, le=1.0)


class InferenceRequest(StrictModel):
    """One timestamped observation sent to the policy worker."""

    request_id: NonBlankText
    task_id: NonBlankText
    robot_id: NonBlankText
    instruction: NonBlankText
    captured_at_ns: int = Field(gt=0)
    deadline_ms: int = Field(gt=0)
    images: dict[NonBlankText, NonBlankText] = Field(min_length=1)
    joint_positions: JointPositions
    gripper_position: float = Field(ge=0.0, le=1.0)


class StageTimings(StrictModel):
    """Worker-side latency components in milliseconds."""

    queue: float = Field(ge=0.0)
    preprocess: float = Field(ge=0.0)
    forward: float = Field(ge=0.0)
    postprocess: float = Field(ge=0.0)
    total: float = Field(ge=0.0)


class InferenceResponse(StrictModel):
    """An ordered action chunk produced for one inference request."""

    request_id: NonBlankText
    model_id: NonBlankText
    model_revision: NonBlankText
    actions: list[ActionStep] = Field(min_length=1)
    termination_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    timings_ms: StageTimings
```

- [ ] **Step 4: Run focused and complete verification**

Run:

```bash
python -m pytest -q tests/unit/test_contracts.py
python -m pytest -q
python -m ruff check .
python -m mypy src
git diff --check
```

Expected: `10 passed` in the focused file, `11 passed` in the full suite, and all static checks exit with code 0.

- [ ] **Step 5: Commit the service contract**

```bash
git add src/so101_policy_platform/contracts.py tests/unit/test_contracts.py
git commit -m "feat: define policy worker contracts"
```

## Task 3: Implement the Backend Boundary and Mock Policy

**Files:**

- Create: `src/so101_policy_platform/policy_backend.py`
- Create: `src/so101_policy_platform/mock_policy.py`
- Create: `tests/unit/test_mock_policy.py`

**Interfaces:**

- Consumes: `InferenceRequest`, `InferenceResponse`, `ActionStep`, and `StageTimings` from `contracts.py`.
- Produces: runtime-checkable `PolicyBackend` protocol and `MockPolicyBackend` used by `policy_worker.py`.

- [ ] **Step 1: Write complete backend behavior tests**

Create `tests/unit/test_mock_policy.py`:

```python
import pytest

from so101_policy_platform.contracts import InferenceRequest
from so101_policy_platform.mock_policy import MockPolicyBackend


def request(
    request_id: str = "req-1",
    joints: tuple[float, float, float, float, float, float] = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    gripper: float = 0.0,
) -> InferenceRequest:
    return InferenceRequest(
        request_id=request_id,
        task_id="task-1",
        robot_id="so101-main",
        instruction="Pick up the red cube",
        captured_at_ns=1,
        deadline_ms=150,
        images={"front": "base64-jpeg-bytes"},
        joint_positions=joints,
        gripper_position=gripper,
    )


def test_backend_must_load_before_inference() -> None:
    backend = MockPolicyBackend()

    with pytest.raises(RuntimeError, match="not loaded"):
        backend.infer_batch([request()])


def test_load_marks_backend_ready_and_is_idempotent() -> None:
    backend = MockPolicyBackend()

    backend.load()
    backend.load()

    assert backend.is_ready is True
    assert backend.model_id == "mock-so101-policy"
    assert backend.model_revision == "deterministic-v1"


def test_inference_preserves_request_order_and_returns_two_actions() -> None:
    backend = MockPolicyBackend()
    backend.load()

    responses = backend.infer_batch([request("req-a"), request("req-b")])

    assert [response.request_id for response in responses] == ["req-a", "req-b"]
    assert [len(response.actions) for response in responses] == [2, 2]


def test_each_action_moves_toward_goal_by_at_most_step_size() -> None:
    backend = MockPolicyBackend()
    backend.load()

    response = backend.infer_batch([request()])[0]

    assert response.actions[0].joint_positions == (0.05, 0.05, 0.05, 0.05, 0.05, 0.05)
    assert response.actions[0].gripper_position == 0.05
    assert response.actions[1].joint_positions == (0.1, 0.1, 0.1, 0.1, 0.1, 0.1)
    assert response.actions[1].gripper_position == 0.1


def test_inference_actions_are_deterministic() -> None:
    backend = MockPolicyBackend()
    backend.load()
    observation = request(joints=(0.3, 0.1, 0.2, -0.1, 0.0, 0.4), gripper=0.8)

    first = backend.infer_batch([observation])[0]
    second = backend.infer_batch([observation])[0]

    assert first.actions == second.actions
    assert first.termination_probability is None
    assert first.timings_ms.total >= 0.0
```

- [ ] **Step 2: Run tests and verify backend modules are absent**

Run:

```bash
python -m pytest -q tests/unit/test_mock_policy.py
```

Expected: collection fails because `so101_policy_platform.mock_policy` does not exist.

- [ ] **Step 3: Define the backend protocol**

Create `src/so101_policy_platform/policy_backend.py`:

```python
"""Boundary implemented by every policy execution backend."""

from typing import Protocol

from so101_policy_platform.contracts import InferenceRequest, InferenceResponse


class PolicyBackend(Protocol):
    """Model lifecycle and batched inference owned by the worker."""

    @property
    def is_ready(self) -> bool:
        raise NotImplementedError

    @property
    def model_id(self) -> str:
        raise NotImplementedError

    @property
    def model_revision(self) -> str:
        raise NotImplementedError

    def load(self) -> None:
        raise NotImplementedError

    def infer_batch(self, requests: list[InferenceRequest]) -> list[InferenceResponse]:
        raise NotImplementedError
```

- [ ] **Step 4: Implement the deterministic policy**

Create `src/so101_policy_platform/mock_policy.py`:

```python
"""Deterministic policy used to prove serving and control flow."""

import time
from typing import cast

from so101_policy_platform.contracts import (
    ActionStep,
    InferenceRequest,
    InferenceResponse,
    JointPositions,
    StageTimings,
)

_JOINT_GOAL: JointPositions = (0.2, 0.2, 0.2, 0.2, 0.2, 0.2)
_GRIPPER_GOAL = 0.5
_MAX_STEP = 0.05


def _step_toward(current: float, goal: float) -> float:
    delta = goal - current
    if abs(delta) <= _MAX_STEP:
        return goal
    return current + (_MAX_STEP if delta > 0.0 else -_MAX_STEP)


def _next_action(joints: JointPositions, gripper: float) -> ActionStep:
    next_joints = cast(
        JointPositions,
        tuple(
            _step_toward(current, goal)
            for current, goal in zip(joints, _JOINT_GOAL, strict=True)
        ),
    )
    return ActionStep(
        joint_positions=next_joints,
        gripper_position=_step_toward(gripper, _GRIPPER_GOAL),
    )


class MockPolicyBackend:
    """Return a predictable two-step action chunk for every observation."""

    def __init__(self) -> None:
        self._is_ready = False

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    @property
    def model_id(self) -> str:
        return "mock-so101-policy"

    @property
    def model_revision(self) -> str:
        return "deterministic-v1"

    def load(self) -> None:
        self._is_ready = True

    def infer_batch(self, requests: list[InferenceRequest]) -> list[InferenceResponse]:
        if not self._is_ready:
            raise RuntimeError("policy backend is not loaded")

        responses: list[InferenceResponse] = []
        for inference_request in requests:
            started_at = time.perf_counter()
            first = _next_action(
                inference_request.joint_positions,
                inference_request.gripper_position,
            )
            second = _next_action(first.joint_positions, first.gripper_position)
            total_ms = (time.perf_counter() - started_at) * 1_000.0
            responses.append(
                InferenceResponse(
                    request_id=inference_request.request_id,
                    model_id=self.model_id,
                    model_revision=self.model_revision,
                    actions=[first, second],
                    timings_ms=StageTimings(
                        queue=0.0,
                        preprocess=0.0,
                        forward=total_ms,
                        postprocess=0.0,
                        total=total_ms,
                    ),
                )
            )
        return responses
```

- [ ] **Step 5: Run focused and complete verification**

Run:

```bash
python -m pytest -q tests/unit/test_mock_policy.py
python -m pytest -q
python -m ruff check .
python -m mypy src
git diff --check
```

Expected: `5 passed` in the focused file, `16 passed` in the full suite, and all static checks exit with code 0.

- [ ] **Step 6: Commit the mock backend**

```bash
git add src/so101_policy_platform/policy_backend.py src/so101_policy_platform/mock_policy.py tests/unit/test_mock_policy.py
git commit -m "feat: add deterministic mock policy"
```

## Task 4: Expose the FastAPI Policy Worker

**Files:**

- Create: `src/so101_policy_platform/policy_worker.py`
- Create: `tests/integration/test_policy_worker.py`

**Interfaces:**

- Consumes: `PolicyBackend`, `MockPolicyBackend`, `InferenceRequest`, and `InferenceResponse`.
- Produces: `create_policy_worker(backend: PolicyBackend | None = None) -> FastAPI`, module-level `app`, `main()`, `GET /health/live`, `GET /health/ready`, and `POST /v1/infer`.

- [ ] **Step 1: Write complete worker integration tests**

Create `tests/integration/test_policy_worker.py`:

```python
from fastapi.testclient import TestClient

from so101_policy_platform.contracts import InferenceRequest, InferenceResponse
from so101_policy_platform.mock_policy import MockPolicyBackend
from so101_policy_platform.policy_worker import create_policy_worker


class CountingBackend(MockPolicyBackend):
    def __init__(self) -> None:
        super().__init__()
        self.load_calls = 0

    def load(self) -> None:
        self.load_calls += 1
        super().load()


def valid_payload() -> dict[str, object]:
    return {
        "request_id": "req-000042",
        "task_id": "task-000007",
        "robot_id": "so101-main",
        "instruction": "Pick up the red cube",
        "captured_at_ns": 1_784_222_700_000_000_000,
        "deadline_ms": 150,
        "images": {"front": "base64-jpeg-bytes"},
        "joint_positions": [0.0, 0.1, -0.2, 0.3, 0.4, 0.5],
        "gripper_position": 0.75,
    }


def test_liveness_does_not_require_loaded_backend() -> None:
    app = create_policy_worker(CountingBackend())
    client = TestClient(app)

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_readiness_is_unavailable_before_lifespan_startup() -> None:
    app = create_policy_worker(CountingBackend())
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "policy backend is not ready"}


def test_lifespan_loads_backend_once_and_reports_ready() -> None:
    backend = CountingBackend()
    app = create_policy_worker(backend)

    with TestClient(app) as client:
        first = client.get("/health/ready")
        second = client.get("/health/ready")

    assert first.status_code == 200
    assert first.json() == {
        "status": "ready",
        "model_id": "mock-so101-policy",
        "model_revision": "deterministic-v1",
    }
    assert second.status_code == 200
    assert backend.load_calls == 1


def test_infer_returns_typed_action_chunk() -> None:
    app = create_policy_worker(CountingBackend())

    with TestClient(app) as client:
        response = client.post("/v1/infer", json=valid_payload())

    parsed = InferenceResponse.model_validate(response.json())
    assert response.status_code == 200
    assert parsed.request_id == "req-000042"
    assert parsed.model_id == "mock-so101-policy"
    assert len(parsed.actions) == 2


def test_infer_rejects_malformed_request() -> None:
    payload = valid_payload()
    payload["joint_positions"] = [0.0]
    app = create_policy_worker(CountingBackend())

    with TestClient(app) as client:
        response = client.post("/v1/infer", json=payload)

    assert response.status_code == 422


def test_infer_is_unavailable_before_backend_startup() -> None:
    app = create_policy_worker(CountingBackend())
    client = TestClient(app)
    request = InferenceRequest.model_validate(valid_payload())

    response = client.post("/v1/infer", json=request.model_dump(mode="json"))

    assert response.status_code == 503
    assert response.json() == {"detail": "policy backend is not ready"}
```

- [ ] **Step 2: Run tests and verify the worker module is absent**

Run:

```bash
python -m pytest -q tests/integration/test_policy_worker.py
```

Expected: collection fails because `so101_policy_platform.policy_worker` does not exist.

- [ ] **Step 3: Implement lifespan, routes, and process entry point**

Create `src/so101_policy_platform/policy_worker.py`:

```python
"""HTTP process that owns policy loading and inference."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, status

from so101_policy_platform.contracts import InferenceRequest, InferenceResponse
from so101_policy_platform.mock_policy import MockPolicyBackend
from so101_policy_platform.policy_backend import PolicyBackend


def create_policy_worker(backend: PolicyBackend | None = None) -> FastAPI:
    selected_backend = backend or MockPolicyBackend()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        selected_backend.load()
        yield

    worker = FastAPI(title="SO-101 Policy Worker", version="0.1.0", lifespan=lifespan)

    @worker.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "live"}

    @worker.get("/health/ready")
    def ready() -> dict[str, str]:
        if not selected_backend.is_ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="policy backend is not ready",
            )
        return {
            "status": "ready",
            "model_id": selected_backend.model_id,
            "model_revision": selected_backend.model_revision,
        }

    @worker.post("/v1/infer", response_model=InferenceResponse)
    def infer(request: InferenceRequest) -> InferenceResponse:
        if not selected_backend.is_ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="policy backend is not ready",
            )
        return selected_backend.infer_batch([request])[0]

    return worker


app = create_policy_worker()


def main() -> None:
    host = os.getenv("SO101_POLICY_HOST", "127.0.0.1")
    port = int(os.getenv("SO101_POLICY_PORT", "8000"))
    uvicorn.run("so101_policy_platform.policy_worker:app", host=host, port=port)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run focused and complete verification**

Run:

```bash
python -m pytest -q tests/integration/test_policy_worker.py
python -m pytest -q
python -m ruff check .
python -m mypy src
git diff --check
```

Expected: `6 passed` in the focused file, `22 passed` in the full suite, and all static checks exit with code 0.

- [ ] **Step 5: Commit the HTTP worker**

```bash
git add src/so101_policy_platform/policy_worker.py tests/integration/test_policy_worker.py
git commit -m "feat: expose local mock policy worker"
```

## Task 5: Document and Smoke-Test the Runnable Worker

**Files:**

- Create: `docs/milestones/01-local-mock-policy-worker.md`
- Modify: `README.md`

**Interfaces:**

- Consumes: `so101-policy-worker`, `/health/live`, `/health/ready`, and `/v1/infer` from Task 4.
- Produces: exact local run and inspection commands for the first professor-mode code walkthrough.

- [ ] **Step 1: Start the worker in one terminal**

```bash
source .venv/bin/activate
so101-policy-worker
```

Expected terminal line includes `Uvicorn running on http://127.0.0.1:8000`.

- [ ] **Step 2: Verify readiness from a second terminal**

```bash
curl --fail --silent http://127.0.0.1:8000/health/ready | python -m json.tool
```

Expected JSON:

```json
{
    "status": "ready",
    "model_id": "mock-so101-policy",
    "model_revision": "deterministic-v1"
}
```

- [ ] **Step 3: Send one complete observation**

```bash
curl --fail --silent \
  --request POST \
  --header 'content-type: application/json' \
  --data '{
    "request_id": "req-000042",
    "task_id": "task-000007",
    "robot_id": "so101-main",
    "instruction": "Pick up the red cube",
    "captured_at_ns": 1784222700000000000,
    "deadline_ms": 150,
    "images": {"front": "base64-jpeg-bytes"},
    "joint_positions": [0.0, 0.1, -0.2, 0.3, 0.4, 0.5],
    "gripper_position": 0.75
  }' \
  http://127.0.0.1:8000/v1/infer | python -m json.tool
```

Expected response properties: `request_id` remains `req-000042`, `model_id` is `mock-so101-policy`, there are exactly two actions, and every timing is non-negative.

- [ ] **Step 4: Write the milestone explanation**

Create `docs/milestones/01-local-mock-policy-worker.md` with this content:

````markdown
# Milestone 1A: Local Mock Policy Worker

## Purpose

This first runnable subsystem proves the model-serving boundary without a model,
robot, camera, or motor. A deterministic backend lets tests verify exact actions
while the HTTP worker proves validation, lifecycle, request mapping, and response
serialization.

## Request Path

```text
curl or future edge agent
        |
        | POST /v1/infer (JSON observation)
        v
FastAPI policy worker
        |
        | validated InferenceRequest
        v
MockPolicyBackend.infer_batch
        |
        | InferenceResponse with two ActionStep values
        v
FastAPI JSON response
```

The policy worker owns inference only. It cannot open a robot serial port and it
cannot execute an action. The future edge agent will decide whether a response is
fresh and safe before putting actions into its bounded queue.

## Why the Mock Comes First

The mock removes model download, MPS compatibility, image preprocessing, learned
behavior, and motor safety from the first debugging session. When an HTTP or
contract test fails, the failure belongs to this subsystem. A Torch backend and a
fine-tuned robot policy will later implement the same `PolicyBackend` protocol.

## What This Does Not Prove

- The base SmolVLA checkpoint can control this SO-101.
- MPS supports every SmolVLA operator.
- Predicted actions are physically safe.
- The camera names, normalization statistics, and joint order match a checkpoint.
- The complete CLI, edge-agent, action-queue, and robot loop work.

Those claims require separate milestones and evidence.
````

- [ ] **Step 5: Add a README quick-start link**

Append:

```markdown
## Current Runnable Subsystem

The first subsystem and its exact request are documented in
[`docs/milestones/01-local-mock-policy-worker.md`](docs/milestones/01-local-mock-policy-worker.md).
```

- [ ] **Step 6: Run final verification**

Stop the worker with `Ctrl-C`, then run:

```bash
python -m pytest -q
python -m ruff check .
python -m mypy src
python -m build
git diff --check
```

Expected: `22 passed`; static checks and package build exit with code 0; `dist/` contains one source archive and one wheel and remains ignored by Git.

- [ ] **Step 7: Commit the runnable-worker guide**

```bash
git add docs/milestones/01-local-mock-policy-worker.md README.md
git commit -m "docs: explain the local mock policy worker"
```

## Review Gate

Before planning the simulator and edge agent:

- [ ] Explain why the worker loads its backend during lifespan startup rather than per request.
- [ ] Trace one JSON field from `curl` through Pydantic, the backend, and the response.
- [ ] Explain why request ID preservation matters when calls become concurrent.
- [ ] Trigger one HTTP 422 response and identify which layer rejected the request.
- [ ] Explain what the mock backend proves and what it cannot prove.
- [ ] Confirm `git status --short --branch` reports a clean branch after every commit is pushed.

The next implementation plan adds the bounded action queue, simulated robot, policy client, and edge-agent task loop. A later plan adds the operator CLI and local process supervisor. The real checkpoint, MPS compatibility, LeRobot adapter, and autonomous hardware remain gated behind those deterministic stages.
