# SO-101 Policy Platform Design

Date: 2026-07-16

Status: ready for user review

## 1. Product Decision

Build a new capstone repository named `so101-policy-platform`.

The repository will teach and demonstrate the complete path from a typed task
instruction and robot observation to policy inference, action chunk execution,
feedback, metrics, and task completion.

Development will begin with a small local vertical slice on the user's Mac:

- Python 3.12
- FastAPI and Uvicorn
- HTTP and JSON contracts
- PyTorch on CPU or Apple MPS
- a simulated robot adapter before real motors
- separate policy-worker and edge-agent processes
- one launcher command and one task command

The architecture will then evolve without changing the product-level behavior:

- a real SO-101 adapter through LeRobot
- a rented NVIDIA cloud GPU using CUDA
- Protocol Buffers and gRPC
- a C++20 ROS 2 edge runtime
- a Rust ingress gateway
- TensorRT or Triton when model compatibility and profiling justify them

The existing `robotics-inference-lab` remains the educational experiments repo.
This repository is the polished product-shaped capstone.

## 2. Problem

A trained robot policy is not yet a usable robot system. A deployable system
must also:

- acquire coherent camera and joint observations
- transmit observations to a model service
- load and retain the selected checkpoint
- preprocess model inputs exactly as training expected
- schedule and execute policy inference
- convert outputs into bounded action chunks
- keep the robot control loop responsive while inference is running
- reject stale, malformed, or unsafe commands
- determine whether to continue, stop, or report task completion
- measure latency, queue behavior, deadline misses, and task outcomes

This project implements those system responsibilities in progressively more
production-oriented forms.

## 3. Goals

1. Provide a runnable local system that can be understood line by line.
2. Keep the model service separate from the robot control process.
3. Make CPU, MPS, and later CUDA backends interchangeable behind one interface.
4. Use typed request and response contracts from the first milestone.
5. Demonstrate action chunking, queue replenishment, feedback, and cancellation.
6. Keep motor safety authoritative on the robot computer.
7. Capture reproducible latency, throughput, queue, and task metrics.
8. Evolve the same system toward C++, ROS 2, Rust, gRPC, and TensorRT.
9. Produce code, tests, runbooks, reports, and interview-ready explanations.

## 4. Non-Goals

The first implementation will not:

- train a new VLA model
- assume arbitrary policies work on the SO-101 embodiment
- control the robot through voice input
- expose the local service to the public internet
- use Kubernetes for one robot and one worker
- write custom CUDA kernels before profiling finds a GPU bottleneck
- claim automatic task success when the selected policy has no termination head
- send unchecked cloud responses directly to servo motors

## 5. Users and Main Workflow

The initial user is an inference engineer developing on a Mac with an SO-101,
one front camera, and a compatible policy checkpoint.

The planned operator workflow is:

```bash
MODEL_REPO=yanizhang/so101-smolvla \
MODEL_REVISION=010000 \
DEVICE=mps \
ROBOT_PORT=/dev/tty.usbmodemXXXX \
FRONT_CAMERA=0 \
make local-up
```

After readiness checks pass:

```bash
./bin/so101ctl task start \
  --instruction "Pick up the red cube from the mat and place it in the bowl" \
  --timeout-s 60 \
  --feedback
```

These commands are requirements for the implementation. They are not available
until the corresponding milestones are built.

## 6. Delivery Strategy

The system will be delivered as seven independently runnable milestones.

### Milestone 1: Local Simulated Vertical Slice

Build the complete request loop with no hardware risk:

- `so101ctl` typed task command
- local edge-agent process
- local policy-worker process
- deterministic mock policy backend
- simulated camera, joints, gripper, and servo execution
- HTTP request and response contracts
- action queue and replenishment threshold
- cancellation, timeout, and safe stop
- unit and end-to-end tests

This milestone runs on CPU and proves service boundaries and control flow.

### Milestone 2: Local Torch Policy Backend

Add:

- checkpoint manifest and immutable revision
- model load once at worker startup
- `torch.inference_mode()` and `model.eval()`
- CPU and MPS device selection
- warm-up before readiness
- preprocessing, forward, postprocessing, and end-to-end timings
- a small Torch policy-shaped model before a heavy VLA

### Milestone 3: Real SO-101 Adapter

Add:

