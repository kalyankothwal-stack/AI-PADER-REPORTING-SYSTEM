# report_config.py
#
# This is the version 1 piece I mentioned - instead of each section
# having its prompt baked directly into a function, all the section
# definitions live here as plain data: title, what data it needs, what
# to ask the AI for. report_generator.py just reads through this list
# and builds whatever it's told to.
#
# If I needed to support a different report type later (say a PSUR
# instead of a PADER), I'd write a new file like this one with
# different sections - report_generator.py wouldn't need any changes.
#
# "type" tells the engine how to handle each section:
# - "static"        -> just formats the numbers directly, no AI involved
# - "ai"             -> sends a small data packet + instruction to the AI, gets text back
# - "ai_with_table"  -> same as "ai" but also appends a markdown table built from the results

PADER_SECTIONS = [
    {
        "key": "reporting_period",
        "title": "Reporting Period",
        "type": "static",
        "renderer": "reporting_period",
    },
    {
        "key": "narrative_summary",
        "title": "Narrative Summary and Analysis",
        "type": "ai",
        "needs": ["case_counts", "demographics", "reactions", "reporting_period"],
        "instruction": (
            "Write a short narrative summary paragraph (4-6 sentences) covering "
            "the case volume, seriousness split, and the most notable reactions. "
            "Stick strictly to the numbers given."
        ),
    },
    {
        "key": "case_summary",
        "title": "Summary Analysis of Cases",
        "type": "static",
        "renderer": "case_summary",
    },
    {
        "key": "reaction_analysis",
        "title": "Reaction / Adverse Event Analysis",
        "type": "ai_with_table",
        "needs": ["reactions"],
        "instruction": (
            "Write a short paragraph (3-5 sentences) describing the reaction pattern - "
            "mention the most common reactions and whether the same reactions dominate "
            "the serious cases too. Stick strictly to these numbers."
        ),
        "table_from": "reactions.top_reactions",
        "table_headers": ["Reaction", "Count"],
    },
    {
        "key": "alerts",
        "title": "Serious Cases / 15-Day Alerts",
        "type": "ai",
        "needs": ["alerts_15day"],
        "instruction": "Write 2-3 sentences summarizing the 15-day alert cases using only these numbers.",
    },
    {
        "key": "trends",
        "title": "Trends and Important Observations",
        "type": "ai",
        "needs": ["trend"],
        "instruction": (
            "Write 2-4 sentences describing the case volume trend over the reporting "
            "period. Just describe what happened month to month (increases, decreases, "
            "the peak) - do NOT call anything a 'safety signal' or draw a conclusion "
            "about why it happened."
        ),
    },
    {
        "key": "history_of_actions",
        "title": "History of Actions",
        "type": "static",
        "renderer": "history_of_actions",
    },
    {
        "key": "case_index",
        "title": "Case Index / Listing",
        "type": "static",
        "renderer": "case_index",
    },
]