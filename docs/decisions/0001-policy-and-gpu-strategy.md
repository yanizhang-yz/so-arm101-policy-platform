# Decision 0001: SmolVLA Fine-Tuning and GPU-First Execution

Date: 2026-07-16

Status: accepted

## Decision Summary

We will:

1. Record demonstrations of one SO-ARM101 pick-and-place task.
2. Fine-tune `lerobot/smolvla_base` on that dataset.
3. Train on a rented RunPod A100 80 GB GPU.
4. Validate and serve the fine-tuned checkpoint on NVIDIA GPUs.
5. Use LeRobot's asynchronous policy server and robot client as the first real
   serving baseline.
6. Keep ACT as a later comparison baseline, not the primary project model.
7. Write custom serving code only after reading, testing, and benchmarking the
   existing LeRobot path.

## Question 1: What Kind of Policy Do We Need?

The desired system receives:

- one or more camera images
- the current robot state
- a natural-language task instruction

It returns:

- a finite chunk of continuous robot actions

That is a vision-language-action, or VLA, policy. A VLA is not just a language
model attached to a robot. It must connect visual observations and language to
the numeric actions expected by a particular robot embodiment.

## Question 2: Which Model Should We Start From?

### Option A: ACT

ACT, or Action Chunking with Transformers, learns imitation directly from robot
demonstrations and predicts action chunks.

Advantages:

- Small compared with modern VLAs.
- Common in LeRobot and easier to train.
- Strong baseline for one narrow, well-demonstrated task.
- Lower inference cost and easier local deployment.
- Makes action chunking easy to study.

Disadvantages for this project's primary goal:

- It is not a language-conditioned foundation VLA in the same sense as SmolVLA.
- It teaches less about multimodal foundation-model serving.
- A narrow ACT policy may learn the one task without exercising the language
  path that interests us.

Decision:

- Keep ACT as the first comparison baseline after the SmolVLA loop works.
- Use it to answer whether the larger VLA earns its additional cost and latency.

### Option B: SmolVLA

SmolVLA is Hugging Face's compact VLA for LeRobot. It accepts camera views,
robot state, and language, and predicts continuous action chunks.

Advantages:

- It is a real VLA and directly matches the learning goal.
- It is substantially smaller than multi-billion-parameter VLA alternatives.
- It has first-party LeRobot training and deployment support.
- It is designed to be fine-tuned on LeRobot datasets.
- Its action-chunk output connects naturally to asynchronous inference, queues,
  latency hiding, and robot control.
- The model is large enough to create meaningful GPU serving work without making
  the first experiment a distributed-training project.

Disadvantages:

- It is slower and more memory-intensive than ACT.
- It still requires task- and embodiment-specific demonstrations.
- Its multimodal processors create more compatibility requirements.
- Remote inference introduces a network and queueing problem.

Decision:

- Select `lerobot/smolvla_base` as the starting checkpoint.
- Fine-tune it on our own SO-ARM101 dataset.

### Option C: A Larger VLA Such as OpenVLA, Pi, or GR00T

Advantages:

- Larger backbones may provide stronger general visual-language representations.
- Some have broader robot and task coverage.
- They expose large-model serving and optimization challenges.

Disadvantages for the first project:

- Higher GPU memory and serving cost.
- More complicated dependencies and model-specific integration.
- Longer iteration cycles make data and hardware mistakes expensive.
- The project could become model installation work before the robot learning loop
  is understood.
- A larger model does not fix mismatched cameras, action spaces, calibration, or
  poor demonstrations.

Decision:

- Do not start here.
- Reconsider a larger VLA only after SmolVLA establishes a measured baseline and
  we can name a capability SmolVLA lacks.

## Why SmolVLA Is the Best First VLA

The decision is not "small is always better." It is the smallest model that
still exercises the system we want to learn:

```text
images + language + robot state
              |
              v
multimodal preprocessing
              |
              v
GPU VLA inference
              |
              v
continuous action chunk
              |
              v
asynchronous queue and robot execution
```

ACT would simplify the model too much for the primary VLA goal. A much larger
VLA would add cost and integration risk before we have a trustworthy dataset or
serving baseline. SmolVLA sits between those extremes.

## Question 3: Use an Existing Checkpoint, Fine-Tune, or Train From Scratch?

### Option A: Serve Someone Else's Fine-Tuned Checkpoint

This is useful for checking whether the software can download and load a model.
It is not sufficient evidence that the model can safely control our arm.

Possible mismatches include:

- camera names and number of cameras
- image resolution and viewpoint
- joint and action ordering
- calibration and mechanical tolerances
- normalization statistics
- control frequency
- task wording, objects, and workspace

Decision:

- Use public checkpoints only for software compatibility experiments.
- Do not use them as the main real-arm policy unless their configuration and
  training data are proven compatible.

### Option B: Train SmolVLA From Scratch

This would discard the visual-language representations learned during
pretraining and require far more data and compute.

Decision:

- Reject. Approximately 50 demonstrations are adaptation data, not foundation
  model pretraining data.

### Option C: Fine-Tune `lerobot/smolvla_base`

Fine-tuning preserves the pretrained model and adapts its processors and action
behavior to our robot, cameras, and task.

Decision:

- Select. This is the intended SmolVLA workflow and gives us both model-learning
  and inference-engineering experience.

## Question 4: What Does Teleoperation Contribute?

