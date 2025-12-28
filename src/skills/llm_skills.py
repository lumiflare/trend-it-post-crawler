"""
LLM skills for analyzing articles using Claude API.
"""
from typing import List, Dict, Any
import json
from anthropic import AsyncAnthropic

from ..models.article import RawArticle, AnalyzedArticle, ImportanceLevel
from ..utils.logger import log
from ..utils.retry import api_retry
from config.settings import settings


class LLMSkills:
    """Collection of LLM skills for article analysis."""

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.model_name
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature

    @api_retry
    async def analyze_article(self, article: RawArticle) -> AnalyzedArticle:
        """
        Analyze a single article using Claude API.

        Args:
            article: RawArticle to analyze

        Returns:
            AnalyzedArticle with summary, tags, and importance
        """
        log.info(f"Analyzing article: {article.title}")

        # Prepare prompt
        prompt = self._create_analysis_prompt(article)

        try:
            # Call Claude API
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract response
            response_text = message.content[0].text
            analysis_result = self._parse_analysis_response(response_text)

            # Create AnalyzedArticle
            analyzed_article = AnalyzedArticle(
                source=article.source,
                url=article.url,
                title=article.title,
                published_at=article.published_at,
                summary=analysis_result["summary"],
                tags=analysis_result["tags"],
                importance=ImportanceLevel(analysis_result["importance"])
            )

            log.info(f"Successfully analyzed article: {article.title} (Importance: {analyzed_article.importance.value})")
            return analyzed_article

        except Exception as e:
            log.error(f"Error analyzing article {article.title}: {e}")
            # Return default analysis on error
            return AnalyzedArticle(
                source=article.source,
                url=article.url,
                title=article.title,
                published_at=article.published_at,
                summary="分析に失敗しました。",
                tags=[],
                importance=ImportanceLevel.B
            )

    def _create_analysis_prompt(self, article: RawArticle) -> str:
        """
        Create analysis prompt for Claude.

        Args:
            article: RawArticle to analyze

        Returns:
            Formatted prompt string
        """
        prompt = f"""あなたは日本のITトレンドを分析する専門家です。以下の記事を分析してください。

記事タイトル: {article.title}
ソース: {article.source}
URL: {article.url}

以下の形式でJSON形式で回答してください：

{{
  "summary": "記事の要約を3行以内の日本語で記載。エンジニア向けに技術的な内容を簡潔にまとめる。",
  "tags": ["技術タグ1", "技術タグ2", "技術タグ3"],
  "importance": "S",
  "reasoning": "重要度判定の理由"
}}

**重要度の基準:**
- **S**: 業界に大きな影響を与える重要なニュース
  - 新しいメジャーバージョンリリース、破壊的変更
  - 重要なセキュリティ脆弱性や脅威
  - 業界標準・新技術の発表（新しいフレームワーク、プロトコル、標準規格など）
  - GitHub、AWS、Googleなど主要企業の重要なアップデート
  - AI/ML分野の画期的な発表や機能追加
- **A**: エンジニアが知るべき技術トレンドや実用的な情報（デフォルト）
  - 新機能・アップデート情報
  - 実践的なチュートリアル、ベストプラクティス
  - パフォーマンス改善・最適化手法
  - 新しいツール・ライブラリの紹介
  - 技術的な課題解決方法
- **B**: 一般的な技術情報や個人的な体験談

**技術タグの抽出ルール:**
- プログラミング言語（例: Python, Rust, TypeScript）
- フレームワーク・ライブラリ（例: React, Next.js, Django）
- クラウド・インフラ（例: AWS, Docker, Kubernetes）
- その他の技術キーワード（例: AI/ML, セキュリティ, パフォーマンス）
- 最大5個まで抽出

必ずJSON形式で回答してください。"""

        return prompt

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """
        Parse Claude's analysis response.

        Args:
            response: Raw response text from Claude

        Returns:
            Parsed analysis dict
        """
        try:
            # Try to extract JSON from response
            # Claude may wrap JSON in markdown code blocks
            response = response.strip()

            # Remove markdown code blocks if present
            if response.startswith("```json"):
                response = response[7:]  # Remove ```json
            if response.startswith("```"):
                response = response[3:]  # Remove ```
            if response.endswith("```"):
                response = response[:-3]  # Remove ```

            response = response.strip()

            # Parse JSON
            result = json.loads(response)

            # Validate required fields
            if "summary" not in result:
                result["summary"] = "要約の生成に失敗しました。"
            if "tags" not in result:
                result["tags"] = []
            if "importance" not in result:
                result["importance"] = "B"

            # Ensure tags is a list
            if not isinstance(result["tags"], list):
                result["tags"] = []

            # Validate importance level
            if result["importance"] not in ["S", "A", "B"]:
                result["importance"] = "B"

            return result

        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON response: {e}")
            log.debug(f"Response text: {response}")
            return {
                "summary": "分析結果の解析に失敗しました。",
                "tags": [],
                "importance": "B"
            }

    async def batch_analyze_articles(
        self,
        articles: List[RawArticle],
        max_concurrent: int = 3
    ) -> List[AnalyzedArticle]:
        """
        Analyze multiple articles concurrently.

        Args:
            articles: List of RawArticle objects
            max_concurrent: Maximum concurrent API calls

        Returns:
            List of AnalyzedArticle objects
        """
        import asyncio

        log.info(f"Starting batch analysis of {len(articles)} articles")

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_with_semaphore(article: RawArticle) -> AnalyzedArticle:
            async with semaphore:
                return await self.analyze_article(article)

        # Analyze all articles concurrently
        analyzed_articles = await asyncio.gather(
            *[analyze_with_semaphore(article) for article in articles],
            return_exceptions=False
        )

        log.info(f"Completed batch analysis of {len(analyzed_articles)} articles")
        return analyzed_articles
