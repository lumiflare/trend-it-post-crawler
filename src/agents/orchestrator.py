"""
Orchestrator Agent - Manages the entire workflow.
"""
from typing import Optional
from datetime import datetime

from .scraper import ScraperAgent
from .analyst import AnalystAgent
from .reporter import ReporterAgent
from ..models.article import DailyReport
from ..utils.logger import log


class OrchestratorAgent:
    """
    Orchestrator Agent responsible for managing the entire workflow.

    Skills:
    - Asyncio Task Management
    - Error Logging
    - Retry Logic

    Tasks:
    - Coordinate scraper, analyst, and reporter agents
    - Handle errors gracefully
    - Ensure pipeline execution
    """

    def __init__(
        self,
        sources_config_path: str = "config/sources.yaml",
        max_concurrent_scrapes: int = 5,
        max_concurrent_analyses: int = 3
    ):
        self.scraper = ScraperAgent(sources_config_path)
        self.analyst = AnalystAgent(max_concurrent_analyses)
        self.reporter = ReporterAgent()

    async def run_pipeline(
        self,
        save_file: bool = True,
        publish_notion: bool = True
    ) -> Optional[DailyReport]:
        """
        Run the complete data collection and analysis pipeline.

        Args:
            save_file: Whether to save report to file
            publish_notion: Whether to publish to Notion

        Returns:
            Generated DailyReport or None if failed
        """
        start_time = datetime.now()
        log.info("=" * 80)
        log.info("Orchestrator Agent started - Beginning daily trend collection")
        log.info("=" * 80)

        try:
            # Step 1: Collect articles
            log.info("STEP 1/3: Collecting articles from sources...")
            raw_articles = await self.scraper.run()

            if not raw_articles:
                log.warning("No articles collected. Aborting pipeline.")
                return None

            log.info(f"✓ Collected {len(raw_articles)} articles")

            # Step 2: Analyze articles
            log.info("STEP 2/3: Analyzing articles with LLM...")
            analyzed_articles = await self.analyst.run(raw_articles)

            if not analyzed_articles:
                log.warning("No articles analyzed. Aborting pipeline.")
                return None

            log.info(f"✓ Analyzed {len(analyzed_articles)} articles")

            # Step 3: Generate and publish report
            log.info("STEP 3/3: Generating and publishing report...")
            report = await self.reporter.run(
                analyzed_articles,
                save_file=save_file,
                publish_notion=publish_notion
            )

            log.info("✓ Report generated and published")

            # Pipeline complete
            elapsed_time = (datetime.now() - start_time).total_seconds()
            log.info("=" * 80)
            log.info(f"Pipeline completed successfully in {elapsed_time:.2f} seconds")
            log.info(f"Total articles processed: {report.total_articles}")
            log.info("=" * 80)

            return report

        except Exception as e:
            log.error(f"Pipeline failed with error: {e}", exc_info=True)
            return None

        finally:
            # Cleanup resources
            await self.scraper.close()

    async def run(
        self,
        save_file: bool = True,
        publish_notion: bool = True
    ) -> Optional[DailyReport]:
        """
        Run the orchestrator agent.

        Args:
            save_file: Whether to save report to file
            publish_notion: Whether to publish to Notion

        Returns:
            Generated DailyReport or None if failed
        """
        return await self.run_pipeline(
            save_file=save_file,
            publish_notion=publish_notion
        )
