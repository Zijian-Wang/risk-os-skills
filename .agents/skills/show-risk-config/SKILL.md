---
name: show-risk-config
description: Read config/defaults.json from risk-os-skills and render concise risk configuration tables (trade limits, exits, thresholds, market profiles).
---
# Show Risk Config

Resolve repo root via `git rev-parse --show-toplevel` (fallback: current working directory).

## Workflow
1. Read `config/defaults.json`.
2. Render human-readable markdown sections:
   - Trade Risk Limits
   - Exit Level Parameters
   - Data Thresholds
   - Market Profiles
3. Keep values exact from JSON (no guessing).

## Output
- Include source path.
- Include short note: edit `config/defaults.json` to change defaults.