- LeRobot SO-101 follower adapter
- camera adapter
- calibration and readiness checks
- observed joint and gripper feedback
- joint, velocity, and action-age validation
- manual success/failure labeling
- dry-run mode that logs actions without moving motors
- real hardware metrics and video evidence

### Milestone 4: NVIDIA Cloud Worker

Move only the policy worker to a rented NVIDIA Linux machine:

- Docker and NVIDIA Container Toolkit
- PyTorch CUDA backend
- checkpoint download and verification
- secure tunnel or authenticated TLS endpoint
- network timeout and stale-response rejection
- CPU/MPS versus CUDA benchmark report

The Mac edge-agent and task CLI remain unchanged except for the worker URL.

### Milestone 5: gRPC and C++/ROS 2 Edge Runtime

Replace the local HTTP data plane with `policy.v1.PolicyService/Infer` and add:

- Protocol Buffers
- generated Python and C++ clients
- C++20 bounded queues and ownership
- ROS 2 camera and joint-state topics
- timestamp-aligned observations
- a cancellable `/execute_task` ROS action
- C++ deadline handling and action execution

The Python LeRobot hardware node remains the hardware adapter until a C++ driver
provides clear value.

### Milestone 6: Rust Gateway

Insert `policy-gateway-rs` between robot clients and GPU workers:

- Tokio and Tonic
- authentication and transport security
- per-robot admission control
- request size limits
- deadline propagation
- model-version routing
- circuit breaking
- OpenTelemetry trace propagation

The gateway does not decode images, preprocess tensors, or execute the model.

### Milestone 7: TensorRT or Triton Optimization

After profiling the PyTorch CUDA baseline:

- attempt ONNX export for compatible model regions
- build a TensorRT engine for the target GPU profile
- verify numerical and task-level correctness
- compare P50, P95, P99, throughput, memory, and startup cost
- use Triton only when its model repository and backend model simplify serving
- retain PyTorch as the correctness baseline and fallback

## 7. Initial Repository Layout

The first milestones use this structure:

```text
so101-policy-platform/
|-- README.md
|-- Makefile
|-- pyproject.toml
|-- src/so101_policy_platform/
|   |-- contracts.py
|   |-- devices.py
|   |-- metrics.py
|   |-- policy_backend.py
|   |-- policy_worker.py
|   |-- policy_client.py
|   |-- robot_adapter.py
|   |-- simulated_robot.py
|   |-- action_queue.py
|   |-- task_runner.py
|   |-- edge_api.py
|   `-- cli.py
|-- scripts/
|   `-- local_up.py
|-- tests/
|   |-- unit/
|   |-- integration/
|   `-- end_to_end/
|-- benchmarks/
|-- configs/
|-- docs/
`-- results/
```

Later milestones add these bounded areas:

```text
contracts/proto/policy/v1/
edge/ros2_ws/src/so101_interfaces/
edge/ros2_ws/src/so101_hardware_py/
edge/ros2_ws/src/so101_runtime_cpp/
services/policy_gateway_rs/
model_tooling/tensorrt_builder/
deploy/docker/
deploy/helm/
observability/
```

## 8. Initial Runtime Processes

The local system uses separate processes with one development launcher.

### Policy Worker

Command implemented by `make run-policy-worker`.

Technology:

- Python
- FastAPI
- Uvicorn
- Pydantic
- PyTorch

Responsibilities:

- select CPU or MPS
- load one checkpoint/backend during startup
- warm the backend before reporting ready
- validate inference requests
- preprocess a batch
- run inference
- return action chunks and stage timings
- expose liveness and readiness endpoints

The policy worker never opens a serial port and never sends motor commands.

### Edge Agent

Command implemented by `make run-edge`.

Technology:

- Python for the first three milestones
- FastAPI for the local task-control API
- `httpx` for policy-worker requests
- LeRobot only after the simulator is stable

Responsibilities:

- own the robot adapter
- own the active task state
- capture observations
- request action chunks when the queue is low
- validate and enqueue policy output
- execute one action per control tick
- publish task feedback
- enforce cancellation, timeout, and safe stop

The edge agent remains authoritative even when inference moves to the cloud.

### Operator CLI

Command implemented as `so101ctl`.

Technology:

- Python standard-library `argparse`
- HTTP client for the first milestones
- ROS 2 action client after Milestone 5

Responsibilities:

- submit typed task instructions
- stream task feedback
- cancel an active task
- record operator-confirmed success or failure
- print the task ID and final result

### Local Launcher

Command implemented by `make local-up` through `scripts/local_up.py`.

