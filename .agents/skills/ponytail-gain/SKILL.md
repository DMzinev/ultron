---
name: ponytail-gain
description: >
  Show ponytail's measured impact as a compact scoreboard: less code, less
  cost, more speed, from the benchmark medians. One-shot display, not a
  persistent mode, and not a per-repo number. Trigger: /ponytail-gain,
  "ponytail gain", "what does ponytail save", "show ponytail impact",
  "ponytail scoreboard".
license: MIT
---

# Ponytail Gain Scoreboard

Display this scoreboard when invoked. One-shot: do NOT change mode, write flag files, or persist anything.

The figures are the published benchmark medians (5 tasks, 3 models). Source: `DietrichGebert/ponytail` README.

```
  ponytail gain                     benchmark median · 5 tasks · 3 models

  Lines of code   no-skill |████████████████████████████████████████| 100%
                  ponytail |██████████████████                      | 46%    (-54%)

  Tokens used     no-skill |████████████████████████████████████████| 100%
                  ponytail |███████████████████████████████         | 78%    (-22%)

  API Cost        no-skill |████████████████████████████████████████| 100%
                  ponytail |████████████████████████████████        | 80%    (-20%)

  Duration        no-skill |████████████████████████████████████████| 100%
                  ponytail |█████████████████████████████           | 73%    (-27%)

  Safety Score    no-skill |████████████████████████████████████████| 100%
                  ponytail |████████████████████████████████████████| 100% (safe)
```
