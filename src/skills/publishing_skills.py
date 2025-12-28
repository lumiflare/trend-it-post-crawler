"""
Publishing skills for distributing reports.
"""
from typing import Optional
from pathlib import Path
from datetime import datetime
import httpx
import aiofiles

from ..models.article import DailyReport
from ..utils.logger import log
from .notion_mcp_skills import NotionMCPSkills
from config.settings import settings


class PublishingSkills:
    """Collection of publishing skills for report distribution."""

    def __init__(self):
        self.output_dir = Path(settings.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.notion_skills = NotionMCPSkills()

    async def save_to_file(self, report: DailyReport, filename: Optional[str] = None) -> str:
        """
        Save report to a markdown file.

        Args:
            report: DailyReport to save
            filename: Optional custom filename

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = report.report_date.strftime("%Y%m%d_%H%M%S")
            filename = f"daily_report_{timestamp}.md"

        filepath = self.output_dir / filename
        markdown_content = report.to_markdown()

        try:
            async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                await f.write(markdown_content)

            log.info(f"Report saved to file: {filepath}")
            return str(filepath)

        except Exception as e:
            log.error(f"Failed to save report to file: {e}")
            raise

    async def publish_to_notion(self, report: DailyReport) -> Optional[str]:
        """
        Publish report to Notion as a new page using MCP.

        Args:
            report: DailyReport to publish

        Returns:
            Notion page URL if successful, None otherwise
        """
        try:
            # Connect to MCP server
            await self.notion_skills.connect()

            # Create page
            page_url = await self.notion_skills.create_daily_report_page(report)

            return page_url

        except Exception as e:
            log.error(f"Failed to publish to Notion via MCP: {e}")
            return None

        finally:
            # Always disconnect
            await self.notion_skills.disconnect()

    async def publish_report(
        self,
        report: DailyReport,
        save_file: bool = True,
        publish_notion: bool = True
    ) -> dict:
        """
        Publish report to all configured destinations.

        Args:
            report: DailyReport to publish
            save_file: Whether to save to file
            publish_notion: Whether to publish to Notion

        Returns:
            Dict with publishing results
        """
        results = {
            "file_path": None,
            "notion_url": None
        }

        # Save to file
        if save_file:
            try:
                results["file_path"] = await self.save_to_file(report)
            except Exception as e:
                log.error(f"Failed to save report to file: {e}")

        # Publish to Notion
        if publish_notion:
            results["notion_url"] = await self.publish_to_notion(report)

        return results
