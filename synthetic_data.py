# synthetic_data.py
#
# A small, clearly-fake sample dataset used only for the deployed demo.
# This is NOT the real Bisoprolol dataset from the assessment - that one
# can't be redistributed publicly (see the original Data Usage Notice).
# This is a handful of made-up rows I wrote myself, matching the same
# column structure, just so the deployed app has something to run on
# without needing a real file upload.

import pandas as pd
import random

COLUMNS = [
    "safetyreportid", "receivedate", "occurcountry",
    "primarysource_reportercountry", "serious",
    "seriousnessdeath", "seriousnesslifethreatening",
    "seriousnesshospitalization", "seriousnessdisabling",
    "seriousnesscongenitalanomali", "seriousnessother",
    "fulfillexpeditecriteria", "patient_patientonsetage",
    "patient_patientonsetageunit", "patient_patientsex",
    "patient_reaction_reactionmeddrapt", "patient_reaction_reactionoutcome",
    "patient_drug_medicinalproduct", "primarysource_qualification",
]

COUNTRIES = ["united kingdom", "france", "germany", "italy", "canada"]
REACTIONS = ["Headache", "Nausea", "Dizziness", "Fatigue", "Hypotension", "Rash"]
OUTCOMES = ["recovered/resolved", "recovering/resolving", "not recovered/not resolved/ongoing", "unknown"]
QUALIFICATIONS = ["physician", "pharmacist", "other health professional", "consumer or non-health professional"]


def generate_demo_dataframe(n_rows=40, seed=42):
    """Builds a small, obviously-synthetic dataset with the same column
    structure the analysis code expects, purely for demo purposes."""
    random.seed(seed)
    rows = []

    for i in range(n_rows):
        is_serious = random.random() < 0.7
        rows.append({
            "safetyreportid": 90000000 + i,
            "receivedate": random.choice(["20250115", "20250320", "20250601", "20250910", "20251205"]),
            "occurcountry": random.choice(COUNTRIES),
            "primarysource_reportercountry": random.choice(COUNTRIES),
            "serious": "serious" if is_serious else "not serious",
            "seriousnessdeath": "yes" if is_serious and random.random() < 0.1 else "no",
            "seriousnesslifethreatening": "yes" if is_serious and random.random() < 0.15 else "no",
            "seriousnesshospitalization": "yes" if is_serious and random.random() < 0.4 else "no",
            "seriousnessdisabling": "no",
            "seriousnesscongenitalanomali": "no",
            "seriousnessother": "yes" if is_serious and random.random() < 0.5 else "no",
            "fulfillexpeditecriteria": "yes" if is_serious else "no",
            "patient_patientonsetage": random.randint(20, 90),
            "patient_patientonsetageunit": "year",
            "patient_patientsex": random.choice(["male", "female"]),
            "patient_reaction_reactionmeddrapt": random.choice(REACTIONS),
            "patient_reaction_reactionoutcome": random.choice(OUTCOMES),
            "patient_drug_medicinalproduct": "DEMO DRUG",
            "primarysource_qualification": random.choice(QUALIFICATIONS),
        })

    return pd.DataFrame(rows, columns=COLUMNS)