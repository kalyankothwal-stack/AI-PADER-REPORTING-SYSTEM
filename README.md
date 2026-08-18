# GenAR Challenge — PADER Report Generator (Bisoprolol)

## What this is

A system that takes a real-format drug safety dataset (1,068 ICSR rows
for Bisoprolol) and turns it into a structured, evidence-based PADER
report. The rule I stuck to the whole way through: the report can only
say what the data actually supports — no invented numbers, no guessed
patient details, no conclusions the data doesn't back up.

## How to run it

```bash
uv sync
uv run main.py
```

You'll get asked to approve each section as it's generated (Enter to
approve, `n` to flag it). The final report gets saved to
`report_output.md`.

Needs a free Gemini API key in a `.env` file:

GEMINI_API_KEY=your_key_here


Get one at https://aistudio.google.com/apikey — free tier, no billing needed.

## Web app

Same pipeline, also available as a small web interface using Streamlit
(`app.py`). None of the actual logic changes — `analysis.py`,
`report_generator.py`, and `report_config.py` stay exactly the same,
`app.py` just calls those same functions from a browser instead of a
terminal, with buttons instead of y/n prompts.

One thing worth noting about the data: the real assessment dataset
can't be shared publicly (the exercise's Data Usage Notice covers that),
so the web app runs on a small synthetic dataset instead
(`synthetic_data.py`) — a handful of rows I made up myself, matching the
same column structure. The pipeline behind it is identical either way.

Run it locally with:
```bash
uv run streamlit run app.py
```

Live demo: [add deployed URL here once deployed]

## Architecture

Raw data (Excel)
|
v
analysis.py — pure Python/pandas, cleans the data and calculates
| every number the report needs. No AI touches this part.
v
results dict — just numbers (total cases, top reactions, trends, etc.)
|
v
report_config.py — describes each section as data: title, what
| numbers it needs, what to ask the AI to write.
v
report_generator.py — generic engine that reads the config and builds
| each section, either formatting numbers directly
| or sending a small packet + instruction to the AI.
| The AI never sees the raw dataset, only the
| numbers relevant to whichever section it's on.
v
Human review — approve/flag each section (terminal in main.py, buttons in app.py)
v
report_output.md — the final report


See `architecture.md` for a diagram of the same flow.

## Files in this project

- `analysis.py` — loads and cleans the data, does every calculation the report needs
- `report_config.py` — the section definitions (title, needed data, what to ask the AI)
- `report_generator.py` — the engine that builds sections from that config
- `main.py` — runs the whole thing from the terminal
- `app.py` — same pipeline, as a Streamlit web app
- `synthetic_data.py` — builds the fake demo dataset the web app runs on
- `report_output.md` — an actual generated report from the real assessment dataset
- `architecture.md` — diagram of the flow above

## Why the AI/code split is where it is

**Python (`analysis.py`) handles:**
- Loading and cleaning the data
- Every number that ends up in the report — case counts, seriousness
  splits, age/sex/country breakdowns, reaction counts, outcomes,
  monthly trends, 15-day alert counts

**The AI only handles:**
- Turning an already-calculated set of numbers into readable sentences,
  for the sections that need actual prose (Narrative Summary, Reaction
  Analysis, Alerts, Trends)

I split it this way on purpose. An LLM writes clear prose from facts you
give it, but I wouldn't trust it to count or calculate anything on its
own — and the challenge itself points this out directly (does the LLM
need to compute this, or can Python already give an exact answer). So
every number gets computed once, in one place, and the AI's only job is
converting numbers I've already verified into English.

## An actual prompt from the system (Reaction Analysis section)

The AI never sees the raw dataset — here's the real packet sent for one
section, built from `report_config.py`:

Approved numbers:
{'total_reaction_entries': 1068, 'unique_reaction_terms': 882,
'top_reactions': {'Acute kidney injury': 22, 'Drug ineffective': 12, ...},
'top_serious_reactions': {'Acute kidney injury': 22, ...}}

Task: Write a short paragraph (3-5 sentences) describing the reaction
pattern - mention the most common reactions and whether the same
reactions dominate the serious cases too. Stick strictly to these
numbers.


Every section shares this same base instruction, so the grounding rules
apply no matter which section is being written:

You are writing one section of a drug safety report (a PADER-style report).

Rules you must follow:

Only use the numbers given to you in the data below. Never calculate
your own numbers, never estimate, never round differently than what's given.
Do not draw medical conclusions. Just describe what the data shows.
Do not say a causal relationship exists between the drug and any
reaction unless the data explicitly says so.
Keep the tone neutral, factual, and professional.
If a number is described as "unknown" or "missing", mention that
honestly instead of ignoring it.
Do not invent patient stories, quotes, or details that aren't in the
data given to you.

## How grounding actually holds up

Every sentence in the report traces back to a value in the `results`
dict that `analysis.py` produces. The AI never sees the raw Excel file
— just a small, pre-approved slice of numbers for whatever section it's
writing. That means it physically can't invent a statistic, since it
never has access to anything beyond numbers I already calculated and
checked myself.

I confirmed this by going through the generated report line by line
against the `analysis.py` JSON output — every number matched.

## Data cleaning decisions