Responsibilities:

- start the worker before the edge agent
- wait for worker readiness
- start the edge agent
- wait for robot readiness
- forward shutdown signals
- stop child processes in reverse order
- surface child-process failures clearly

This is a development supervisor, not a production process manager.

## 9. Python Interfaces

The first milestone defines small interfaces that later implementations preserve.

```python
class PolicyBackend(Protocol):
    def load(self) -> None: ...
    def infer_batch(
        self, requests: list[ObservationRequest]
    ) -> list[ActionChunkResponse]: ...


class RobotAdapter(Protocol):
    def read_observation(self) -> RobotObservation: ...
    def apply_action(self, action: ActionStep) -> None: ...
    def stop(self) -> None: ...
    def health(self) -> RobotHealth: ...


class SuccessDetector(Protocol):
    def evaluate(self, task: Task, observation: RobotObservation) -> TaskStatus: ...
```

Initial implementations:

- `MockPolicyBackend`
- `TorchPolicyBackend`
- `SimulatedRobotAdapter`
- `LeRobotSO101Adapter`
- `ManualSuccessDetector`
- later `VisionSuccessDetector`

## 10. HTTP Contracts

The initial HTTP API is intentionally easy to inspect with `curl` and tests.

### Policy Worker Endpoints

```text
GET  /health/live
GET  /health/ready
POST /v1/infer
```

`POST /v1/infer` accepts:

```json
{
  "request_id": "req-000042",
  "task_id": "task-000007",
  "robot_id": "so101-main",
  "instruction": "Pick up the red cube",
  "captured_at_ns": 1784222700000000000,
  "deadline_ms": 150,
  "images": {
    "front": "base64-jpeg-bytes"
  },
  "joint_positions": [0.0, 0.1, -0.2, 0.3, 0.4, 0.5],
  "gripper_position": 0.75
}
```

It returns:

```json
{
  "request_id": "req-000042",
  "model_id": "yanizhang/so101-smolvla",
  "model_revision": "010000",
  "actions": [
    {
      "joint_positions": [0.01, 0.11, -0.19, 0.30, 0.39, 0.49],
      "gripper_position": 0.72
    }
  ],
  "termination_probability": null,
  "timings_ms": {
    "queue": 0.0,
    "preprocess": 1.2,
    "forward": 8.4,
    "postprocess": 0.5,
    "total": 10.1
  }
}
```

Base64 JPEG is accepted for the learning-first HTTP version. Milestone 5 replaces
it with Protobuf `bytes` to reduce size and serialization overhead.

### Edge-Agent Endpoints

```text
GET  /health/live
GET  /health/ready
POST /v1/tasks
GET  /v1/tasks/{task_id}
POST /v1/tasks/{task_id}/cancel
POST /v1/tasks/{task_id}/operator-result
```

Only one active task is allowed in the initial SO-101 system.

## 11. Request and Action Loop

1. `so101ctl` creates a task through the edge agent.
2. The edge agent validates readiness and stores the typed instruction.
3. Camera and robot state are sampled with timestamps.
4. The observation is rejected if required data is missing or too old.
5. When the action queue falls below its threshold, the edge agent sends an
   inference request.
6. The policy worker preprocesses image, text, and proprioception.
7. The backend returns a finite action chunk.
8. The edge agent rejects responses that are late, mismatched, malformed, or
   outside configured limits.
9. Accepted actions are appended or blended into the action queue.
10. One action is applied per control tick.
11. New measured joints and camera images become the next observation.
12. The loop repeats until success, failure, cancellation, timeout, or safety
    stop.

This is receding-horizon behavior. The policy repeatedly replans from recent
observations instead of sending one unchecked full-task trajectory.

## 12. Timing and Queue Policy

The initial control frequency is configurable and defaults to 30 Hz because the
current LeRobot rollout documentation uses 30 FPS as its common default.

The service does not use a fixed universal latency SLO. Its useful deadline is
derived from queue runway:

```text
queue_runway_ms = queued_actions / control_frequency_hz * 1000
inference_deadline_ms = queue_runway_ms - safety_margin_ms
```

The edge agent requests a new chunk before runway reaches the safety margin.

Metrics must prove:

- request latency P50, P95, and P99
- queue depth over time
- queue underflow count
- late response count
- stale observation count
- actions accepted and rejected
- control-loop period distribution

## 13. Feedback and Task Completion

