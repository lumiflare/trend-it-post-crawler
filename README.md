# Trend IT Post Crawler

日本の最新ITトレンドを自動収集・分析するマルチエージェントシステム

## 概要

主要な技術ブログから「今日の人気記事」を毎日自動収集し、AI（Claude）を使って要約・分析し、Markdownレポートを生成するシステムです。

## アーキテクチャ

マルチエージェントシステムとして設計されており、各エージェントが特定のスキル（ツール/関数）を持ち、役割を分担します。

### エージェント構成

```
┌─────────────────────────────────────────────────────┐
│           Orchestrator Agent (Manager)              │
│  • Asyncio Task Management                          │
│  • Error Logging & Retry Logic                      │
│  • Workflow Coordination                            │
└──────────────┬──────────────────────────────────────┘
               │
       ┌───────┴────────┬─────────────┐
       ▼                ▼             ▼
┌─────────────┐  ┌─────────────┐  ┌──────────────┐
│  Scraper    │  │  Analyst    │  │  Reporter    │
│   Agent     │→ │   Agent     │→ │   Agent      │
└─────────────┘  └─────────────┘  └──────────────┘
│                │               │
│ Skills:        │ Skills:       │ Skills:
│ • Playwright   │ • Claude API  │ • Markdown
│ • BeautifulSoup│ • Analysis    │ • Notion MCP
│ • FeedParser   │               │
└────────────────┴───────────────┴────────────────┘
```

#### 1. **Orchestrator Agent (Manager)**
- **役割**: ワークフロー全体の管理、各Sub-agentの呼び出し
- **Skills**: Asyncio Task Management, Error Logging, Retry Logic

#### 2. **Scraper Agent (Collector)**
- **役割**: WebサイトまたはRSSからの情報収集
- **Skills**: Playwright (動的サイト), BeautifulSoup (静的サイト), FeedParser (RSS)
- **タスク**: 設定ファイルで定義されたURLから記事のURL・タイトル・本文を取得

#### 3. **Analyst Agent (Processor)**
- **役割**: AIを使ったコンテンツの理解と分析
- **Skills**: Claude API Client
- **タスク**:
  - 要約: エンジニア向けに3行で要約（日本語）
  - タグ抽出: 技術スタック（例: Rust, Next.js, AWS）を抽出
  - 重要度判定: トレンド度合いをS/A/Bで判定

#### 4. **Reporter Agent (Publisher)**
- **役割**: レポートの整形と配信
- **Skills**: Markdown formatting, Slack Webhook, Notion MCP
- **タスク**: 分析結果をMarkdownにまとめ、ファイル保存、Slack配信、Notion子ページ作成

## プロジェクト構造

```
trend-it-post-crawler/
├── src/
│   ├── agents/              # エージェント実装
│   │   ├── orchestrator.py  # ワークフロー管理
│   │   ├── scraper.py       # 記事収集
│   │   ├── analyst.py       # AI分析
│   │   └── reporter.py      # レポート生成・配信
│   ├── skills/              # スキル（ツール）実装
│   │   ├── scraping_skills.py   # スクレイピング
│   │   ├── llm_skills.py        # LLM連携
│   │   ├── notion_mcp_skills.py # Notion統合（MCP経由）
│   │   └── publishing_skills.py # レポート配信
│   ├── utils/               # ユーティリティ
│   │   ├── logger.py        # ロギング
│   │   └── retry.py         # リトライロジック
│   └── models/              # データモデル
│       └── article.py       # 記事データ構造
├── config/                  # 設定ファイル
│   ├── sources.yaml         # 収集対象サイト定義
│   └── settings.py          # アプリ設定
├── output/                  # レポート出力先
├── logs/                    # ログファイル
├── main.py                  # メインエントリーポイント
├── requirements.txt         # Python依存関係
├── Dockerfile              # Dockerイメージ定義
├── docker-compose.yml      # Docker構成
└── README.md               # このファイル
```

## セットアップ

### 1. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、必要な情報を設定します。

```bash
cp .env.example .env
```

`.env` ファイルを編集:

```env
# 必須: Anthropic API Key
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# モデル設定（デフォルト: claude-sonnet-4-5-20250929）
# Claude Sonnet 4.5 - Anthropic最新の最も高性能なモデル（コーディングとエージェントに最適）
# 注意: 正しいモデル名を使用してください。存在しないモデル名を指定するとエラーになります
MODEL_NAME=claude-sonnet-4-5-20250929

# 注意: 環境変数名は NOTION_API_KEY（pydantic settings用）
# 内部的に notion-mcp-server には NOTION_TOKEN として渡されます
NOTION_API_KEY=your_notion_integration_token_here
NOTION_PARENT_PAGE_ID=your_notion_parent_page_id_here
```

#### Notion統合のセットアップ

このプロジェクトはNotion統合に **MCP (Model Context Protocol)** を使用しています。

**前提条件:**
- Node.js がインストールされていること（MCP Notion サーバーの実行に必要）

**セットアップ手順:**

1. **Node.js のインストール確認**
   ```bash
   node --version  # v18以上を推奨
   ```

2. **Notionインテグレーションの作成**
   - https://www.notion.so/my-integrations にアクセス
   - 「新しいインテグレーション」を作成
   - API Keyをコピーして `.env` の `NOTION_API_KEY` に設定

3. **親ページの準備**
   - Notionで「IT Trend」などの親ページを作成
   - ページのURLから親ページIDを取得（例: `https://notion.so/xxxxx` の `xxxxx` 部分）
   - `.env` の `NOTION_PARENT_PAGE_ID` に設定

4. **インテグレーションの接続**
   - 親ページの右上「...」メニュー → 「接続」
   - 作成したインテグレーションを選択して接続

