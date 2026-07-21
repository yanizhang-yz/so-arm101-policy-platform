# SO-ARM101 SmolVLA Learning Roadmap

Date: 2026-07-16

Status: Phase 1 complete; Phase 2 dataset recording is next

## 1. The Project in One Sentence

Record one SO-ARM101 task through teleoperation, fine-tune SmolVLA on those
demonstrations using a rented NVIDIA GPU, run the resulting policy on the real
arm through remote GPU inference, and then measure and improve the serving path.

## 2. The First Task

The first task is:

> Pick up a red cube and place it in a bowl.

We are choosing one object, one destination, and one instruction because every
extra object, camera layout, background, or instruction adds another source of
variation. We will first prove that the complete learning loop works. We will add
variation only after we can measure the effect of each change.

## 3. The Whole Loop

```text
Human teleoperates the leader arm
                |
                v
Follower arm, camera, state, and actions are recorded
                |
                v
LeRobot dataset with approximately 50 demonstrations
                |
                v
Rented NVIDIA A100 fine-tunes lerobot/smolvla_base
                |
                v
Fine-tuned checkpoint is evaluated off the robot
                |
                v
Cloud policy server loads the checkpoint once
                |
                v
Mac robot client sends observations and receives action chunks
                |
                v
SO-ARM101 executes bounded actions and records task results
                |
                v
Latency, queue behavior, failures, and success rate are analyzed
```

The arm contributes demonstrations and later executes inference results. The
arm does not run the training computation. Training and policy inference run on
an NVIDIA GPU.

## 4. The Main Decisions

### Policy

- Start from `lerobot/smolvla_base`.
- Fine-tune it on our own SO-ARM101 dataset.
- Do not train a VLA from scratch.
- Do not assume another person's checkpoint matches our cameras, calibration,
  joint order, action normalization, or physical task.
- Keep ACT as a smaller comparison baseline after the SmolVLA path works.

### Compute

- Use a rented NVIDIA GPU from the beginning of model work.
- Use a RunPod GPU Pod rather than Apple MPS for the main path.
- Start training on one A100 80 GB GPU to minimize memory troubleshooting.
- Benchmark inference on a less expensive serving GPU after correctness is
  established; the initial comparison candidate is an NVIDIA L4.
- Keep the Mac as the edge computer connected to the arm and cameras.

### Software

- Use LeRobot first for assembly, calibration, teleoperation, recording,
  training, rollout, and asynchronous remote inference.
- Read and test the relevant LeRobot product code rather than recreating it
  before understanding it.
- Add our own code where it creates learning or evidence: reproducible cloud
  setup, checkpoint verification, benchmarks, tracing, failure injection,
  safety validation, reports, and later serving improvements.
- Introduce C++, ROS 2, Rust, TensorRT, Triton, or custom CUDA only after the
  measured baseline shows which problem each technology would solve.

The detailed reasoning and rejected alternatives are recorded in
[`decisions/0001-policy-and-gpu-strategy.md`](decisions/0001-policy-and-gpu-strategy.md).

## 5. Runtime Boundary

The first real deployment has two computers.

```text
Local Mac                              RunPod NVIDIA GPU
-----------------------------          -----------------------------
SO-ARM101 USB connection               Fine-tuned SmolVLA checkpoint
Camera capture                         CUDA and PyTorch
LeRobot robot client       <------>    LeRobot policy server
Observation timestamps                 Preprocessing
Action queue                           Model forward pass
Motor limits                           Postprocessing
Emergency stop                         Action chunks
```

The local side remains authoritative for safety. A network timeout, stale
response, invalid action, or empty action queue must stop or hold the robot
locally. The cloud model never writes directly to a motor bus.

## 6. Phase-by-Phase Roadmap

The estimates assume 4 to 5 focused hours per day. Hardware, dataset quality,
and model convergence can add iteration time, so completion gates matter more
than calendar promises.

### Phase 0: Understand the System and Freeze the Experiment

Estimate: 1 to 2 days

Work:

- Identify the leader arm, follower arm, motor controller, power supplies,
  camera, USB ports, and emergency-stop method.
- Freeze the first task, camera location, workspace, red cube, and bowl.
- Record exact LeRobot and Python versions.
- Create an experiment ID and a place for commands, measurements, and failures.

Learn:

- Leader versus follower roles.
- Observation, state, action, trajectory, episode, dataset, policy, checkpoint,
  inference, and rollout.
- Why reproducibility starts before training.

Completion evidence:

- Hardware inventory.
- One experiment configuration file.
- A diagram showing data and control flow.
- An interview answer explaining the complete project in two minutes.

### Phase 1: Hardware, Calibration, Camera, and Teleoperation

Estimate: 3 to 5 days

Current evidence is recorded in
[`phases/01-hardware-calibration-teleoperation.md`](phases/01-hardware-calibration-teleoperation.md).
The integrated camera and teleoperation stack passed a 16-minute stability run.
A follower-focused teleoperation recording supplies the visual evidence without
implying that the leader and follower need matching physical placement.

