import argparse
import asyncio
import logging
from collections.abc import Sequence
from pathlib import Path

from sunbeam_valet.config import load_config
from sunbeam_valet.harness import Harness


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Sunbeam Valet triage harness.")
    parser.add_argument(
        "--config",
        default="config/harness.yaml",
        help="Path to the harness YAML config.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level))

    try:
        config = load_config(Path(args.config))
        harness = Harness(config)
        asyncio.run(harness.run())
    except Exception as exc:
        logging.getLogger(__name__).error("sunbeam-valet failed: %s", exc)
        return 1

    return 0
