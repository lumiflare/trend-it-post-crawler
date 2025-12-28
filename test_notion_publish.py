"""
Test script to publish a sample report to Notion.
This test creates a child page under the IT Trend parent page.
"""
import asyncio
from datetime import datetime
from src.models.article import DailyReport, AnalyzedArticle, ImportanceLevel, now_jst
from src.skills.notion_mcp_skills import NotionMCPSkills
from src.utils.logger import log, setup_logger
from config.settings import settings


def create_sample_report() -> DailyReport:
    """Create a sample daily report for testing."""

    # Sample articles
    articles = [
        AnalyzedArticle(
            source="Qiita",
            url="https://qiita.com/sample1",
            title="Claude Code で開発生産性が10倍に！実践的な活用法",
            published_at=now_jst(),
            summary="Claude Codeを使うことで、コーディングからレビューまでの開発フローが劇的に改善。特にリファクタリングやバグ修正で効果を発揮。AIエージェントとの協働により、開発者は本質的な設計に集中できるようになった。",
            tags=["Claude", "AI", "開発生産性"],
            importance=ImportanceLevel.S
        ),
        AnalyzedArticle(
            source="Zenn",
            url="https://zenn.dev/sample2",
            title="Next.js 15の新機能まとめ - React Server Componentsの進化",
            published_at=now_jst(),
            summary="Next.js 15でReact Server Componentsが大幅に強化。パフォーマンスが向上し、データフェッチングが簡潔に記述可能に。Turbopackの正式サポートによりビルド時間も短縮された。",
            tags=["Next.js", "React", "Frontend"],
            importance=ImportanceLevel.A
        ),
        AnalyzedArticle(
            source="DevelopersIO",
            url="https://dev.classmethod.jp/sample3",
            title="Amazon Bedrock の新機能でマルチモーダルAIアプリ構築が簡単に",
            published_at=now_jst(),
            summary="Amazon BedrockにマルチモーダルAPI機能が追加。画像とテキストを組み合わせたAIアプリケーションの開発が容易に。Claude 3との連携で高度な分析が可能になった。",
            tags=["AWS", "Bedrock", "AI", "Claude"],
            importance=ImportanceLevel.A
        ),
        AnalyzedArticle(
            source="Hatena Blog",
            url="https://example.com/sample4",
            title="Rustで作る高速WebAPIサーバー - Axumフレームワーク入門",
            published_at=now_jst(),
            summary="Rustの非同期フレームワークAxumを使った高速なWeb APIサーバーの構築方法を解説。型安全性とパフォーマンスを両立し、本番環境での運用実績も豊富。",
            tags=["Rust", "Axum", "WebAPI"],
            importance=ImportanceLevel.A
        ),
        AnalyzedArticle(
            source="Publickey",
            url="https://publickey.jp/sample5",
            title="GitHub Copilot Workspace が GA に - AIによる開発フロー全体の自動化",
            published_at=now_jst(),
            summary="GitHub Copilot WorkspaceがGA（一般提供）を開始。Issue作成から実装、テスト、PRまでの開発フロー全体をAIが支援。開発者の生産性がさらに向上する見込み。",
            tags=["GitHub", "Copilot", "AI"],
            importance=ImportanceLevel.A
        )
    ]

    # Create report
    articles_by_importance = {
        ImportanceLevel.S: sum(1 for a in articles if a.importance == ImportanceLevel.S),
        ImportanceLevel.A: sum(1 for a in articles if a.importance == ImportanceLevel.A),
        ImportanceLevel.B: sum(1 for a in articles if a.importance == ImportanceLevel.B),
    }

    report = DailyReport(
        report_date=now_jst(),
        total_articles=len(articles),
        articles_by_importance=articles_by_importance,
        articles=articles
    )

    return report


async def main():
    """Test Notion page creation with sample data."""
    setup_logger(log_level="INFO")

    log.info("=" * 80)
    log.info("Testing Notion Page Creation")
    log.info("=" * 80)

    # Check configuration
    if not settings.notion_api_key:
        log.error("NOTION_API_KEY not configured in .env file")
        return 1

    if not settings.notion_parent_page_id:
        log.error("NOTION_PARENT_PAGE_ID not configured in .env file")
        return 1

    log.info(f"NOTION_API_KEY: {settings.notion_api_key}")
    log.info(f"Parent Page ID: {settings.notion_parent_page_id}")

    # Create sample report
    log.info("Creating sample report...")
    report = create_sample_report()
    log.info(f"Sample report created: {report.total_articles} articles")
    log.info(f"  - S Rank: {report.articles_by_importance[ImportanceLevel.S]}")
    log.info(f"  - A Rank: {report.articles_by_importance[ImportanceLevel.A]}")
    log.info(f"  - B Rank: {report.articles_by_importance[ImportanceLevel.B]}")

    # Connect to Notion and create page
    log.info("\nConnecting to Notion MCP server...")
    notion_skills = NotionMCPSkills()

    try:
        # Connect
        await notion_skills.connect()
        log.info("✓ Connected to Notion MCP server")

        # Create page
        log.info("\nCreating Notion page...")
        page_url = await notion_skills.create_daily_report_page(report)

        if page_url:
            log.info("=" * 80)
            log.info("✅ SUCCESS! Notion page created!")
            log.info("=" * 80)
            log.info(f"Page URL: {page_url}")
            log.info("")
            log.info("Please check your Notion workspace to see the new page!")
            return 0
        else:
            log.error("=" * 80)
            log.error("❌ FAILED to create Notion page")
            log.error("=" * 80)
            return 1

    except Exception as e:
        log.error(f"Error during test: {e}", exc_info=True)
        return 1

    finally:
        # Disconnect
        await notion_skills.disconnect()
        log.info("Disconnected from Notion MCP server")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
