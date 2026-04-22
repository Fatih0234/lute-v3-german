# PRD: Lute Progress Dashboard

## Problem
Lute exposes a legacy statistics page, but it does not provide a cohesive progress dashboard for reading streaks, book completion, vocabulary growth, and goal tracking.

## Goal
Ship a new `/progress` dashboard backed by normalized progress tables and JSON APIs while preserving existing `/stats` and book-list stats behavior.

## In Scope
- database migrations for `reading_sessions`, `goals`, `milestones`
- progress dashboard APIs under `/api/stats/*`
- new `/progress` page with charts and heatmap
- navigation integration
- tests for new service, routes, and read-flow integration

## Out of Scope
- goal creation/edit UI
- full vocabulary event history beyond existing `words` timestamps
- replacing the existing `/stats/` page in this iteration

## Users
- self-directed Lute learners who want to monitor daily reading consistency
- learners tracking vocabulary growth over time
- readers comparing progress across books

## Success Criteria
- `/progress` loads and shows streak, vocabulary, books, and heatmap data
- `/api/stats/overview`, `/books`, `/vocabulary`, `/streak` all return valid JSON
- marking a page as read writes normalized session data and preserves legacy history
- existing `/stats/` and `/book/table_stats/<id>` continue to work
