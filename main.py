# main.py
#
# Runs the whole system end to end: load data -> analyze -> generate
# report using the config-driven engine -> save it as a file.
#
# To point this at a different report type in the future, you'd just
# import a different config (e.g. psur_config.py instead of report_config.py)
# - nothing else here would need to change.

from analysis import run_full_analysis
from report_generator import generate_full_report
from report_config import PADER_SECTIONS

DATA_PATH = "data/Bisoprolol_icsr_sample_1068rows.xlsx"
OUTPUT_PATH = "report_output.md"


def main():
    print("Step 1: Running analysis on the dataset...")
    results = run_full_analysis(DATA_PATH)
    print(f"  Done - found {results['case_counts']['total_cases']} cases.")

    print("\nStep 2: Generating the report (you'll be asked to approve each section)...")
    report = generate_full_report(results, PADER_SECTIONS, auto_approve=False)

    print(f"\nStep 3: Saving report to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print("Done! Report saved.")


if __name__ == "__main__":
    main()