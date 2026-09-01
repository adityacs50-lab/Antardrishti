"""prahari command line: database setup and demo seeding.

    python -m prahari.cli seed --limit 800
    python -m prahari.cli reset
    python -m prahari.cli stats
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import func, select

from prahari.api.service import persist
from prahari.core.config import get_settings
from prahari.db.models import Base, Report, Verdict
from prahari.db.session import create_all, get_engine, session_scope

#: Sites the synthetic corpus uses. Reports carry the site inside their text,
#: so seeding recovers it by matching against this list.
KNOWN_SITES: tuple[str, ...] = (
    "Naoholia", "Baghjan", "Duliajan", "Moran", "Kusijan",
    "Dikom", "Jorajan", "Madhuban", "Tengakhat", "Hebeda",
)


def _site_of(text: str, rng: random.Random) -> str:
    lowered = text.lower()
    for site in KNOWN_SITES:
        if site.lower() in lowered:
            return site
    return rng.choice(KNOWN_SITES)


def _activity_of(record: dict) -> str:
    from prahari.data.scenarios import SCENARIOS_BY_KEY

    key = record.get("meta", {}).get("scenario_key", "")
    scenario = SCENARIOS_BY_KEY.get(key)
    return scenario.activity if scenario else "(unspecified)"


def seed(
    limit: int | None,
    corpus: Path | None,
    seed_value: int,
    spread_days: int,
    cluster: bool = True,
) -> int:
    """Load the synthetic corpus so the demo has data on first run.

    Dates are spread across a recent window rather than taken from the corpus,
    because the accumulation index is a rolling-window measure and needs recent
    history to show anything on day one.

    CLUSTERING (`--cluster`, on by default). Each kind of work is given a home
    site and most of its reports land there inside a tighter date window. This
    is not cosmetic dressing for the demo: it is what real fields look like.
    The same crew on the same installation makes the same mistake repeatedly,
    which is precisely the pattern the accumulation index exists to surface. A
    uniform random scatter would have no repeats to find, and would make the
    index look useless against data that does not resemble reality.

    Pass --no-cluster to seed a flat random scatter instead.
    """
    settings = get_settings()
    path = corpus or settings.corpus_path
    if not path.exists():
        print(
            f"corpus not found at {path}\n"
            "Generate it first:  python -m prahari.data.generator --n 3000 --seed 42",
            file=sys.stderr,
        )
        return 1

    create_all()
    rng = random.Random(seed_value)
    today = date.today()
    home_site: dict[str, str] = {}
    home_window: dict[str, int] = {}

    with session_scope() as db:
        existing = db.scalar(select(func.count()).select_from(Report)) or 0
        if existing:
            print(f"database already holds {existing} reports; use `reset` first.")
            return 1

        counts: Counter = Counter()
        n = 0
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if limit is not None and n >= limit:
                    break
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                text = rec.get("text", "").strip()
                if not text:
                    continue
                scenario_key = rec.get("meta", {}).get("scenario_key", "")
                if cluster and scenario_key:
                    if scenario_key not in home_site:
                        home_site[scenario_key] = rng.choice(KNOWN_SITES)
                        home_window[scenario_key] = rng.randint(20, max(21, spread_days // 2))
                    if rng.random() < 0.62:
                        site = home_site[scenario_key]
                        centre = home_window[scenario_key]
                        report_date = today - timedelta(
                            days=max(0, min(spread_days, centre + rng.randint(-45, 45)))
                        )
                    else:
                        site = _site_of(text, rng)
                        report_date = today - timedelta(days=rng.randint(0, spread_days))
                else:
                    site = _site_of(text, rng)
                    report_date = today - timedelta(days=rng.randint(0, spread_days))
                report = persist(
                    db,
                    text=text,
                    site=site,
                    report_date=report_date,
                    reporter_role=rec.get("reporter_role") or "Safety Officer",
                    activity=_activity_of(rec),
                    report_uid=rec.get("report_id"),
                    source="seed",
                    commit=False,
                )
                db.flush()
                counts[report.verdict.classification] += 1
                n += 1
                if n % 250 == 0:
                    print(f"  seeded {n}...")

    print(f"\nSeeded {n} reports from {path.name}")
    for cls, c in counts.most_common():
        print(f"  {cls:28s} {c:5d}  {100 * c / n:5.1f}%")

    # Printed here rather than by a second `prahari.cli banner` process: the
    # import chain costs ~3s, which is a third of the reset budget.
    from prahari.core.banner import print_banner

    print_banner()
    return 0


def reset() -> int:
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("database reset.")
    return 0


def stats() -> int:
    create_all()
    with session_scope() as db:
        total = db.scalar(select(func.count()).select_from(Report)) or 0
        print(f"reports: {total}")
        if not total:
            return 0
        rows = db.execute(
            select(Verdict.classification, func.count()).group_by(Verdict.classification)
        ).all()
        for cls, c in sorted(rows, key=lambda r: -r[1]):
            print(f"  {cls:28s} {c:5d}")
        sites = db.execute(select(Report.site, func.count()).group_by(Report.site)).all()
        print(f"sites: {len(sites)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m prahari.cli", description="prahari admin CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_seed = sub.add_parser("seed", help="load the synthetic corpus into the database")
    p_seed.add_argument("--limit", type=int, default=800, help="max records (default 800)")
    p_seed.add_argument("--corpus", type=Path, default=None)
    p_seed.add_argument("--seed", type=int, default=42)
    p_seed.add_argument("--spread-days", type=int, default=240, help="date window to spread over")
    p_seed.add_argument(
        "--no-cluster",
        dest="cluster",
        action="store_false",
        help="seed a flat random scatter instead of realistic per-site repeat clusters",
    )
    p_seed.set_defaults(cluster=True)

    sub.add_parser("reset", help="drop and recreate all tables")
    sub.add_parser("stats", help="show what is in the database")
    sub.add_parser("banner", help="print the startup banner and exit")
    sub.add_parser("init", help="create tables without seeding")

    args = parser.parse_args(argv)
    if args.command in ("stats", "banner"):
        from prahari.core.banner import print_banner

        create_all()
        print_banner()
        if args.command == "banner":
            return 0
    if args.command == "seed":
        return seed(args.limit, args.corpus, args.seed, args.spread_days, args.cluster)
    if args.command == "reset":
        return reset()
    if args.command == "stats":
        return stats()
    create_all()
    print("tables created.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
