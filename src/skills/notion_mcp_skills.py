"""
Notion integration skills using MCP (Model Context Protocol).
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..models.article import DailyReport, AnalyzedArticle, ImportanceLevel
from ..utils.logger import log
from config.settings import settings


class NotionMCPSkills:
    """Collection of Notion integration skills using MCP."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        parent_page_id: Optional[str] = None
    ):
        """
        Initialize Notion MCP client.

        Args:
            api_key: Notion API key (defaults to settings)
            parent_page_id: Parent page ID for creating child pages (defaults to settings)
        """
        self.api_key = api_key or settings.notion_api_key
        self.parent_page_id = parent_page_id or settings.notion_parent_page_id
        self.session: Optional[ClientSession] = None
        self._read_stream = None
        self._write_stream = None
        self._stdio_context = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self):
        """Connect to Notion MCP server."""
        if not self.api_key:
            log.warning("Notion API key not configured")
            return

        try:
            # Set environment variable for MCP server
            # notion-mcp-server expects NOTION_TOKEN
            env = os.environ.copy()
            env["NOTION_TOKEN"] = self.api_key

            # Configure MCP server parameters
            server_params = StdioServerParameters(
                command="npx",
                args=["-y", "@notionhq/notion-mcp-server"],
                env=env
            )

            # Connect to MCP server
            log.info("Connecting to Notion MCP server...")

            # Create stdio context manager
            self._stdio_context = stdio_client(server_params)
            self._read_stream, self._write_stream = await self._stdio_context.__aenter__()

            # Create session
            self.session = ClientSession(self._read_stream, self._write_stream)
            await self.session.__aenter__()

            # Initialize session
            await self.session.initialize()

            log.info("Successfully connected to Notion MCP server")

        except Exception as e:
            log.error(f"Failed to connect to Notion MCP server: {e}")
            self.session = None
            raise

    async def disconnect(self):
        """Disconnect from Notion MCP server."""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
                self.session = None

            if self._stdio_context:
                await self._stdio_context.__aexit__(None, None, None)
                self._stdio_context = None

            self._read_stream = None
            self._write_stream = None

            log.info("Disconnected from Notion MCP server")
        except Exception as e:
            log.error(f"Error disconnecting from MCP server: {e}")

    def _create_page_title(self, report: DailyReport) -> str:
        """Create page title from report date."""
        return report.report_date.strftime("%Y年%m月%d日")

    def _format_article_content(self, article: AnalyzedArticle) -> str:
        """
        Format a single article as markdown.

        Args:
            article: AnalyzedArticle object

        Returns:
            Formatted markdown string
        """
        content = f"### [{article.title}]({article.url})\n\n"
        content += f"**{article.source}**"

        if article.published_at:
            content += f" | {article.published_at.strftime('%Y-%m-%d %H:%M')}"

        content += "\n\n"
        content += f"> {article.summary}\n\n"

        if article.tags:
            tags_str = ", ".join([f"`{tag}`" for tag in article.tags])
            content += f"{tags_str}\n\n"

        content += "---\n\n"

        return content

    def _create_page_content(self, report: DailyReport) -> str:
        """
        Create full page content as markdown.

        Args:
            report: DailyReport object

        Returns:
            Full markdown content
        """
        content = "# 今日の記事\n\n"
        for level in [ImportanceLevel.S, ImportanceLevel.A, ImportanceLevel.B]:
            count = report.articles_by_importance.get(level, 0)
            content += f"- {level.value} ランク記事： {count} 件\n"

        content += "\n---\n\n"

        # Add articles by importance level
        for level in [ImportanceLevel.S, ImportanceLevel.A, ImportanceLevel.B]:
            articles = [a for a in report.articles if a.importance == level]

            if articles:
                content += f"## {level.value} ランク記事\n\n"

                for article in articles:
                    content += self._format_article_content(article)

        return content

    def _parse_inline_markdown(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse inline markdown (bold, italic, code, links) to Notion rich_text format.

        Args:
            text: Text with inline markdown

        Returns:
            List of Notion rich_text objects
        """
        import re

        rich_text = []
        pos = 0

        # Pattern for inline markdown with named groups
        pattern = re.compile(
            r'(?P<bold>\*\*(?P<bold_text>.+?)\*\*)|'
            r'(?P<code>`(?P<code_text>[^`]+?)`)|'
            r'(?P<link>\[(?P<link_text>[^\]]+?)\]\((?P<link_url>[^\)]+?)\))|'
            r'(?P<italic>\*(?P<italic_text>.+?)\*)'
        )

        for match in pattern.finditer(text):
            # Add text before the match
            if match.start() > pos:
                before_text = text[pos:match.start()]
                if before_text:
                    rich_text.append({
                        "type": "text",
                        "text": {"content": before_text}
                    })

            # **bold**
            if match.group('bold'):
                rich_text.append({
                    "type": "text",
                    "text": {"content": match.group('bold_text')},
                    "annotations": {"bold": True}
                })
            # `code`
            elif match.group('code'):
                rich_text.append({
                    "type": "text",
                    "text": {"content": match.group('code_text')},
                    "annotations": {"code": True}
                })
            # [text](url)
            elif match.group('link'):
                rich_text.append({
                    "type": "text",
                    "text": {"content": match.group('link_text'), "link": {"url": match.group('link_url')}}
                })
            # *italic*
            elif match.group('italic'):
                rich_text.append({
                    "type": "text",
                    "text": {"content": match.group('italic_text')},
                    "annotations": {"italic": True}
                })

            pos = match.end()

        # Add remaining text after last match
        if pos < len(text):
            remaining = text[pos:]
            if remaining:
                rich_text.append({
                    "type": "text",
                    "text": {"content": remaining}
                })

        # If no matches found, return plain text
        if not rich_text:
            rich_text.append({
                "type": "text",
                "text": {"content": text}
            })

        return rich_text

    def _markdown_to_blocks(self, markdown: str) -> List[Dict[str, Any]]:
        """
        Convert markdown text to Notion block objects.

        Args:
            markdown: Markdown formatted text

        Returns:
            List of Notion block objects
        """
        blocks = []
        lines = markdown.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                i += 1
                continue

            # Code block (```)
            if stripped.startswith('```'):
                language = stripped[3:].strip() or "plain_text"
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                blocks.append({
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": '\n'.join(code_lines)}}],
                        "language": language
                    }
                })
                i += 1
                continue

            # Heading 1
            if stripped.startswith('# '):
                blocks.append({
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": self._parse_inline_markdown(stripped[2:])
                    }
                })
            # Heading 2
            elif stripped.startswith('## '):
                blocks.append({
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": self._parse_inline_markdown(stripped[3:])
                    }
                })
            # Heading 3
            elif stripped.startswith('### '):
                blocks.append({
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": self._parse_inline_markdown(stripped[4:])
                    }
                })
            # Bulleted list (- or *)
            elif stripped.startswith('- ') or stripped.startswith('* '):
                blocks.append({
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": self._parse_inline_markdown(stripped[2:])
                    }
                })
            # Numbered list
            elif len(stripped) > 2 and stripped[0].isdigit() and stripped[1] == '.' and stripped[2] == ' ':
                blocks.append({
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": self._parse_inline_markdown(stripped[3:])
                    }
                })
            # Quote (blockquote)
            elif stripped.startswith('> '):
                blocks.append({
                    "type": "quote",
                    "quote": {
                        "rich_text": self._parse_inline_markdown(stripped[2:])
                    }
                })
            # Callout (using > with emoji)
            elif stripped.startswith('>') and len(stripped) > 1 and stripped[1] != ' ':
                blocks.append({
                    "type": "callout",
                    "callout": {
                        "rich_text": self._parse_inline_markdown(stripped[1:].strip()),
                        "icon": {"emoji": "💡"}
                    }
                })
            # Divider
            elif stripped == '---' or stripped == '***':
                blocks.append({"type": "divider", "divider": {}})
            # To-do list
            elif stripped.startswith('- [ ] '):
                blocks.append({
                    "type": "to_do",
                    "to_do": {
                        "rich_text": self._parse_inline_markdown(stripped[6:]),
                        "checked": False
                    }
                })
            elif stripped.startswith('- [x] ') or stripped.startswith('- [X] '):
                blocks.append({
                    "type": "to_do",
                    "to_do": {
                        "rich_text": self._parse_inline_markdown(stripped[6:]),
                        "checked": True
                    }
                })
            # Regular paragraph
            else:
                blocks.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": self._parse_inline_markdown(stripped)
                    }
                })

            i += 1

        return blocks

    async def create_page(
        self,
        title: str,
        content: str,
        parent_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a Notion page using MCP.

        Args:
            title: Page title
            content: Page content (markdown)
            parent_id: Parent page ID

        Returns:
            Created page URL or None if failed
        """
        if not self.session:
            log.error("Not connected to Notion MCP server")
            return None

        parent_id = parent_id or self.parent_page_id
        if not parent_id:
            log.error("Parent page ID not configured")
            return None

        try:
            # Convert markdown to Notion blocks
            children_blocks = self._markdown_to_blocks(content)

            # Prepare arguments in correct Notion API format
            arguments = {
                "parent": {"page_id": parent_id},
                "properties": {
                    "title": [{"text": {"content": title}}]
                }
            }

            # Add children blocks if any
            if children_blocks:
                arguments["children"] = children_blocks

            # Call MCP tool to create page
            result = await self.session.call_tool(
                "API-post-page",
                arguments=arguments
            )

            # Extract page URL from result
            if result and result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        response_text = item.text
                        log.info(f"Page created successfully: {response_text[:200]}...")

                        # Try to parse JSON response
                        try:
                            response_data = json.loads(response_text)
                            if "url" in response_data:
                                return response_data["url"]
                            if "id" in response_data:
                                return f"https://notion.so/{response_data['id'].replace('-', '')}"
                        except json.JSONDecodeError:
                            pass

                        # Try to extract URL from text
                        import re
                        url_match = re.search(r'https://[^\s"]+', response_text)
                        if url_match:
                            return url_match.group(0).rstrip('",')
                        return response_text

            log.warning("Could not extract page URL from MCP response")
            return None

        except Exception as e:
            log.error(f"Failed to create Notion page via MCP: {e}")
            return None

    async def create_daily_report_page(
        self,
        report: DailyReport,
        parent_page_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a Notion page with the daily report using MCP.

        Args:
            report: DailyReport to publish
            parent_page_id: Parent page ID (defaults to configured parent)

        Returns:
            Created page URL or None if failed
        """
        if not self.session:
            log.error("Not connected to Notion MCP server. Call connect() first.")
            return None

        log.info("Creating Notion page for daily report via MCP")

        # Create page title and content
        page_title = self._create_page_title(report)
        page_content = self._create_page_content(report)

        # Create the page
        page_url = await self.create_page(
            title=page_title,
            content=page_content,
            parent_id=parent_page_id
        )

        if page_url:
            log.info(f"Successfully created Notion page via MCP: {page_url}")
        else:
            log.error("Failed to create Notion page via MCP")

        return page_url

    async def test_connection(self) -> bool:
        """
        Test Notion MCP server connection.

        Returns:
            True if connection successful, False otherwise
        """
        if not self.api_key:
            log.error("Notion API key not configured")
            return False

        try:
            log.info(f"Notion API key: {self.api_key}")
            await self.connect()

            if not self.session:
                return False

            # Try to list available tools
            tools = await self.session.list_tools()
            log.info(f"Available MCP tools: {[tool.name for tool in tools.tools]}")

            await self.disconnect()
            return True

        except Exception as e:
            log.error(f"Notion MCP connection test failed: {e}")
            await self.disconnect()
            return False
