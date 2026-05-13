import logging

from sunbeam_valet.agent.pool import AgentPool
from sunbeam_valet.config import HarnessConfig
from sunbeam_valet.disagreement.std_dev import StdDevDisagreementMetric
from sunbeam_valet.fetchers.watchtower import WatchtowerFetcher
from sunbeam_valet.formatters.markdown import MarkdownFormatter
from sunbeam_valet.judge.engine import run_judge
from sunbeam_valet.mattermost.poster import MattermostPoster
from sunbeam_valet.models import Bug, JudgeOutput, TableRow

logger = logging.getLogger(__name__)


class Harness:
    def __init__(self, config: HarnessConfig):
        self.config = config
        self.pool = AgentPool(config.agents)
        self.fetcher = WatchtowerFetcher(config.watchtower)
        self.disagreement_metric = StdDevDisagreementMetric()
        self.formatter = MarkdownFormatter()
        self.poster = MattermostPoster(config.mattermost) if config.mattermost else None

    async def run(self, *, post_to_mattermost: bool = True, limit: int | None = None) -> str:
        logger.info("Fetching bugs from watchtower...")
        bugs = await self.fetcher.fetch()
        if limit is not None:
            bugs = bugs[:limit]
        logger.info(f"Fetched {len(bugs)} bugs")

        table_rows = []
        round2_count = 0

        for bug in bugs:
            row = await self._triage_bug(bug)
            table_rows.append(row)
            if row.round2:
                round2_count += 1

        message = self.formatter.format(table_rows, round2_count)
        if not post_to_mattermost:
            return message

        if self.poster is None:
            raise ValueError("Mattermost configuration is required for Mattermost output")

        logger.info(
            "Posting to Mattermost via %s...",
            self.config.mattermost.mode if self.config.mattermost else "",
        )
        await self.poster.post(message)
        logger.info("Done.")
        return message

    async def _triage_bug(self, bug: Bug) -> TableRow:
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
                    classification=None,
                    priority=None,
                    action=None,
                    rationale=None,
                    concerns=[],
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
                confidence=None,
                classification=None,
                priority=None,
                action=None,
                rationale=None,
                agent_votes=judge_output.agent_votes,
                status="error",
                round2=judge_output.did_round2,
            )

        return TableRow(
            bug_reference=f"LP:#{bug.id}",
            bug_reference_url=bug.url,
            summary=judge_output.summary,
            confidence=judge_output.confidence,
            classification=judge_output.classification,
            priority=judge_output.priority,
            action=judge_output.action,
            rationale=judge_output.rationale,
            agent_votes=judge_output.agent_votes,
            status=judge_output.status,
            round2=judge_output.did_round2,
        )
