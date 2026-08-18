# analysis.py
#
# All the number crunching for the report happens in this file. Just
# pandas, nothing else - no AI touches any of this. report_generator.py
# calls into this later and only gets the numbers back, never the raw
# rows, which is basically the whole reason the final report can be
# trusted - every number in it traces back to something calculated
# right here.

# Quick rundown of the cleaning decisions I made (more detail in README):
#
# - receivedate comes in as a plain number (20250115) instead of an
#   actual date, so I convert it early on. Needed this for the trend
#   analysis later.
#
# - reactionoutcome sometimes has more than one outcome jammed into the
#   same cell, comma separated, since a case can have multiple
#   reactions. Had to split these apart before counting or the numbers
#   come out wrong (e.g. "recovered,recovered" gets treated as its own
#   weird category instead of two "recovered" outcomes).
#
# - occurcountry was blank for 7 rows. primarysource_reportercountry
#   has basically the same info (matches on 1067/1068 rows), so I used
#   that instead of just dropping these cases. Not making anything up
#   here, just pulling the real answer from a different column.
#
# - roughly a third of rows just say "eu" for country instead of a real
#   country name. Left it alone - no way for me to know which actual
#   country that is, and guessing isn't something I want to do.
#
# - age missing on 91 cases, sex missing on 30. Didn't fill these with
#   averages or anything like that - that's basically inventing a fact
#   about a real person that was never reported. These cases just get
#   skipped when I'm specifically doing age/sex breakdowns, but still
#   count everywhere else.
#
# - age unit isn't consistent - mostly "year" but a handful in
#   month/day/week (probably infants) plus 3 rows with some unit code
#   "800" that doesn't mean anything I recognize. Only used the "year"
#   rows for the age buckets - it's a tiny slice of the data (12 rows)
#   so converting the others wasn't worth the hassle.
#
# - double checked every row actually mentions Bisoprolol somewhere in
#   the drug field, and it does, all 1068. Most patients are on other
#   meds too at the same time which is normal, not a data issue.

import pandas as pd

# keeping all the column names as constants up top instead of typing
# the string out every time - mainly so a typo is easier to catch, and
# if this ever needs to point at a different file with slightly
# different column names I only have one place to change

CASE_ID_COL = "safetyreportid"
DATE_COL = "receivedate"
COUNTRY_COL = "occurcountry"
COUNTRY_BACKUP_COL = "primarysource_reportercountry"
SERIOUS_COL = "serious"
SERIOUSNESS_FLAG_COLS = [
    "seriousnessdeath",
    "seriousnesslifethreatening",
    "seriousnesshospitalization",
    "seriousnessdisabling",
    "seriousnesscongenitalanomali",
    "seriousnessother",
]
ALERT_COL = "fulfillexpeditecriteria"
AGE_COL = "patient_patientonsetage"
AGE_UNIT_COL = "patient_patientonsetageunit"
SEX_COL = "patient_patientsex"
REACTION_COL = "patient_reaction_reactionmeddrapt"
OUTCOME_COL = "patient_reaction_reactionoutcome"
DRUG_NAME_COL = "patient_drug_medicinalproduct"
REPORTER_TYPE_COL = "primarysource_qualification"

VALID_AGE_UNIT = "year"


def load_data(path):
    """Reads the excel file and applies the cleaning steps from the notes above."""
    df = pd.read_excel(path)

    df[DATE_COL] = pd.to_datetime(df[DATE_COL], format="%Y%m%d", errors="coerce")
    df[COUNTRY_COL] = df[COUNTRY_COL].fillna(df[COUNTRY_BACKUP_COL])

    return df


def get_case_level(df):
    """
    1068 rows but only 1024 actual cases - some cases show up more
    than once because they had more than one reaction. Anywhere I need
    to count CASES rather than reactions, I drop down to one row per
    case first, which is what this does.
    """
    return df.drop_duplicates(subset=CASE_ID_COL).copy()


def split_outcomes(df):
    """Breaks the comma-separated outcome strings into individual values so they count correctly."""
    return (
        df[OUTCOME_COL]
        .dropna()
        .astype(str)
        .str.split(",")
        .explode()
        .str.strip()
    )


def get_year_unit_cases(case_level):
    """Filters down to cases where age was actually reported in years."""
    return case_level[case_level[AGE_UNIT_COL] == VALID_AGE_UNIT]


# ------------------------------------------------------------------
# analysis functions, one per thing the report needs
# split these into separate functions instead of one big block mainly
# so each piece is easy to check on its own
# ------------------------------------------------------------------

def analyze_reporting_period(df):
    return {
        "product": "Bisoprolol",
        "start_date": df[DATE_COL].min().strftime("%Y-%m-%d"),
        "end_date": df[DATE_COL].max().strftime("%Y-%m-%d"),
        "total_rows_in_source_file": len(df),
    }