During one demonstration:

1. The human moves the leader arm.
2. The follower arm executes the corresponding motion.
3. Cameras capture the scene.
4. LeRobot records robot state and the human-generated action at each time step.
5. The episode is labeled with the task instruction.

The resulting dataset teaches the model which actions tended to follow each
visual state, robot state, and instruction. The arm is a data source and action
executor. The training computation happens later on a GPU.

## Question 5: Where Should Training Run?

### Option A: Apple MPS

Advantages:

- No rental cost.
- Convenient local debugging.

Disadvantages:

- Not the target production inference environment.
- Operator support and performance can differ from CUDA.
- Long training runs consume the development laptop.
- We would still need to repeat environment and performance work on NVIDIA.

Decision:

- Do not use MPS for the main training or serving path.
- The Mac may still inspect datasets and run non-model edge code.

### Option B: Consumer NVIDIA GPU Such as RTX 4090

Advantages:

- Strong compute per dollar.
- Usually cheaper than a data-center GPU.

Disadvantages:

- 24 GB memory can require smaller batches, checkpointing, or other memory work.
- No ECC memory.
- Memory limitations could distract from proving the first training run.

Decision:

- Consider after the reference run, when we can compare cost and throughput.

### Option C: NVIDIA A100 80 GB

Advantages:

- Ample memory for the documented recipe and experiments.
- BF16, Tensor Cores, high memory bandwidth, and mature CUDA support.
- Reduces the chance that the first training lesson becomes an out-of-memory
  tuning lesson.
- Provides a useful professional GPU environment.

Disadvantages:

- Higher hourly cost than consumer GPUs.
- More capacity than serving this model may ultimately require.

Decision:

- Use one RunPod A100 80 GB for the first fine-tuning baseline.
- Shut it down when inactive and keep artifacts on persistent storage.

## Question 6: Which Cloud Product?

### Considered

- RunPod GPU Pod
- AWS, GCP, or Azure GPU VM
- Lambda GPU Cloud
- Modal or another serverless GPU platform

### Decision: RunPod GPU Pod

Reasons:

- Explicit GPU selection.
- Interactive SSH access for learning and debugging.
- Persistent volumes for datasets, checkpoints, and caches.
- Custom containers and normal Linux tooling.
- Transparent hourly pricing and easy shutdown.
- Lower platform complexity than beginning with a large public-cloud account.

Trade-off:

- We own more environment setup than with a managed endpoint.
- Availability and prices vary, so the exact GPU and region must be checked when
  the Pod is created.

We choose a Pod rather than Serverless for training because training is a
stateful, long-running job. Serverless can be evaluated later for intermittent
inference.

## Question 7: How Should the First Real Inference Be Served?

### Option A: Write a Custom FastAPI Service Immediately

Advantages:

- Complete control over the API.
- Familiar backend technology.

Disadvantages:

- Recreates policy loading, processing, queues, and action mapping before we
  understand the reference implementation.
- Makes failures ambiguous: our wrapper or the model stack could be wrong.
- Does not begin in the real LeRobot product path.

Decision:

- Reject as the first step.

### Option B: Run the Policy on the Mac

Decision:

- Reject for the main path because the project explicitly targets NVIDIA CUDA
  training and serving.

### Option C: Use LeRobot Asynchronous Inference

LeRobot already provides a policy server and robot client that decouple GPU
inference from local robot execution. It supports action chunks and policies
including SmolVLA.

Decision:

- Use it as the first correctness baseline.
- Read its request path, model lifecycle, processors, queues, and failure
  behavior line by line.
- Benchmark it before adding or replacing a service boundary.

This is still inference-engineering work. The first engineering skill is knowing
when to adopt a proven subsystem, understand it, and measure it instead of
immediately rebuilding it.

## Question 8: Which GPU Should Serve the Model?

The training GPU is not automatically the serving GPU.

Initial plan:

1. Use the A100 for correctness and the first latency baseline.
2. Verify peak memory and warm latency.
3. Test an L4 24 GB if the checkpoint and processors fit safely.
4. Compare cost, P50, P95, P99, throughput, queue underflow, and task success.
5. Select the cheaper GPU only if it meets the control deadline and reliability
   requirements.

We are not selecting L4 permanently before measuring the real checkpoint.

## Reconsider This Decision When

- SmolVLA cannot achieve useful task success after data-quality iterations.
- The checkpoint cannot meet control deadlines on reasonable GPUs.
- The project changes from language-conditioned tasks to one fixed motion.
- A newer first-party LeRobot policy offers materially better support.
- The action or observation space is incompatible with SmolVLA.
- Cloud networking is too unstable for the required control behavior.

If the first two conditions occur, ACT becomes the next baseline. If cloud
networking is the blocker, the model may move to an NVIDIA edge computer while
the same measurement and safety rules remain.

## Sources

- SmolVLA training and fine-tuning: <https://huggingface.co/docs/lerobot/smolvla>
- LeRobot real-world imitation learning: <https://huggingface.co/docs/lerobot/il_robots>
- LeRobot asynchronous inference: <https://huggingface.co/docs/lerobot/async>
- LeRobot rollout strategies: <https://huggingface.co/docs/lerobot/v0.6.0/inference>
- RunPod GPU Pods and prices: <https://www.runpod.io/pricing>
- NVIDIA A100 architecture: <https://www.nvidia.com/en-us/data-center/a100/>
