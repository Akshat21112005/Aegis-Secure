# AEGIS Secure – Runtime Specialist Documentation

Complete architectural documentation for the Runtime Specialist, structured in five parts to mirror the Infrastructure Specialist documentation series.

| Part | Title | File |
|------|-------|------|
| 1 | Vision, Motivation & Philosophy | [PART_1_VISION_MOTIVATION_PHILOSOPHY.md](./PART_1_VISION_MOTIVATION_PHILOSOPHY.md) |
| 2 | Complete Runtime Collector Architecture | [PART_2_COLLECTOR_ARCHITECTURE.md](./PART_2_COLLECTOR_ARCHITECTURE.md) |
| 3 | Intelligence Layer | [PART_3_INTELLIGENCE_LAYER.md](./PART_3_INTELLIGENCE_LAYER.md) |
| 4 | Engineering Journey | [PART_4_ENGINEERING_JOURNEY.md](./PART_4_ENGINEERING_JOURNEY.md) |
| 5 | Final Runtime Architecture & Research Contribution | [PART_5_FINAL_ARCHITECTURE.md](./PART_5_FINAL_ARCHITECTURE.md) |

## Frozen Runtime File Tree

```text
runtime/

│
├── behavior/
│   │
│   ├── network.py
│   ├── javascript_runtime.py
│   ├── forms.py
│   ├── storage.py
│   └── permissions.py
│
├── browser.py
├── preprocessing.py
├── evidence_builder.py
├── prompt.md
├── predictor.py
├── evaluate.py
│
└── model/
    │
    ├── base/
    └── tokenizer/
```

Collectors observe. The model reasons. Browser lifecycle lives in `browser.py`. JavaScript instrumentation stays inside `javascript_runtime.py`. Network request, response, redirect, and download events remain merged in `network.py`.
