# Architecture Diagram

```mermaid
flowchart TD
    A[Raw Excel data<br/>1068 ICSR rows] --> B[analysis.py<br/>load + clean + calculate]
    B --> C[results dict<br/>numbers only, no AI]
    C --> D[report_config.py<br/>section definitions: title, needed data, instruction]
    D --> E[report_generator.py<br/>generic build_section engine]
    C --> E
    E --> F{Section type?}
    F -->|static| G[Format numbers directly<br/>no AI call]
    F -->|ai / ai_with_table| H[Send small data packet<br/>+ instruction to Gemini]
    H --> I[AI writes narrative text<br/>grounded in given numbers only]
    G --> J[Human review<br/>approve / flag each section]
    I --> J
    J --> K[report_output.md<br/>final PADER report]
```

The main thing this shows: Gemini only ever gets reached through one
narrow path — a small packet of numbers I've already calculated, never
the raw dataset itself. Everything before that point (loading, cleaning,
calculating) is plain, deterministic Python — no AI involved at all.