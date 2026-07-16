# Hardware-to-Policy Engineering Playbook

Use this playbook when a new robot, sensor, task, model, or compute target
arrives. The goal is to make the decision process repeatable instead of copying
the SO-ARM101 stack blindly.

## 1. Begin With the Product Behavior

Write one observable task before choosing a model or framework.

Good:

> Starting from marked home position, pick up one red cube placed in one of five
> documented locations and release it inside the bowl within 30 seconds.

Weak:

> Make the robot intelligent.

Define:

- initial state
- available objects and variations
- success condition
- failure condition
- time limit
- acceptable contact and motion
- human intervention rule
- evaluation episode count

Why this comes first:

- A model cannot be selected without knowing the required behavior.
- A dataset cannot be judged without knowing what distribution it should cover.
- A latency target cannot be selected without knowing the control behavior.
- A demo is not evidence unless success is defined.

## 2. Inventory the Hardware

Record every physical input, output, and connection.

| Area | Questions |
| --- | --- |
| Robot | Model, degrees of freedom, joint names, gripper, limits, control mode? |
| Sensors | Camera count, view, resolution, FPS, depth, force, joint feedback? |
| Teleoperator | Leader arm, joystick, keyboard, motion capture, or none? |
| Compute | Robot computer, edge GPU, cloud GPU, network constraints? |
| Transport | USB, serial, CAN, Ethernet, Wi-Fi, ROS topic, vendor SDK? |
| Safety | Power cutoff, software stop, joint bounds, velocity bounds, workspace? |

Produce:

- hardware inventory
- wiring and process diagram
- device identifiers
- calibration files and procedure
- manual recovery procedure

## 3. Define the Observation and Action Contract

A policy is compatible only if its expected tensors can be constructed and its
output actions can be interpreted safely.

### Observation Questions

- How many camera views?
- What are their semantic names?
- What resolution, color order, and frame rate?
- Which robot-state values are included and in what order?
- Are values positions, velocities, torques, or normalized features?
- How are timestamps aligned?
- Is a language instruction required?
- How old may an observation be when inference begins?

### Action Questions

- Joint positions, velocities, torques, end-effector poses, or discrete skills?
- Which joint order?
- Physical units or normalized values?
- One action or an action chunk?
- What control frequency?
- Which component clips or rejects unsafe output?
- What happens when no new action is available?

Write an example observation and action before integrating a model.

## 4. Choose the Policy Family

Use the task, data, and interface to narrow the family before comparing model
names.

### Narrow Visuomotor Policy

Examples: ACT or Diffusion Policy.

Best fit:

- one or a small number of tasks
- consistent camera and workspace
- enough teleoperated demonstrations
- low serving cost is important
- language variation is not a core requirement

### Vision-Language-Action Policy

Examples: SmolVLA and larger VLA families.

Best fit:

- language is part of the policy input
- multiple instructions or task variations matter
- multimodal foundation-model behavior is part of the learning goal
- GPU training and inference are acceptable

### Planner Plus Learned Skills

Examples: an LLM or VLM selects from separately trained robot skills.

Best fit:

- the robot must perform long, compositional tasks
- reliable low-level skills already exist
- high-level reasoning and low-level continuous control should fail separately

Do not use an LLM response as a direct stream of unchecked motor commands.

## 5. Compare Candidate Models

Create a table and support every score with a source or experiment.

| Criterion | Candidate A | Candidate B | Candidate C |
| --- | --- | --- | --- |
| Task fit | | | |
| Observation compatibility | | | |
| Action compatibility | | | |
| Language support | | | |
| Required demonstrations | | | |
| Training memory and time | | | |
| Inference memory and latency | | | |
| Framework and hardware support | | | |
| Checkpoint and processor maturity | | | |
| License and redistribution | | | |
| Debuggability | | | |
| Community evidence | | | |

Selection rule:

Choose the smallest model that satisfies the actual product behavior and still
exercises the engineering skills the project is meant to teach. Larger is not a
substitute for compatible data or interfaces.

## 6. Choose the Checkpoint Strategy

### Use a Public Fine-Tuned Checkpoint Directly

Choose only when all of these match:

- robot embodiment and joint order
- camera names, views, and preprocessing
- action representation and control frequency
- normalization statistics
- physical task and workspace distribution
- framework and policy versions

Even then, validate offline and use a dry run before moving motors.

### Fine-Tune a Pretrained Model

Choose when:

- the model family supports the required observation and action spaces
- the base model provides useful pretrained representations
- robot- and task-specific demonstrations can be collected
- training compute is available

This is the normal choice for adapting a foundation VLA.

### Train a Policy From Scratch

Choose when:

- the selected architecture does not rely on useful foundation pretraining
- the task is narrow enough for the available dataset
- training cost and validation are understood

Do not train a foundation VLA from scratch with a small teleoperation dataset.

## 7. Design the Dataset Before Recording

Specify:

- instruction vocabulary
- object and start-position variations
- lighting and background policy
- camera placement
- episode length
- control frequency
- successful and failed episode handling
- train and validation split
- minimum demonstrations per variation

