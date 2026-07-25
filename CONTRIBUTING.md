# Contributing

Contributions should keep this repository reproducible, safe around physical
hardware, and suitable for public collaboration.

## Hardware changes

Every hardware-facing change requires:

- a mockable boundary between hardware I/O and reusable logic;
- safety notes that identify hazards, limits, and a safe shutdown procedure;
- a test where possible, using mocks or deterministic fixtures when physical
  hardware is unavailable.

## Public repository rules

Do not commit:

- calibration files;
- access tokens or other secrets;
- concrete serial identifiers, including motor, camera, or USB device IDs;
- raw datasets.

Use documented placeholders or redacted examples for configuration and
diagnostic output. Run `uv run pytest -q` before opening a pull request.