5. **接続テスト**
   ```bash
   # Docker環境（推奨）
   docker compose run --rm crawler python test_notion_connection.py

   # ローカル環境
   python test_notion_connection.py
   ```

6. **ページ作成テスト**
   ```bash
   # Docker環境（推奨）
   docker compose run --rm crawler python test_notion_publish.py

   # ローカル環境
   python test_notion_publish.py
   ```

これで、毎日新しい子ページが自動作成されます！

**MCPについて:**
- MCP (Model Context Protocol) は AI アプリケーションとサービスを統合するための標準プロトコルです
- `@notionhq/notion-mcp-server` パッケージは自動的にダウンロードされます（初回実行時に `npx` が自動取得）
- 直接 Notion API を呼び出すよりも、より安全で保守しやすい実装になっています

### 2. Docker環境での実行（推奨）

#### ビルド

```bash
docker compose build
```

#### 実行（1回のみ）

```bash
docker compose run --rm crawler
```

#### 定期実行（毎日実行）

スケジューラーサービスを使用:

```bash
docker compose --profile scheduler up -d
```

これで毎日0時（UTC）にクローラーが自動実行されます。

#### Dockerビルドでエラーが出る場合

ディスク容量不足の場合:
```bash
# ビルドキャッシュをクリア
docker builder prune -af
```

### 3. ローカル環境での実行

#### 依存関係のインストール

```bash
# Python 3.10+ が必要
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Playwright ブラウザのインストール
playwright install chromium
```

#### 実行

```bash
python main.py
```

#### オプション

```bash
# ファイル保存のみ（Notion配信なし）
python main.py --no-notion

# Notionのみに配信（ファイル保存なし）
python main.py --no-file

# ログレベルの変更
python main.py --log-level DEBUG
```

## 収集対象サイト

`config/sources.yaml` で定義されています。デフォルトでは以下のサイトから収集します:

- **Qiita Trend**: トレンド記事
- **Zenn Trend**: トレンド記事
- **Note IT Category**: ITカテゴリーの記事
- **Hatena Blog Technology**: テクノロジーカテゴリー
- **DevelopersIO**: Classmethod技術ブログ（RSS）
- **Publickey**: 技術ニュース（RSS）
- **ICS Media**: フロントエンド技術ブログ（RSS）

### カスタマイズ

`config/sources.yaml` を編集して、収集対象サイトを追加・変更できます:

```yaml
sources:
  - name: "Your Blog"
    url: "https://example.com/tech"
    type: "html"  # or "rss"
    method: "playwright"  # or "requests", "feedparser"
    selectors:
      article_list: "article"
      article_link: "a"
      article_title: "h2"
    max_articles: 10
    enabled: true
```

## 出力

### 1. Markdownレポート

`output/` ディレクトリに以下の形式で保存されます:

```
output/daily_report_20251229_090000.md
```

レポートには以下が含まれます:
- 収集日時
- 記事総数
- 重要度別の記事数（S/A/B）
- 各記事の詳細（タイトル、要約、タグ、重要度）

### 2. Notion統合

Notion MCP（インテグレーション）を設定している場合、毎日新しい子ページが自動作成されます。

**Notionページの構成:**
- **親ページ**: IT Trend（手動で作成）
  - **子ページ**: Y年m月d日（自動作成）

**ページの特徴:**
- 見出し、引用、リンクを含む美しい構成
- 記事タイトルはクリック可能なリンク
- 技術タグの自動抽出（インラインコードで表示）
- 重要度別のグループ化
- 毎日自動で新しいページが追加される

**対応しているマークダウン記法:**
- `# 見出し1`, `## 見出し2`, `### 見出し3`
- `- リスト` (箇条書き)
- `1. 番号付きリスト`
- `> 引用`
- `---` (区切り線)
- `**太字**`, `*斜体*`
- `` `インラインコード` ``
- `[リンクテキスト](URL)`
- `- [ ] ToDo`, `- [x] 完了`
- コードブロック（```言語名）

## カスタマイズ

### 分析条件の変更

`src/skills/llm_skills.py` の `_create_analysis_prompt()` メソッドを編集して、AI分析のプロンプトをカスタマイズできます。

### 重要度の基準

- **S**: 業界に大きな影響を与える重要なニュース
- **A**: 注目すべき技術トレンドや実用的な情報
- **B**: 参考になる一般的な技術情報

### スクレイピング設定

`.env` ファイルで以下を調整できます:

```env
SCRAPING_TIMEOUT=30              # タイムアウト（秒）
MAX_CONCURRENT_SCRAPES=5         # 同時スクレイピング数
MAX_RETRY_ATTEMPTS=3             # リトライ回数
```

## トラブルシューティング

### Playwright のエラー

```bash
# ブラウザを再インストール
playwright install --force chromium
```

### API Rate Limit

Claude APIのレート制限に達した場合、`.env` で以下を調整:

```env
MAX_CONCURRENT_ANALYSES=1  # 同時分析数を減らす
```

## ライセンス

MIT License

## 開発者向け

### ログの確認

```bash
# Docker環境
docker compose logs -f crawler

# ローカル環境
tail -f logs/app.log
```

### デバッグモード

```bash
python main.py --log-level DEBUG
```

### テスト実行

**Notion接続テスト:**

```bash
# Docker環境（推奨）
docker compose run --rm crawler python test_notion_connection.py

# ローカル環境
python test_notion_connection.py
```

**Notionページ作成テスト:**

```bash
# Docker環境（推奨）
docker compose run --rm crawler python test_notion_publish.py

# ローカル環境
python test_notion_publish.py
```

**個別エージェントのテスト:**

```python
from src.agents import ScraperAgent

scraper = ScraperAgent()
articles = await scraper.run()
print(f"Collected {len(articles)} articles")
```
