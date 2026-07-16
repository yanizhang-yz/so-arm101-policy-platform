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

Important: the repository is currently in the roadmap and environment-verification
stage. It does not yet contain autonomous robot-control code.