Inspect during collection, not only after it finishes:

- video quality
- missing frames
- timestamp gaps
- action saturation
- joint and gripper ranges
- repeated or nearly identical trajectories
- accidental correlations such as one cube position always appearing last

The dataset card is part of the model interface.

## 8. Choose Where Model Compute Runs

### On the Robot Computer

Choose when the model fits, deadlines are met, offline operation matters, and the
device supports the required runtime.

### On a Nearby Edge GPU

Choose when the model is too large for the robot computer but low and predictable
network latency is required.

### On a Cloud GPU

Choose when:

- flexible GPU access is important
- WAN latency can be tolerated or hidden with action chunks
- the local controller can reject stale responses and stop independently
- secure connectivity is available

Measure before committing. Include serialization, network, queue, and action age,
not only model-forward latency.

## 9. Choose Training and Serving GPUs Separately

Training favors:

- enough memory for parameters, activations, gradients, optimizer state, and
  batch size
- mixed-precision support
- training throughput
- checkpoint reliability

Serving favors:

- enough memory for weights, processors, temporary tensors, and concurrency
- deadline latency and tail latency
- utilization and throughput
- hourly or per-request cost
- startup time and availability

Start with a roomy training GPU for correctness. Downsize the serving GPU only
after measuring the real checkpoint.

## 10. Establish a Reference Runtime Before Customizing

Use the model or robot framework's supported path first.

For LeRobot:

- official robot and teleoperator adapters
- official dataset recorder
- official training command
- official checkpoint loader and processors
- official rollout or asynchronous-inference path

The reference path answers whether hardware, data, checkpoint, and framework are
compatible. Custom code written before that answer makes root-cause analysis
harder.

## 11. Draw Ownership Boundaries

Every responsibility needs one authoritative owner.

| Responsibility | Typical owner |
| --- | --- |
| Camera and robot-state capture | Robot client or hardware adapter |
| Observation validation | Robot client |
| Model weights and processors | Policy server |
| GPU inference | Policy server |
| Action queue | Robot client |
| Joint, velocity, and workspace limits | Local safety layer |
| Emergency stop | Local operator and robot client |
| Task result | Evaluator or operator |
| Checkpoint revision | Training and deployment manifest |
| Metrics and trace IDs | Both sides, correlated by request ID |

The remote model may propose actions. The local safety layer decides whether they
are still valid to execute.

## 12. Validate in Increasing-Risk Stages

Use this order:

1. Schema and tensor-shape tests.
2. Dataset sample through processors.
3. Checkpoint load on target GPU.
4. Offline inference on held-out observations.
5. Repeated inference and range checks.
6. Robot client with motors disabled.
7. Dry-run action logging.
8. One bounded, low-speed action.
9. Short rollout with immediate stop access.
10. Full task trials with video and metrics.

Do not skip directly from successful model loading to autonomous motion.

## 13. Benchmark the Complete Path

Measure:

- observation capture age
- serialization and upload
- request queue
- preprocessing
- GPU forward pass
- postprocessing
- download and deserialization
- action queue wait
- action age at execution
- queue underflows
- rejected and stale actions
- task success and failure reason
- GPU memory and utilization
- cost per training run, GPU hour, and task attempt

Report cold and warm behavior separately. Report P50, P95, and P99 rather than
only an average.

## 14. Optimize From Evidence

Use the measured bottleneck to select the next tool.

| Bottleneck | First investigations |
| --- | --- |
| Data quality | demonstrations, variation, labels, calibration |
| Preprocessing | image decode, resize, copies, processor placement |
| GPU forward | precision, compile, CUDA graphs, model architecture |
| Network | payload, compression, placement, transport |
| Queue underflow | chunk size, threshold, scheduling, inference latency |
| Edge jitter | process priority, C++, ROS 2, bounded allocation |
| Concurrency | batching, admission, backpressure, gateway |
| Deployment lifecycle | container, health checks, checkpoint caching |

Custom CUDA, TensorRT, Triton, C++, or Rust are possible answers. None is the
default answer before profiling.

## 15. Required Decision Record

For every major choice, write:

```text
Question:
Constraints:
Options considered:
Selected option:
Why it fits:
What it costs:
Evidence:
What would make us reconsider:
```

This separates engineering reasoning from personal preference and makes the
project useful in interviews.

## 16. SO-ARM101 Example

Applying the playbook to this project:

```text
Task:             red cube into bowl
Robot:            SO-ARM101 leader and follower
Observations:     camera + six motor states + instruction
Actions:          continuous SO-ARM101 action chunks
Primary policy:   lerobot/smolvla_base, fine-tuned
Data:             approximately 50 teleoperated demonstrations
Training:         RunPod A100 80 GB
Serving baseline: LeRobot asynchronous policy server on NVIDIA GPU
Edge:             LeRobot robot client on Mac
Safety:           local bounds, stale-response rejection, queue stop, operator stop
Evidence:         dataset, checkpoint, trials, latency, queues, utilization, cost
```

The values will change for another robot. The questions and evidence standards
should remain.
