import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from sunbeam_valet.config import load_config
from sunbeam_valet.harness import Harness

OutputMode = Literal["mattermost", "stdout"]


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
    parser.add_argument(
        "--output",
        choices=["mattermost", "stdout"],
        default="mattermost",
        help="Where to send the rendered report.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of fetched bugs to triage.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level))

    try:
        output: OutputMode = args.output
        config = load_config(
            Path(args.config),
            require_mattermost=output == "mattermost",
        )
        harness = Harness(config)
        message = asyncio.run(
            harness.run(
                post_to_mattermost=output == "mattermost",
                limit=args.limit,
            )
        )
        if output == "stdout":
            print(message, file=sys.stdout)
    except Exception as exc:
        logging.getLogger(__name__).error("sunbeam-valet failed: %s", exc)
        return 1

    return 0
