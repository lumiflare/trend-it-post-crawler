"""
Reporter Agent - Generates and publishes reports.
"""
from typing import List
from datetime import datetime

from ..models.article import AnalyzedArticle, DailyReport, ImportanceLevel, now_jst
from ..skills.publishing_skills import PublishingSkills
from ..utils.logger import log


class ReporterAgent:
    """
    Reporter Agent responsible for generating and publishing reports.

    Skills:
    - Markdown formatting
    - Notion integration (daily pages)

    Tasks:
    - Generate structured daily report
    - Save report to file
    - Create Notion page as child of IT Trend page
    """

    def __init__(self):
        self.publishing_skills = PublishingSkills()

    def generate_report(self, articles: List[AnalyzedArticle]) -> DailyReport:
        """
        Generate a daily report from analyzed articles.

        Args:
            articles: List of AnalyzedArticle objects

        Returns:
            DailyReport object
        """
        log.info(f"Generating report from {len(articles)} articles")

        # Sort articles by importance (S > A > B), then by source
        importance_order = {ImportanceLevel.S: 0, ImportanceLevel.A: 1, ImportanceLevel.B: 2}
        sorted_articles = sorted(
            articles,
            key=lambda a: (importance_order[a.importance], a.source, a.title)
        )

        # Select top 10 articles prioritizing S/A rank
        # Ideally 8+ S/A rank articles
        top_articles = sorted_articles[:10]

        # Count selected articles by importance
        articles_by_importance = {
            ImportanceLevel.S: 0,
            ImportanceLevel.A: 0,
            ImportanceLevel.B: 0
        }

        for article in top_articles:
            articles_by_importance[article.importance] += 1

        report = DailyReport(
            report_date=now_jst(),
            total_articles=len(top_articles),
            articles_by_importance=articles_by_importance,
            articles=top_articles
        )

        s_count = articles_by_importance[ImportanceLevel.S]
        a_count = articles_by_importance[ImportanceLevel.A]
        b_count = articles_by_importance[ImportanceLevel.B]

        log.info(
            f"Report generated: {report.total_articles} articles "
            f"(S: {s_count}, A: {a_count}, B: {b_count}) "
            f"[S+A: {s_count + a_count}/10 articles]"
        )

        return report

    async def publish_report(
        self,
        report: DailyReport,
        save_file: bool = True,
        publish_notion: bool = True
    ) -> dict:
        """
        Publish report to configured destinations.

        Args:
            report: DailyReport to publish
            save_file: Whether to save to file
            publish_notion: Whether to publish to Notion

        Returns:
            Dict with publishing results
        """
        log.info("Publishing report")
        results = await self.publishing_skills.publish_report(
            report,
            save_file=save_file,
            publish_notion=publish_notion
        )
        log.info(f"Report published: {results}")
        return results

    async def run(
        self,
        articles: List[AnalyzedArticle],
        save_file: bool = True,
        publish_notion: bool = True
    ) -> DailyReport:
        """
        Run the reporter agent to generate and publish report.

        Args:
            articles: List of AnalyzedArticle objects
            save_file: Whether to save report to file
            publish_notion: Whether to publish to Notion

        Returns:
            Generated DailyReport
        """
        log.info("Reporter Agent started")

        if not articles:
            log.warning("No articles to report")
            return DailyReport()

        # Generate report
        report = self.generate_report(articles)

        # Publish report
        await self.publish_report(
            report,
            save_file=save_file,
            publish_notion=publish_notion
        )

        log.info("Reporter Agent completed")
        return report
