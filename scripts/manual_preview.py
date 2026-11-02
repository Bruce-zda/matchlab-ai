"""Generate a fresh, non-archived matchup preview using the production models.

Usage:
  python scripts/manual_preview.py --league "Premier League" --home "Arsenal FC" --away "Chelsea FC" --kickoff-utc "2026-11-07T15:00:00Z"

The supplied kickoff must be independently verified; this tool does not verify fixtures.
Preview results are not published to the immutable official prediction ledger.
"""
import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from forward_validation import utc_time
from intelligence_report import build_intelligence_report
from scripts.collect_forward import LEAGUES, collect, json_native


def preview(league, home, away, kickoff_utc, now=None, fitted_cache=None):
    if league not in LEAGUES:
        raise ValueError("Unsupported league")
    if not home.strip() or not away.strip() or home.casefold().strip() == away.casefold().strip():
        raise ValueError("Home and away must be different nonempty teams")
    now = utc_time(now or dt.datetime.now(dt.timezone.utc))
    kickoff = utc_time(kickoff_utc)
    if not now < kickoff <= now + dt.timedelta(days=14):
        raise ValueError("Verified kickoff must be in the next 14 days")
    fixture = dict(league=league, home=home.strip(), away=away.strip(), kickoff_utc=kickoff.isoformat())
    version = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    records, audit = collect([fixture], [], now.isoformat(), version, preview=True, fitted_cache=fitted_cache)
    if len(records) != 4 or audit[0]["status"] != "preview":
        raise ValueError("Preview unavailable: " + str(audit))
    return {
        "kind": "on_demand_preview",
        "official_forward_archive": False,
        "fixture_verified": False,
        "model_version": version,
        "generated_at_utc": now.isoformat(),
        "warning": "Kickoff supplied by user, not independently verified. Fresh analysis; never a pre-existing archived forecast. No guarantee of accuracy.",
        "forecasts": records,
        "intelligence": build_intelligence_report(records),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", required=True, choices=sorted(LEAGUES))
    parser.add_argument("--home", required=True)
    parser.add_argument("--away", required=True)
    parser.add_argument("--kickoff-utc", required=True)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = preview(args.league, args.home, args.away, args.kickoff_utc)
    except (ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    output = json.dumps(result, indent=2, default=json_native) + "\n"
    if args.output:
        if args.output.resolve().is_relative_to((ROOT / "artifacts").resolve()):
            parser.error("Cannot write manual previews into official artifacts directory")
        args.output.write_text(output)
        print("Saved non-archived preview to", args.output)
    else:
        print(output)


if __name__ == "__main__":
    main()
