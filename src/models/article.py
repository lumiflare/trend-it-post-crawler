"""
Data models for articles and analysis results.
"""
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Literal
from datetime import datetime
from zoneinfo import ZoneInfo
from enum import Enum

# Japan timezone
JST = ZoneInfo("Asia/Tokyo")


def now_jst() -> datetime:
    """Get current time in JST."""
    return datetime.now(JST)


class ImportanceLevel(str, Enum):
    """Importance level of an article."""
    S = "S"  # 非常に重要
    A = "A"  # 重要
    B = "B"  # 普通


class RawArticle(BaseModel):
    """Raw article data collected from sources."""
    source: str = Field(..., description="Source website name")
    url: HttpUrl = Field(..., description="Article URL")
    title: str = Field(..., description="Article title")
    content: Optional[str] = Field(None, description="Article content (if available)")
    published_at: Optional[datetime] = Field(None, description="Publication date")
    collected_at: datetime = Field(default_factory=now_jst, description="Collection timestamp")


class AnalyzedArticle(BaseModel):
    """Analyzed article with AI-generated insights."""
    # Original data
    source: str
    url: HttpUrl
    title: str
    published_at: Optional[datetime] = None

    # Analysis results
    summary: str = Field(..., description="3-line summary in Japanese")
    tags: List[str] = Field(default_factory=list, description="Technology tags (e.g., Rust, Next.js)")
    importance: ImportanceLevel = Field(..., description="Importance level (S/A/B)")
    analyzed_at: datetime = Field(default_factory=now_jst)


class DailyReport(BaseModel):
    """Daily report containing all analyzed articles."""
    report_date: datetime = Field(default_factory=now_jst)
    total_articles: int = Field(0, description="Total number of articles analyzed")
    articles_by_importance: dict[ImportanceLevel, int] = Field(
        default_factory=dict,
        description="Count of articles by importance level"
    )
    articles: List[AnalyzedArticle] = Field(default_factory=list)

    def to_markdown(self) -> str:
        """Convert report to Markdown format."""
        md_lines = [
            f"# 📊 IT Trend Daily Report",
            f"**Date:** {self.report_date.strftime('%Y-%m-%d %H:%M')}",
            f"**Total Articles:** {self.total_articles}",
            "",
            "## 📈 Summary",
            ""
        ]

        # Importance distribution
        for level in ImportanceLevel:
            count = self.articles_by_importance.get(level, 0)
            md_lines.append(f"- **{level.value} Rank:** {count} articles")

        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

        # Group articles by importance
        for level in [ImportanceLevel.S, ImportanceLevel.A, ImportanceLevel.B]:
            articles = [a for a in self.articles if a.importance == level]
            if not articles:
                continue

            md_lines.append(f"## {level.value} Rank Articles ({len(articles)})")
            md_lines.append("")

            for article in articles:
                md_lines.append(f"### [{article.title}]({article.url})")
                md_lines.append(f"**Source:** {article.source}")
                if article.published_at:
                    md_lines.append(f"**Published:** {article.published_at.strftime('%Y-%m-%d %H:%M')}")
                md_lines.append("")
                md_lines.append("**Summary:**")
                md_lines.append(article.summary)
                md_lines.append("")
                if article.tags:
                    tags_str = ", ".join([f"`{tag}`" for tag in article.tags])
                    md_lines.append(f"**Tags:** {tags_str}")
                md_lines.append("")
                md_lines.append("---")
                md_lines.append("")

        return "\n".join(md_lines)
