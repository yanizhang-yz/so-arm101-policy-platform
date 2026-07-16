# SO-101 Policy Platform

A learning-first, production-shaped platform for serving a robot policy to an
SO-101 arm.

The first implementation runs locally on macOS with Python, FastAPI, PyTorch,
and CPU or MPS. Later milestones preserve the same system boundaries while
adding a real LeRobot adapter, an NVIDIA cloud GPU, gRPC, C++/ROS 2, a Rust
gateway, and TensorRT.

The approved design is documented in
[`docs/superpowers/specs/2026-07-16-so101-policy-platform-design.md`](docs/superpowers/specs/2026-07-16-so101-policy-platform-design.md).

Status: design review before implementation planning.