Work:

- Install the supported LeRobot version in an isolated environment.
- Discover leader and follower serial ports.
- Configure motor IDs if required.
- Calibrate both arms.
- Verify leader-to-follower teleoperation.
- Configure the camera at the resolution and frame rate used for recording.
- Record a manual safety checklist and recovery procedure.

Learn:

- Serial devices and motor buses.
- Calibration offsets and why policies depend on consistent coordinates.
- Camera frame rate, exposure, resolution, and observation timing.
- Why a physically working arm is not yet a machine-learning system.

Completion evidence:

- A short teleoperation video.
- Saved calibration data.
- Stable camera preview.
- Ten minutes of teleoperation without disconnects or unsafe motion.

### Phase 2: Record and Inspect the Dataset

Estimate: 4 to 7 days

Work:

- Record approximately 50 successful demonstrations.
- Use one language instruction consistently.
- Vary the cube position deliberately across a small documented set.
- Re-record failed or low-quality episodes rather than hiding them.
- Inspect video, states, actions, timestamps, feature shapes, and episode lengths.
- Split training and validation episodes without leaking repeated trajectories.

Learn:

- Behavior cloning and imitation learning.
- What teleoperation teaches the policy.
- Dataset schema and temporal alignment.
- Distribution, variation, data leakage, and data quality.
- Why model performance is often a data problem.

Completion evidence:

- Versioned dataset on the Hugging Face Hub.
- Dataset card describing hardware, task, cameras, variations, and known flaws.
- Data-quality report with plots and example episodes.
- Exact feature names and tensor shapes expected by the policy.

### Phase 3: Create the Reproducible NVIDIA Environment

Estimate: 2 to 3 days

Work:

- Rent a RunPod A100 80 GB Pod.
- Attach persistent storage for datasets, checkpoints, logs, and caches.
- Verify NVIDIA driver, CUDA visibility, PyTorch CUDA support, and GPU memory.
- Install the exact LeRobot commit or release used by the project.
- Authenticate to Hugging Face without committing tokens.
- Download and validate the dataset and `lerobot/smolvla_base`.
- Capture the environment in scripts and a container definition.

Learn:

- GPU driver versus CUDA runtime versus PyTorch CUDA build.
- GPU memory, mixed precision, batch size, and out-of-memory failures.
- Ephemeral compute versus persistent storage.
- Secrets, model caches, and immutable dependency versions.

Completion evidence:

- One command verifies the GPU environment.
- One command recreates the training container.
- Environment report includes GPU, driver, CUDA, PyTorch, LeRobot, and commit IDs.
- A cost log records active GPU time and storage separately.

### Phase 4: Fine-Tune SmolVLA

Estimate: 3 to 6 days including iteration

Work:

- Run a small overfit experiment first to prove data and model compatibility.
- Run the main fine-tuning job from `lerobot/smolvla_base`.
- Begin with the documented 20,000-step recipe and change one variable at a time.
- Track loss, learning rate, throughput, GPU memory, step time, and checkpoints.
- Resume from a checkpoint once to prove recovery.
- Save configuration, processor state, normalization statistics, and weights.

Learn:

- Pretraining versus fine-tuning versus training from scratch.
- Flow matching at a conceptual level.
- Checkpoints, optimizer state, processors, and normalization statistics.
- Training throughput, utilization, convergence, and experiment comparison.
- Why lower training loss does not guarantee robot success.

Completion evidence:

- Fine-tuned checkpoint on the Hugging Face Hub.
- Training report with commands, curves, cost, and failures.
- Reproducible checkpoint revision and content hash.
- Evidence that the model can process held-out observations and return correctly
  shaped action chunks.

### Phase 5: Validate the Checkpoint Before Moving the Robot

Estimate: 2 to 4 days

Work:

- Load the checkpoint once on the cloud GPU.
- Run held-out observations through preprocessing, inference, and postprocessing.
- Verify camera names, state order, action order, tensor shapes, dtypes, ranges,
  normalization, and action chunk length.
- Compare repeated inference for determinism where expected.
- Test malformed observations and incompatible checkpoints.

Learn:

- Model loading and readiness.
- Preprocessing and postprocessing contracts.
- `eval()`, inference mode, autocast, synchronization, and warm-up.
- Model correctness versus task correctness.

Completion evidence:

- Offline checkpoint-validation test suite.
- Golden observation and action-shape fixtures.
- Cold-start and warm-inference measurements.
- No motor movement in this phase.

### Phase 6: Run Remote GPU Inference on the SO-ARM101

Estimate: 4 to 7 days

Work:

- Run LeRobot's policy server on the RunPod GPU.
- Run LeRobot's robot client on the Mac.
- Use an authenticated private connection rather than a public unauthenticated
  motor-control endpoint.
- Start with motors disabled or dry-run action logging.
- Add local action bounds, response-age checks, queue-underflow behavior, timeout,
  cancellation, and an emergency stop.
- Execute short, low-speed trials before full task attempts.
- Record at least ten evaluation episodes with success or failure labels.