Two feedback loops are distinct.

### Control Feedback

Measured joint and gripper positions are read after commands and included in
future observations. This feedback is always required.

### Task-Level Success

Milestone 3 uses operator-confirmed success or failure because a generic VLA
checkpoint may not provide a reliable termination signal.

The active task can end through:

- operator-confirmed success
- operator-confirmed failure
- user cancellation
- configured timeout
- safety stop
- a model termination probability only when the selected policy supports it
- a later independent vision success detector

The system never invents success from motion completion alone.

## 14. Safety Requirements

1. The policy worker never communicates directly with motors.
2. The robot adapter starts disabled until calibration and health checks pass.
3. Dry-run mode is the default for the first hardware integration.
4. Every response must match the active task and request IDs.
5. Responses older than their deadline are discarded.
6. Joint positions, per-step deltas, velocities, and gripper commands are bounded.
7. Cancellation clears pending requests and queued actions.
8. Queue underflow causes a configured safe hold or stop.
9. Network failures do not trigger blind retries of stale observations.
10. The operator can stop the task independently of model-server health.

This project is an educational system and does not claim safety certification.

## 15. Checkpoints and Model Versioning

A model manifest records:

```yaml
model_id: yanizhang/so101-smolvla
revision: "010000"
checkpoint_sha256: immutable-content-hash
policy_type: smolvla
robot_type: so101_follower
camera_names:
  - front
action_dimension: 7
action_horizon: 16
normalization_revision: norm-v1
```

The worker startup sequence is:

1. Read the manifest.
2. Download or locate the pinned checkpoint revision.
3. Verify the expected artifact hash when available.
4. Load policy configuration, processors, and normalization data.
5. Construct the model.
6. Load checkpoint weights.
7. Move the model to CPU, MPS, or CUDA.
8. Call `model.eval()`.
9. Run a warm-up under `torch.inference_mode()`.
10. Mark the worker ready.

Requests reuse the in-memory model and never reload the checkpoint.

## 16. Local and Cloud Deployment Profiles

### Local Mac Profile

- all processes run natively on macOS
- policy worker binds to `127.0.0.1:8000`
- edge agent binds to `127.0.0.1:8001`
- CPU or MPS backend
- no public network exposure
- no TensorRT
- no CUDA

The full-stack local profile includes every initial process even though the
gateway is not yet present.

### NVIDIA Cloud Profile

- edge agent and robot remain local
- policy worker runs in an NVIDIA-enabled Linux container
- Docker receives GPU access through NVIDIA Container Toolkit
- checkpoint is loaded into CUDA memory once
- development traffic uses an SSH tunnel
- production-shaped traffic uses authenticated TLS
- the edge agent changes only `POLICY_BASE_URL`

Later the Rust gateway becomes the only externally reachable data-plane service.

## 17. Failure Handling

| Failure | Required behavior |
| --- | --- |
| Worker not ready | Edge agent refuses to start an autonomous task. |
| Checkpoint load fails | Worker remains unready and reports the exact cause. |
| Camera frame missing | Observation is not sent; task feedback reports waiting. |
| Joint feedback stale | Robot enters safe hold or stop. |
| Inference timeout | Response is discarded; no blind retry of the old observation. |
| Malformed action shape | Entire chunk is rejected. |
| Unsafe action value | Entire chunk is rejected and safety metric increments. |
| Queue underflow | Robot performs configured safe hold or stop. |
| User cancellation | Clear queue, stop requests, stop robot, report cancelled. |
| Model process crashes | Edge safety process remains alive and stops the robot. |

## 18. Observability

Every task and inference request carries `task_id`, `request_id`, `robot_id`, and
`model_revision`.

Initial output is structured JSON logs plus result files. Later milestones add
OpenTelemetry, Prometheus, and Grafana without changing metric meanings.

Required inference metrics:

- queue wait
- preprocess latency
- model forward latency
- postprocess latency
- end-to-end latency
- P50, P95, P99
- action chunks per second
- observed batch size
- device and model revision

Required robot metrics:

- observation age
- camera frame interval
- joint feedback age
- control-loop period
- action queue depth
- queue underflows
- stale actions discarded
- unsafe actions rejected
- task duration
- operator success or failure result

## 19. Testing Strategy

### Unit Tests

- request and response validation
- action queue behavior
- queue replenishment decision
- timeout and deadline calculation
- stale response rejection
- action-limit validation
- model manifest parsing
- simulator state transitions

