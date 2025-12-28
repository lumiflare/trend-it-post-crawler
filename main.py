"""
Main entry point for the Trend IT Post Crawler.

This script orchestrates the entire pipeline:
1. Scraper Agent: Collects articles from configured sources
2. Analyst Agent: Analyzes articles using Claude API
3. Reporter Agent: Generates and publishes daily report
"""
import asyncio
import argparse
from pathlib import Path

from src.agents.orchestrator import OrchestratorAgent
from src.utils.logger import log, setup_logger


async def main(
    save_file: bool = True,
    publish_notion: bool = True,
    log_level: str = "INFO"
):
    """
    Main async function to run the crawler.

    Args:
        save_file: Whether to save report to file
        publish_notion: Whether to publish to Notion
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Setup logger
    setup_logger(log_level=log_level)

    log.info("Starting Trend IT Post Crawler")

    # Create and run orchestrator
    orchestrator = OrchestratorAgent()

    try:
        report = await orchestrator.run(
            save_file=save_file,
            publish_notion=publish_notion
        )

        if report:
            log.info("Crawler completed successfully!")
            log.info(f"Total articles: {report.total_articles}")
        else:
            log.error("Crawler failed to generate report")
            return 1

        return 0

    except KeyboardInterrupt:
        log.warning("Crawler interrupted by user")
        return 130
    except Exception as e:
        log.error(f"Crawler failed with unexpected error: {e}", exc_info=True)
        return 1


def cli():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Trend IT Post Crawler - Daily IT trend collection and analysis"
    )

    parser.add_argument(
        "--no-file",
        action="store_true",
        help="Don't save report to file"
    )

    parser.add_argument(
        "--no-notion",
        action="store_true",
        help="Don't publish to Notion"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )

    args = parser.parse_args()

    # Run async main
    exit_code = asyncio.run(
        main(
            save_file=not args.no_file,
            publish_notion=not args.no_notion,
            log_level=args.log_level
        )
    )

    return exit_code


if __name__ == "__main__":
    exit(cli())
