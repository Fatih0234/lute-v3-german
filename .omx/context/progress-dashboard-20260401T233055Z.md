# Context Snapshot
- task statement: Build a Lute progress dashboard with migrations, API routes, /progress UI, and nav integration.
- desired outcome: working end-to-end dashboard with tests and preserved legacy stats behavior.
- known facts/evidence: existing stats blueprint, Chart.js assets, wordsread legacy history, books/texts/words schema, page-read flow in lute/read/service.py.
- constraints: Flask + SQLAlchemy + SQLite, no new deps, keep existing /stats and book table stats working.
- unknowns/open questions: best migration placement for new models; whether to track page_open sessions in MVP.
- likely codebase touchpoints: lute/models, lute/db/schema, lute/read/service.py, lute/stats, lute/templates, lute/static, lute/app_factory.py, tests.