Learn:

- Synchronous versus asynchronous inference.
- Action chunks, queue thresholds, backpressure, and receding-horizon control.
- Network latency, model latency, end-to-end latency, and stale responses.
- Why safety belongs at the edge.

Completion evidence:

- Video of dry-run and bounded-motion tests.
- At least ten labeled task trials.
- Success rate with confidence limits appropriate to the small sample.
- Failure taxonomy separating policy, data, network, serving, and hardware causes.

### Phase 7: Benchmark the Real Serving Path

Estimate: 4 to 6 days

Work:

- Instrument observation capture, serialization, upload, queueing, preprocessing,
  forward pass, postprocessing, download, queue wait, and action execution.
- Separate cold start from warm inference.
- Measure P50, P95, P99, throughput, GPU memory, utilization, queue depth,
  underflows, stale actions, and task success.
- Sweep action chunk size, actions consumed per chunk, queue threshold, precision,
  and request concurrency where safe.
- Compare A100 with a lower-cost inference GPU such as L4.

Learn:

- Benchmark design and measurement bias.
- Latency-throughput trade-offs.
- GPU utilization and memory behavior.
- Tail latency and its effect on physical control.
- Why the cheapest GPU is a workload decision, not a model-name decision.

Completion evidence:

- Reproducible benchmark harness.
- Raw machine-readable results.
- Charts and written interpretation.
- A serving-GPU recommendation supported by cost, latency, and task evidence.

### Phase 8: Read and Improve Product Code

Estimate: 1 to 2 weeks

Work:

- Trace LeRobot's robot client, policy server, request path, queue, processors,
  policy load, inference call, and action execution line by line.
- Add tests around one measured weakness or missing observability feature.
- Implement one bounded improvement in this repository or contribute it upstream.
- Add failure injection for delay, disconnect, malformed response, and worker crash.
- Keep improvements compatible with the known-correct baseline.

Learn:

- How production robotics code divides ownership.
- Concurrency, futures, queues, cancellation, and lifecycle management.
- Testability at process and hardware boundaries.
- How to make an engineering claim with before-and-after evidence.

Completion evidence:

- Small reviewed commits.
- Tests that fail before and pass after the change.
- Before-and-after benchmark.
- Design explanation and interview-ready trade-off discussion.

### Phase 9: Optimization and Systems Extensions

Estimate: 2 to 4 weeks, selected by evidence

Possible work:

- `torch.compile`, precision changes, processor optimization, or CUDA graphs.
- ONNX and TensorRT compatibility investigation.
- Triton only if its batching, model repository, metrics, or lifecycle help.
- Custom CUDA or Triton kernels only for a profiled GPU bottleneck.
- C++ or ROS 2 only for a measured edge-runtime requirement.
- Rust only for a real gateway, reliability, or concurrency requirement.

This phase is intentionally not preselected. The benchmark tells us which option
has value.

## 7. Estimated Duration

At 4 to 5 focused hours every day:

- First trained checkpoint: approximately 3 to 4 weeks.
- First cautious real-arm rollout: approximately 4 to 6 weeks.
- Strong inference-engineering case study: approximately 7 to 10 weeks.
- Deeper systems optimization extension: approximately 10 to 14 weeks total.

These ranges include learning and documentation, not only typing code.

## 8. How Every Session Will Be Taught

For each meaningful component:

1. State the real product problem.
2. Show where the component sits in the full system.
3. Define the vocabulary.
4. Present the realistic options.
5. Explain the selected option and rejected alternatives.
6. Read the public interface and tests.
7. Run one real command and inspect its input and output.
8. Read the implementation line by line.
9. Trigger one failure and trace it.
10. Benchmark the behavior when measurement is meaningful.
11. Write a short takeaway and interview answer.
12. Make one small, coherent commit and push it.

The point is transferable judgment. The learner should be able to repeat the
same reasoning when a different robot, camera, task, policy, or GPU arrives.

## 9. Evidence Bar

The project is complete only when it contains:

- A versioned real-robot dataset and dataset card.
- A reproducible GPU training environment.
- A fine-tuned checkpoint and training report.
- Offline validation tests.
- Safe remote inference on the SO-ARM101.
- At least ten labeled real task trials.
- A benchmark harness with raw results and interpretation.
- A measured serving improvement.
- Clean code, small commits, and line-by-line understanding.
- A concise architecture explanation and interview answers.

## 10. Sources

- LeRobot SO-ARM101 assembly: <https://huggingface.co/docs/lerobot/main/en/assemble_so101>
- LeRobot real-world imitation learning: <https://huggingface.co/docs/lerobot/il_robots>
- SmolVLA: <https://huggingface.co/docs/lerobot/smolvla>
- LeRobot asynchronous inference: <https://huggingface.co/docs/lerobot/async>
- LeRobot policy deployment: <https://huggingface.co/docs/lerobot/v0.6.0/inference>
- RunPod GPU pricing: <https://www.runpod.io/pricing>