1. **`receivedate`** came in as a plain int (`20250115`) — converted it
   to a real datetime, otherwise date math for the trend section isn't
   possible.

2. **`patient_reaction_reactionoutcome`** sometimes has more than one
   outcome jammed into a single cell, comma separated, since a case can
   have multiple reactions. Split these before counting — otherwise
   `"recovered,recovered"` gets treated as a totally separate category
   from plain `"recovered"`.

3. **7 rows had no `occurcountry`.** Filled those from
   `primarysource_reportercountry` instead — the two fields agree on
   1,067 of 1,068 rows, so this isn't invented data, just pulling the
   real answer from a second column that already had it.

4. **353 cases (33%) just say `"eu"`** instead of an actual country.
   Left it alone and reported it honestly as its own category — no way
   to know which specific EU country that is, and guessing would break
   the whole "only what the data supports" rule.

5. **Age missing on 91 cases, sex missing on 30.** Didn't impute either
   one. Unlike country, there's no second field with the real answer
   here, so anything I filled in would just be made up. These cases get
   skipped only for the age/sex breakdowns specifically — they still
   count everywhere else.

6. **Age unit isn't always "year"** — a few are month/day/week (likely
   infants), and 3 rows have some unit code ("800") that doesn't match
   anything recognizable. Age-bucket analysis only uses the 938 cases
   with a confirmed "year" unit; the other ~86 are excluded from that
   one chart, not from the rest of the report — converting them wasn't
   worth it for such a small slice of the data.

7. **Confirmed all 1,068 rows actually contain Bisoprolol** somewhere
   in the drug field (checked as a substring match, since most rows
   list several drugs together — normal, not a data issue).

## Human review

Before anything gets written to the final report, each section is
shown and has to be approved (or flagged). Flagged sections get marked
`[FLAGGED FOR REVIEW]` in the output rather than silently passing
through as final. `main.py` does this as a terminal y/n prompt;
`app.py` does it with Approve/Flag buttons. Same underlying idea in
both — nothing becomes final without a human actually looking at it.

## How I'd check this at scale (1,000 reports, not one)

Right now I'm just eyeballing one report by hand. At real scale I'd want:
- **An automated grounding check** — parse every number the AI writes
  and diff it against the `results` dict for that section, flag
  anything that doesn't match.
- **A consistency check across runs** — regenerate the same section a
  few times and confirm the numbers stay identical (they should, since
  they're calculated once — only the wording should vary).
- **A chronology check on the trend text specifically** — make sure
  month references come out in the right order (see the limitation
  below, I actually caught this going wrong once).
- **Random spot-checks** — a reviewer samples some percentage of
  generated reports each run, similar to the approve/flag step but at
  scale instead of every single section.

## Known limitations

- **The AI sometimes describes trend data out of order**, even though
  the numbers themselves are always right. I caught one instance where
  it mentioned August before July's peak, when July actually comes
  first. Fixable with a stricter prompt or by pre-sorting the trend
  data before it's sent over.
- **No individual "Case Presentation" write-ups** for the top
  reactions, unlike the sample reference report — not one of the 8
  actually required sections, so I skipped it given the time I had.
- **Case Index/Listing is a pointer, not a full table** — with 1,024
  cases, embedding the whole case-level listing directly in the
  markdown wasn't really practical; a real version would export it as
  a separate CSV.
- **"eu" as a country stays undisaggregated** — intentional, not a bug
  (see cleaning decision #4), but it does mean about a third of cases
  aren't tied to a specific country.
- **Wording shifts between runs** even when the data doesn't, since the
  AI writes with some built-in randomness. The facts stay the same
  (checked against `analysis.py`'s output) — only the phrasing moves.
- **The web app only runs on the built-in synthetic data**, not
  arbitrary uploads — `analysis.py` expects specific ICSR column names,
  so a generic "upload anything" option would just crash on a mismatch
  instead of failing gracefully. A real version would validate the
  uploaded columns first and give a clear error instead of assuming
  the file matches.

## Version 1 — what's actually built vs. what's still missing

**What's built:** `report_generator.py` no longer has a separate
hardcoded function per section. `report_config.py` describes each
section as plain data — title, what numbers it needs, what to ask the
AI — and `report_generator.py` has one generic function that reads that
config and builds whatever section it's told to. To support a new
report type down the line, I'd write a new config file with different
sections — `report_generator.py` and `analysis.py` wouldn't need to
change for the parts they already cover. I also built the Streamlit app
on top of these exact same functions, which is a decent proof that the
core logic works from more than one entry point without modification.

**What would still need work for an actually new report type:**
- `analysis.py`'s functions are still built around what a PADER
  specifically needs — a different report type would likely need new
  analysis functions, though some (case counts, demographics) would
  probably carry over fine.
- The config declares what each section needs, but there's no check
  that the data actually exists in `results` before it runs — a
  misconfigured report type would just crash mid-generation instead of
  failing with a clear error. I'd add that check.
- No evidence tracing (click a sentence, see exactly where the number
  came from) — right now grounding is something I verify manually by
  comparing text to numbers, not something built into the system.

## Models used

Gemini 3.5 Flash Lite (free tier) for the narrative writing. No model
does any of the actual analysis — that's fully deterministic
Python/pandas in `analysis.py`.