def analyze_case_counts(case_level):
    total = len(case_level)
    counts = case_level[SERIOUS_COL].value_counts()
    serious = int(counts.get("serious", 0))
    non_serious = int(counts.get("not serious", 0))

    return {
        "total_cases": total,
        "serious_cases": serious,
        "serious_pct": round(serious / total * 100, 1) if total else 0,
        "non_serious_cases": non_serious,
        "non_serious_pct": round(non_serious / total * 100, 1) if total else 0,
    }


def analyze_seriousness_breakdown(case_level):
    # yes/no flags, and a case can hit more than one at once (e.g.
    # hospitalization AND death both "yes" on the same case)
    return {col: int((case_level[col] == "yes").sum()) for col in SERIOUSNESS_FLAG_COLS}


def analyze_demographics(case_level):
    known_sex = case_level[SEX_COL].dropna()

    year_unit_cases = get_year_unit_cases(case_level)
    known_age = year_unit_cases[AGE_COL].dropna()

    bins = [0, 18, 40, 65, 85, 150]
    labels = ["0-17", "18-39", "40-64", "65-84", "85+"]
    age_groups = pd.cut(known_age, bins=bins, labels=labels, right=False)

    non_year_unit_count = len(case_level) - len(year_unit_cases)
    year_unit_but_missing_age = len(year_unit_cases) - len(known_age)

    return {
        "age_known_and_used_count": len(known_age),
        "age_excluded_non_year_unit_count": non_year_unit_count,
        "age_excluded_missing_value_count": year_unit_but_missing_age,
        "age_group_counts": {str(k): int(v) for k, v in age_groups.value_counts().sort_index().items()},
        "sex_known_count": len(known_sex),
        "sex_missing_count": int(case_level[SEX_COL].isna().sum()),
        "sex_counts": known_sex.value_counts().to_dict(),
    }


def analyze_country(case_level, top_n=10):
    known = case_level[COUNTRY_COL].dropna()
    return {
        "country_known_count": len(known),
        "country_still_missing_count": int(case_level[COUNTRY_COL].isna().sum()),
        "note": "'eu' shows up on its own as a value - it's a regional code, not a country, and I left it as-is rather than guess which country it actually is",
        "top_countries": known.value_counts().head(top_n).to_dict(),
    }


def analyze_reactions(df, case_level, top_n=10):
    # row level on purpose here, not case level - a single case can
    # have more than one distinct reaction
    all_reactions = df[REACTION_COL].dropna()

    serious_ids = set(case_level.loc[case_level[SERIOUS_COL] == "serious", CASE_ID_COL])
    serious_rows = df[df[CASE_ID_COL].isin(serious_ids)]

    return {
        "total_reaction_entries": len(all_reactions),
        "unique_reaction_terms": int(all_reactions.nunique()),
        "top_reactions": all_reactions.value_counts().head(top_n).to_dict(),
        "top_serious_reactions": serious_rows[REACTION_COL].dropna().value_counts().head(top_n).to_dict(),
    }


def analyze_outcomes(df):
    exploded = split_outcomes(df)
    return {
        "total_outcome_entries": len(exploded),
        "outcome_counts": exploded.value_counts().to_dict(),
    }


def analyze_trend_over_time(case_level):
    # grouping by month so the trend section can talk about whether
    # case volume went up or down over the year
    monthly = (
        case_level.dropna(subset=[DATE_COL])
        .set_index(DATE_COL)
        .resample("MS")[CASE_ID_COL]
        .count()
    )
    return {m.strftime("%Y-%m"): int(c) for m, c in monthly.items()}


def analyze_15day_alerts(case_level):
    alert_cases = case_level[case_level[ALERT_COL] == "yes"]
    return {
        "alert_case_count": len(alert_cases),
        "alert_serious_count": int((alert_cases[SERIOUS_COL] == "serious").sum()),
        "alert_death_count": int((alert_cases["seriousnessdeath"] == "yes").sum()),
    }


def analyze_reporter_type(case_level):
    return {
        "known_count": int(case_level[REPORTER_TYPE_COL].notna().sum()),
        "counts": case_level[REPORTER_TYPE_COL].value_counts(dropna=False).to_dict(),
    }


def run_full_analysis(path):
    """Runs every analysis function and bundles the results into one dict."""
    df = load_data(path)
    case_level = get_case_level(df)

    return {
        "reporting_period": analyze_reporting_period(df),
        "case_counts": analyze_case_counts(case_level),
        "seriousness_breakdown": analyze_seriousness_breakdown(case_level),
        "demographics": analyze_demographics(case_level),
        "country": analyze_country(case_level),
        "reactions": analyze_reactions(df, case_level),
        "outcomes": analyze_outcomes(df),
        "trend": analyze_trend_over_time(case_level),
        "alerts_15day": analyze_15day_alerts(case_level),
        "reporter_type": analyze_reporter_type(case_level),
    }


# so I can just run "uv run analysis.py" on its own to sanity check the
# numbers before plugging this into the report generator
if __name__ == "__main__":
    import json

    results = run_full_analysis("data/Bisoprolol_icsr_sample_1068rows.xlsx")
    print(json.dumps(results, indent=2, default=str))