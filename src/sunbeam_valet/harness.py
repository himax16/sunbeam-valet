import logging
from pathlib import Path

from sunbeam_valet.agent.pool import AgentPool
from sunbeam_valet.config import HarnessConfig, load_config
from sunbeam_valet.disagreement import get_metric
from sunbeam_valet.fetchers import get_fetcher
from sunbeam_valet.formatters import get_formatter
from sunbeam_valet.judge import run_judge
from sunbeam_valet.mattermost import MattermostPoster
from sunbeam_valet.models import Bug, JudgeOutput, TableRow

logger = logging.getLogger(__name__)


class Harness:
    def __init__(self, config: HarnessConfig):
        self.config = config
        self.pool = AgentPool(config.agents)
        self.fetcher = get_fetcher("watchtower", config.watchtower)
        self.disagreement_metric = get_metric(config.round2_trigger.metric)
        self.formatter = get_formatter("markdown")
        self.poster = MattermostPoster(config.mattermost)

    async def run(self) -> None:
        logger.info("Fetching bugs from watchtower...")
        bugs = await self.fetcher.fetch()
        logger.info(f"Fetched {len(bugs)} bugs")

        table_rows = []
        round2_count = 0

        for bug in bugs:
            row = await self._process_bug(bug)
            table_rows.append(row)
            if row.round2 == "yes":
                round2_count += 1

        message = self.formatter.format(table_rows, round2_count)
        logger.info(
            "Posting to Mattermost channel '%s'...",
            self.config.mattermost.channel_id,
        )
        await self.poster.post(message)
        logger.info("Done.")

    async def _process_bug(self, bug: Bug) -> TableRow:
        logger.debug(f"Processing bug {bug.id}")

        round1_result = await self.pool.run_agents(bug, round_number=1)
        all_outputs = list(round1_result.outputs)

        if round1_result.errors:
            logger.warning(f"Bug {bug.id} round 1 errors: {round1_result.errors}")

        if not all_outputs:
            return self._to_table_row(
                bug,
                JudgeOutput(
                    bug_id=bug.id,
                    summary="ERROR",
                    confidence=0.0,
                    agent_votes={},
                    status="error",
                    did_round2=False,
                    error="no agent outputs returned",
                ),
            )

        did_round2 = False
        if self.config.max_rounds >= 2 and len(all_outputs) >= 2:
            disagreement = self.disagreement_metric.compute(all_outputs)
            if disagreement > self.config.round2_trigger.threshold:
                logger.debug(
                    f"Bug {bug.id}: disagreement {disagreement:.3f} > "
                    f"threshold {self.config.round2_trigger.threshold}, running round 2"
                )
                round2_result = await self.pool.run_agents(
                    bug,
                    round_number=2,
                    context=list(all_outputs),
                )
                all_outputs.extend(round2_result.outputs)
                did_round2 = True

                if round2_result.errors:
                    logger.warning(f"Bug {bug.id} round 2 errors: {round2_result.errors}")

        judge_output = await run_judge(
            self.config.judge,
            bug,
            all_outputs,
            did_round2,
        )

        return self._to_table_row(bug, judge_output)

    def _to_table_row(
        self,
        bug: Bug,
        judge_output: JudgeOutput,
    ) -> TableRow:
        if judge_output.status == "error":
            return TableRow(
                bug_reference=f"LP:#{bug.id}",
                bug_reference_url=bug.url,
                summary=judge_output.error or "Unknown error",
                confidence="ERROR",
                agent_votes="-",
                status="error",
                round2="-" if not judge_output.did_round2 else "yes",
            )

        agent_votes_str = ", ".join(
            f"{name}:{conf:.1f}" for name, conf in judge_output.agent_votes.items()
        )

        return TableRow(
            bug_reference=f"LP:#{bug.id}",
            bug_reference_url=bug.url,
            summary=(
                judge_output.summary[:100] + "..."
                if len(judge_output.summary) > 100
                else judge_output.summary
            ),
            confidence=f"{judge_output.confidence:.2f}",
            agent_votes=agent_votes_str,
            status=judge_output.status,
            round2="yes" if judge_output.did_round2 else "no",
        )


async def run(config_path: str | Path = "config/harness.yaml") -> None:
    config_file = Path(config_path)
    if not config_file.is_absolute():
        config_file = Path(__file__).parent.parent.parent / config_path

    config = load_config(config_file)
    harness = Harness(config)
    await harness.run()
