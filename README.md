# SO-ARM101 SmolVLA Learning Lab

This repository follows one real robot policy from demonstrations to training,
GPU inference, robot execution, benchmarking, and production-oriented serving.

The first task is deliberately narrow:

> Pick up a red cube and place it in a bowl with an SO-ARM101.

The selected policy is Hugging Face LeRobot's `lerobot/smolvla_base`, fine-tuned
on demonstrations recorded with this SO-ARM101. Model training and inference run
on rented NVIDIA GPUs. The Mac remains the robot-side computer for cameras,
teleoperation, action execution, and safety.

Start with [`docs/ROADMAP.md`](docs/ROADMAP.md). It explains what we are doing,
why the stages are ordered this way, what should be learned, and what evidence
must exist before moving forward.

Supporting guides:

- [`docs/decisions/0001-policy-and-gpu-strategy.md`](docs/decisions/0001-policy-and-gpu-strategy.md)
  explains the selected model, training strategy, cloud, and serving baseline.
- [`docs/guides/hardware-to-policy-playbook.md`](docs/guides/hardware-to-policy-playbook.md)
  provides a reusable method for evaluating future robots, models, and serving
  stacks.

Important: the repository is currently in the roadmap and environment-verification
stage. It does not yet contain autonomous robot-control code.
