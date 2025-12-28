"""
Analyst Agent - Analyzes articles using LLM.
"""
from typing import List

from ..models.article import RawArticle, AnalyzedArticle, ImportanceLevel
from ..skills.llm_skills import LLMSkills
from ..utils.logger import log


class AnalystAgent:
    """
    Analyst Agent responsible for analyzing articles using LLM.

    Skills:
    - LLM Client (Claude API)

    Tasks:
    - Summarize articles (3 lines in Japanese)
    - Extract technology tags
    - Determine importance level (S/A/B)
    """

    def __init__(self, max_concurrent_analyses: int = 3):
        self.llm_skills = LLMSkills()
        self.max_concurrent = max_concurrent_analyses

    async def analyze_article(self, article: RawArticle) -> AnalyzedArticle:
        """
        Analyze a single article.

        Args:
            article: RawArticle to analyze

        Returns:
            AnalyzedArticle with analysis results
        """
        return await self.llm_skills.analyze_article(article)

    async def analyze_batch(self, articles: List[RawArticle]) -> List[AnalyzedArticle]:
        """
        Analyze multiple articles concurrently.

        Args:
            articles: List of RawArticle objects

        Returns:
            List of AnalyzedArticle objects
        """
        log.info(f"Analyzing {len(articles)} articles")
        analyzed = await self.llm_skills.batch_analyze_articles(
            articles,
            max_concurrent=self.max_concurrent
        )
        log.info(f"Analysis complete: {len(analyzed)} articles analyzed")
        return analyzed

    async def run(self, articles: List[RawArticle]) -> List[AnalyzedArticle]:
        """
        Run the analyst agent to analyze all articles.

        Args:
            articles: List of RawArticle objects to analyze

        Returns:
            List of AnalyzedArticle objects
        """
        log.info("Analyst Agent started")

        if not articles:
            log.warning("No articles to analyze")
            return []

        analyzed_articles = await self.analyze_batch(articles)

        # Log statistics
        importance_counts = {
            ImportanceLevel.S: 0,
            ImportanceLevel.A: 0,
            ImportanceLevel.B: 0
        }

        for article in analyzed_articles:
            importance_counts[article.importance] += 1

        log.info(
            f"Analyst Agent completed. "
            f"S: {importance_counts[ImportanceLevel.S]}, "
            f"A: {importance_counts[ImportanceLevel.A]}, "
            f"B: {importance_counts[ImportanceLevel.B]}"
        )

        return analyzed_articles
