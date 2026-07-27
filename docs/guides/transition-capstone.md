# Real-Arm Transition Capstone

This repository is the advanced physical-system path for
[M3 — Optional Real-Arm Capstone](https://github.com/yanizhang-yz/software-to-robotics-inference/blob/main/docs/milestones/m3-real-arm-capstone.md).
This page maps evidence states to their authoritative phase documents; it does
not replace the [phase-by-phase roadmap](../ROADMAP.md).

## What Software Engineers Already Know

Treat observations, actions, checkpoints, and network messages as versioned
interfaces with explicit owners, tests, failure behavior, and measurable
service levels. The roadmap's [runtime boundary](../ROADMAP.md#5-runtime-boundary)
applies those familiar responsibilities to a robot client and GPU policy server.

## New Hardware Responsibilities

Physical identity, calibration, camera placement, workspace clearance, power
cutoff, and supervised recovery now affect correctness. The committed
[foundation](../phases/00-foundation.md) and
[hardware-validation phase](../phases/01-hardware-calibration-teleoperation.md)
own that evidence.

## Safety Gate

**Verified for calibration and supervised, camera-enabled teleoperation.**
The evidence and recovery constraints are in
[Phase 1](../phases/01-hardware-calibration-teleoperation.md). Autonomous
control is absent, so this state does not verify policy-driven motion.

## Data Gate

**Active.** [Phase 2](../phases/02-record-and-inspect-dataset.md) owns the
three-episode recording pilot and its unchecked completion gate. Dataset
quality and publication are not yet verified.

## Training Gate

**Planned.** The existing [GPU-environment and fine-tuning phases](../ROADMAP.md#phase-3-create-the-reproducible-nvidia-environment)
own the future training evidence. No committed checkpoint or training report
currently satisfies this gate.

## Evaluation Gate

**Planned.** The [offline-validation and real-arm inference phases](../ROADMAP.md#phase-5-validate-the-checkpoint-before-moving-the-robot)
own this evidence. There are no committed autonomous task trials, success-rate
measurements, or policy failure results.

## Inference-Systems Gate

**Planned.** The [serving benchmark phase](../ROADMAP.md#phase-7-benchmark-the-real-serving-path)
owns the future latency, queue, utilization, and serving-GPU evidence.
Production serving is not implemented or verified.

## Cost Record

**Planned.** Training cost belongs with the
[GPU environment phase](../ROADMAP.md#phase-3-create-the-reproducible-nvidia-environment),
and serving cost belongs with the
[serving benchmark phase](../ROADMAP.md#phase-7-benchmark-the-real-serving-path).
No committed cost record exists yet.

## Current Evidence State

| Capability | State | Authoritative evidence |
|---|---|---|
| Hardware calibration | verified | [Phase 1](../phases/01-hardware-calibration-teleoperation.md) |
| Camera-enabled teleoperation | verified | [Phase 1](../phases/01-hardware-calibration-teleoperation.md) |
| Dataset recording | active | [Phase 2](../phases/02-record-and-inspect-dataset.md) |
| GPU training | planned | [Roadmap Phase 4](../ROADMAP.md#phase-4-fine-tune-smolvla) |
| Autonomous evaluation | planned | [Roadmap Phases 5–6](../ROADMAP.md#phase-5-validate-the-checkpoint-before-moving-the-robot) |
| Production serving | planned | [Roadmap Phases 7–8](../ROADMAP.md#phase-7-benchmark-the-real-serving-path) |

## Simulation Alternative

Real hardware is optional in M3. If safe arm access is unavailable, follow the
[guide's hardware-free path](https://github.com/yanizhang-yz/software-to-robotics-inference/blob/main/docs/milestones/m3-real-arm-capstone.md#hardware-free-path)
and keep physical execution claims out of the evidence.