### Integration Tests

- HTTP client to worker with deterministic backend
- CLI to edge agent
- edge agent to policy worker
- worker startup and readiness
- task cancellation during inference
- worker crash while edge agent remains alive

### End-to-End Tests

- one command starts the local platform
- typed instruction creates a task
- simulator observations produce multiple inference requests
- action chunks are executed in order
- task feedback streams to the CLI
- cancellation clears the queue and stops execution
- operator result produces a reproducible metrics file

### Hardware Tests

- camera-only observation capture
- arm connected with motors disabled
- dry-run action logging
- low-speed bounded action
- cancellation and queue-underflow stop behavior
- at least ten documented task trials before reporting success rate

### GPU Tests

- CUDA visibility and model load
- CPU/MPS versus CUDA output comparison
- warm and cold latency separation
- concurrency and batch-size sweep
- GPU memory and utilization capture

## 20. Continuous Integration

Initial CI runs:

- formatting and linting
- type checking
- Python unit tests
- Python integration tests with the mock backend
- package build
- `git diff --check`

Later CI adds:

- Protocol Buffer compatibility checks
- C++ build, tests, and sanitizers
- Rust formatting, Clippy, and tests
- container builds
- GPU integration tests on a dedicated runner

Large model weights, datasets, TensorRT plan files, and captured videos are not
committed to Git.

## 21. Acceptance Criteria

### Local Simulated Slice

- `make local-up` starts worker and edge agent and waits for readiness.
- `so101ctl task start` accepts a typed instruction.
- the simulator completes a multi-request, multi-chunk control loop.
- cancellation and timeout stop execution and clear queued actions.
- tests and documented commands reproduce the behavior.

### Local Torch Backend

- worker loads the selected backend once.
- CPU and MPS can be selected by configuration.
- warm-up occurs before readiness.
- stage and end-to-end timings are recorded.
- deterministic fixtures validate output shape and request mapping.

### Real SO-101

- calibration and camera checks pass before autonomous motion.
- dry-run mode records predicted actions without moving motors.
- bounded low-speed actions execute through LeRobot.
- empty queues, stale responses, and cancellation produce a safe stop.
- at least ten trials record task result, latency, queue, and failure reason.

### NVIDIA Cloud

- the same edge client calls the remote CUDA worker by changing configuration.
- the cloud worker reports its GPU, CUDA, model, and checkpoint revision.
- network and service timings are separated.
- a report compares local CPU/MPS and remote CUDA behavior honestly.

### Production-Oriented Extensions

- generated gRPC clients preserve the same logical request contract.
- C++/ROS 2 owns deadline-sensitive edge queues and execution.
- Rust gateway enforces admission and propagates deadlines.
- TensorRT or Triton is adopted only with correctness evidence and a measurable
  benefit over the PyTorch baseline.

## 22. Learning Workflow

Each milestone will be taught in this order:

1. State the interview-style system requirement.
2. Draw the component and request path.
3. Read the public types and tests.
4. Implement one behavior at a time with test-driven development.
5. Run the service and inspect one real request.
6. Explain the implementation line by line.
7. Introduce one failure and trace it across process boundaries.
8. Benchmark the behavior.
9. Write takeaways and interview answers.
10. Commit the coherent learning unit before moving on.

## 23. Source References

- LeRobot SO-101: <https://huggingface.co/docs/lerobot/main/en/so101>
- LeRobot policy deployment: <https://huggingface.co/docs/lerobot/main/inference>
- LeRobot policy integration: <https://huggingface.co/docs/lerobot/main/en/bring_your_own_policies>
- PyTorch inference mode: <https://docs.pytorch.org/docs/stable/generated/torch.autograd.grad_mode.inference_mode.html>
- PyTorch CUDA semantics: <https://docs.pytorch.org/docs/main/notes/cuda.html>
- ROS 2 topics, services, and actions: <https://docs.ros.org/en/ros2_documentation/kilted/How-To-Guides/Topics-Services-Actions.html>
- gRPC deadlines: <https://grpc.io/docs/guides/deadlines/>
- Rust Tonic: <https://github.com/hyperium/tonic>
- NVIDIA Container Toolkit: <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html>
- NVIDIA TensorRT architecture: <https://docs.nvidia.com/deeplearning/tensorrt/latest/architecture/architecture-overview.html>
- NVIDIA Triton quickstart: <https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/getting_started/quick_start.html>
