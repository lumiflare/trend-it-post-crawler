"""
Test script to verify Notion MCP connection.

Usage:
    python test_notion_connection.py
"""
import asyncio
from src.skills.notion_mcp_skills import NotionMCPSkills
from src.utils.logger import log, setup_logger
from config.settings import settings


async def main():
    """Test Notion MCP connection."""
    setup_logger(log_level="INFO")

    log.info("Testing Notion MCP connection...")
    log.info(f"Notion API Key configured: {'Yes' if settings.notion_api_key else 'No'}")
    log.info(f"Parent Page ID configured: {'Yes' if settings.notion_parent_page_id else 'No'}")

    if not settings.notion_api_key:
        log.error("NOTION_API_KEY not configured in .env file")
        return 1

    if not settings.notion_parent_page_id:
        log.warning("NOTION_PARENT_PAGE_ID not configured in .env file")
        log.info("You can still test the MCP connection without a parent page ID")

    # Test connection
    notion_skills = NotionMCPSkills()
    success = await notion_skills.test_connection()

    if success:
        log.info("✅ Notion MCP connection successful!")
        if settings.notion_parent_page_id:
            log.info(f"Parent page ID: {settings.notion_parent_page_id}")
        log.info("You're ready to start creating daily report pages!")
        log.info("\nMake sure:")
        log.info("1. Node.js is installed (required for MCP server)")
        log.info("2. The Notion integration is connected to the parent page")
        return 0
    else:
        log.error("❌ Notion MCP connection failed!")
        log.error("\nTroubleshooting:")
        log.error("1. Check your NOTION_API_KEY in .env file")
        log.error("2. Make sure Node.js is installed: node --version")
        log.error("3. Ensure @notionhq/notion-mcp-server is available via npx")
        log.error("4. Check that the integration is connected to the parent page")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
