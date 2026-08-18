# report_generator.py
#
# This is version 1 of this file - it used to have one hardcoded
# function per report section, but now it's one generic engine that
# reads section definitions from report_config.py and builds whatever
# that config tells it to. If I ever need a different report type, I'd
# just write a new config file with different sections - this file
# shouldn't need to change at all.
#
# Same rule as before applies here: the AI never gets handed the raw
# dataset, only the small slice of already-calculated numbers each
# section actually needs. That's what keeps everything grounded.

import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-3.5-flash-lite"

SYSTEM_PROMPT = """You are writing one section of a drug safety report (a PADER-style report).

Rules you must follow:
- Only use the numbers given to you in the data below. Never calculate your own numbers, never estimate, never round differently than what's given.
- Do not draw medical conclusions (like "this proves the drug is unsafe"). Just describe what the data shows.
- Do not say a causal relationship exists between the drug and any reaction unless the data explicitly says so.
- Keep the tone neutral, factual, and professional - like a regulatory document, not a blog post.
- If a number is described as "unknown" or "missing", mention that honestly instead of ignoring it.
- Do not invent patient stories, quotes, or details that aren't in the data given to you.
- Keep it concise - a few sentences to a short paragraph, not a long essay."""


def ask_ai(system_prompt, user_prompt):
    full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
    response = client.models.generate_content(model=MODEL, contents=full_prompt)
    return response.text


def get_nested(results, dotted_path):
    """Looks up something like 'reactions.top_reactions' inside the results dict."""
    value = results
    for part in dotted_path.split("."):
        value = value[part]
    return value


def build_markdown_table(data_dict, headers):
    header_row = f"| {headers[0]} | {headers[1]} |"
    divider_row = "|---|---|"
    rows = "\n".join(f"| {k} | {v} |" for k, v in data_dict.items())
    return f"{header_row}\n{divider_row}\n{rows}"


# ------------------------------------------------------------------
# a few sections don't need the AI at all, just formatting the numbers
# straight into markdown. each one takes the full results dict and
# returns the body text (the engine adds the ## title on top separately)
# ------------------------------------------------------------------
def render_reporting_period(results):
    rp = results["reporting_period"]
    return f"""- **Product:** {rp['product']}
- **Reporting Period:** {rp['start_date']} to {rp['end_date']}
- **Report Type:** PADER (simplified, for this exercise)
- **Total case reports in source data:** {rp['total_rows_in_source_file']} rows ({results['case_counts']['total_cases']} unique cases)"""


def render_case_summary(results):
    cc = results["case_counts"]
    demo = results["demographics"]

    age_table = "\n".join(f"| {k} | {v} |" for k, v in demo["age_group_counts"].items())
    country_table = "\n".join(f"| {k} | {v} |" for k, v in list(results["country"]["top_countries"].items())[:5])

    return f"""| Metric | Count |
|---|---|
| Total cases | {cc['total_cases']} |
| Serious | {cc['serious_cases']} ({cc['serious_pct']}%) |
| Non-serious | {cc['non_serious_cases']} ({cc['non_serious_pct']}%) |

**Age breakdown** (known for {demo['age_known_and_used_count']} of {cc['total_cases']} cases):

| Age group | Count |
|---|---|
{age_table}

**Sex breakdown** (known for {demo['sex_known_count']} of {cc['total_cases']} cases): female {demo['sex_counts'].get('female', 0)}, male {demo['sex_counts'].get('male', 0)}

**Top reporting countries:**

| Country | Count |
|---|---|
{country_table}"""


def render_history_of_actions(results):
    return 'No history-of-actions data (e.g. labeling changes, regulatory communications, safety studies) was supplied for this exercise. This section is intentionally left as "none reported" rather than inferring or inventing any actions.'


def render_case_index(results):
    cc = results["case_counts"]
    return f"This report covers {cc['total_cases']} individual cases. A full case-level listing (case ID, reaction, seriousness, date, country, outcome) can be generated directly from the cleaned dataset in `analysis.py` - not duplicated here to keep this report readable."


STATIC_RENDERERS = {
    "reporting_period": render_reporting_period,
    "case_summary": render_case_summary,
    "history_of_actions": render_history_of_actions,
    "case_index": render_case_index,
}


# ------------------------------------------------------------------
# the actual generic engine - builds one section based on whatever its
# config entry says. this is the piece that makes the whole thing
# reusable, since it doesn't know or care what report type it's
# working on, it just does what the config tells it
# ------------------------------------------------------------------
def build_section(section_def, results):
    section_type = section_def["type"]

    if section_type == "static":
        body = STATIC_RENDERERS[section_def["renderer"]](results)

    elif section_type == "ai":
        needed_data = {key: results[key] for key in section_def["needs"]}
        packet = f"Approved numbers:\n{needed_data}\n\nTask: {section_def['instruction']}"
        body = ask_ai(SYSTEM_PROMPT, packet)

    elif section_type == "ai_with_table":
        needed_data = {key: results[key] for key in section_def["needs"]}
        packet = f"Approved numbers:\n{needed_data}\n\nTask: {section_def['instruction']}"
        narrative = ask_ai(SYSTEM_PROMPT, packet)

        table_data = get_nested(results, section_def["table_from"])
        table = build_markdown_table(table_data, section_def["table_headers"])
        body = f"{narrative}\n\n**Top 10 {section_def['table_headers'][0].lower()}s:**\n\n{table}"

    else:
        raise ValueError(f"Unknown section type: {section_type}")

    return f"## {section_def['title']}\n\n{body}\n"


# ------------------------------------------------------------------
# loops through every section in the config, builds each one, and
# handles the approve/flag step along the way - same idea as before,
# nothing gets marked final without me looking at it first
# ------------------------------------------------------------------
def generate_full_report(results, section_config, auto_approve=False):
    built_sections = {}
    for section_def in section_config:
        content = build_section(section_def, results)

        if not auto_approve:
            print("\n" + "=" * 60)
            print(content)
            print("=" * 60)
            choice = input(f"Approve section '{section_def['key']}'? (y/n, default y): ").strip().lower()
            if choice == "n":
                content = f"[FLAGGED FOR REVIEW]\n\n{content}"

        built_sections[section_def["key"]] = content

    title = f"# Periodic Adverse Drug Experience Report (PADER)\n## {results['reporting_period']['product']}\n\n"
    return title + "\n".join(built_sections.values())