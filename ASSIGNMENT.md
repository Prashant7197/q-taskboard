# Senior Software Assignment — Fullstack (AI-Assisted)

## Overview

| | |
|---|---|
| **What** | Review the codebase, fix a critical bug, build the Airtable integration (Part 3c, required), and complete at least one of Part 3a or 3b. |
| **Time** | 90–100 minutes |
| **Submit within** | 24 hours after receiving this assignment |
| **AI tools** | Encouraged. Claude Code, Cursor, Aider, Cline, or similar. |
| **Prerequisites** | Docker, Python 3.12+, Node.js 20+ and PostgreSQL 15+. An Airtable account with a personal access token and a base ready to receive records (or equivalent credentials). Set this up before your session starts. |

Read each and every word of this document carefully before you start.

---

## Getting Started

1. Set up the project from the repo URL provided.
2. Start the app:
   ```bash
   docker-compose up --build
   docker-compose exec backend python manage.py migrate
   docker-compose exec backend python manage.py seed
   ```
3. Open **http://localhost:3000** and sign in with `meera@taskboard.dev` / `password123`
4. **Do not modify the seed data. Do not squash commits. We read your commit history.**

---

## About the Application

TaskBoard is a project management tool — think of a simplified Jira, Trello, or Linear. The app already has authentication, project CRUD, task CRUD, and a Kanban-style UI.

**Tech stack:**

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite 5, TypeScript 5 (strict) |
| Routing | React Router 6 |
| Data fetching | TanStack Query 5 |
| Styling | Tailwind CSS 3 |
| Frontend tests | Vitest 2 + Testing Library |
| Backend | Django 5, Django REST Framework 3 |
| Auth | JWT via djangorestframework-simplejwt (30-day tokens) |
| Database | PostgreSQL 16 |
| Backend tests | pytest-django |
| Container | Docker + docker-compose |

**What already exists:**

| Model | Description |
|-------|-------------|
| `User` | Email + password account, JWT-based sessions (30-day tokens) |
| `Project` | Has a name, description, and an owner |
| `Membership` | Links a user to a project with a role: `admin`, `member`, or `viewer` |
| `Task` | Belongs to a project; has a title, description, status (`todo` / `in_progress` / `review` / `done`), an optional assignee, and a position within its column |

---

## Your Tasks

### Part 1 — Code Review

Create a `REVIEW.md` listing the **top 4 issues** you find, prioritized by business impact.

For each issue include:

- File and line reference
- Category: `Security` / `Performance` / `Architecture` / `Data Integrity` / `Testing`
- Severity
- A 2–3 sentence description
- A recommended fix

For **at least 1 issue**, include a `curl` command and the response showing the bug in action.

---

### Part 2 — Fix the #1 Critical Issue

Pick your highest-priority issue and fix it. Submit:

- The fix as a commit
- Tests that prove it works
- A `curl` command showing the bug before, alongside the same `curl` showing the fix

---

### Part 3a — Build Task Comments *(complete at least one of 3a or 3b)*

Tasks can have a chronological comment thread where project members discuss the work.

**Must work:**
- Comments are listed chronologically, showing author, body, and when posted
- Project members can post; viewers can read but not post
- Comments are append-only — once posted, they cannot be edited or deleted
- Authorization must be enforced correctly at the Django API layer

---

### Part 3b — Build the Activity Feed *(complete at least one of 3a or 3b)*

Every meaningful change to a project (task created, status changed, assignee changed, comment added) leaves an audit record. The project detail page shows a chronological feed of recent activity.

**Must work:**
- The feed shows who did what, when, scoped to one project
- Only project members can read; recent activity is shown most recently first

**Design decision:** If the activity write fails, should the original change roll back? Pick an approach, implement it, and explain your reasoning in 2–3 sentences in your commit message or a `DESIGN_NOTES.md`. Your reasoning matters more than the choice itself.

---

### Part 3c — Bulk Export Tasks to Airtable *(Mandatory)*

Build a feature that exports all tasks for a project to a real Airtable base. At the end of the export, open your Airtable base and the tasks must be visible there.

**Must work:**
- A trigger from the project detail page that initiates the export
- Only project members (`admin` or `member`) can trigger the export
- A Django endpoint (`POST /api/projects/:id/export`) that fetches all tasks and pushes them to Airtable using real API calls via **`pyairtable`**
- The export must handle being run more than once gracefully (idempotent)
- Handle Airtable client errors gracefully: retry transient failures (rate limits, 5xx), do not retry permanent failures, do not fail the entire export if a single record fails

**Notes:**
- Assume up to ~1,000 tasks; synchronous is fine (async earns bonus credit)
- The export endpoint stub already exists at `POST /api/projects/:id/export` — implement the real logic there using `pyairtable` with your actual credentials
- If you'd rather integrate with Trello, Notion, or Linear instead of Airtable, that's fine — pick one and make real API calls

**Setup:** Add your credentials to `.env` before running the export:
```
AIRTABLE_API_KEY=your_personal_access_token
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX
AIRTABLE_TABLE_NAME=Tasks
```

---

## What to Submit

| Deliverable | Required |
|-------------|----------|
| Repository URL (full commit history, do not squash) | ✅ |
| `REVIEW.md` — code review with bug proof from the running app | ✅ |
| `TERMINAL_LOG.md` — in order: setup output · initial test run · bug curl proof · fix curl proof · Part 3c export demo (Airtable screenshot or share link + second run to show idempotency) · 3a/3b demo · final test run | ✅ |
| Part 3c with passing tests | ✅ |
| At least one of Part 3a or 3b with passing tests | ✅ |
| Both Part 3a and 3b | Bonus |
| Screen recording (Loom or similar) — narrate your thinking, keep terminal visible throughout. Include the link in `README.md` or `RECORDING.md`. **Submissions without a recording will not be evaluated.** | ✅ |

**Tip:** `script -a terminal_log.txt` captures your terminal session automatically.

---

## AI Tool Conversation Tracking

**This repository is configured to automatically capture your AI coding tool conversation history with each git commit.** This includes conversations from Claude Code, Cursor, Aider, Continue.dev, Cody, Cline, and Windsurf.

This is part of the evaluation process. We evaluate how you collaborate with AI tools — your prompting strategy, how you break down problems, and how you review AI suggestions.

**How it works:** A pre-commit git hook runs automatically before each commit. It copies conversation files from AI tool directories (e.g., `.claude/`, `.cursor/`) into `.ai-conversations/` and stages them with your commit. You don't need to do anything — it happens automatically.

**What's captured:** Only AI tool conversation logs stored in the project directory. No system files, browsing history, or anything outside this repository.

If you prefer a tool that doesn't store local conversations (like browser-based ChatGPT), the screen recording will capture your interactions instead.
