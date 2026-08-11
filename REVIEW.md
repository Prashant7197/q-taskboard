# TaskBoard Production Code Review

## 1. Task search SQL injection bypassed the project boundary

- **File and line:** `backend/projects/views.py`, baseline lines 110-123 (the corrected search path is now lines 115-125)
- **Category:** Security
- **Severity:** Critical

The baseline implementation interpolated `q` directly into raw SQL after checking membership only for the project in the URL. An authenticated member or viewer could alter the predicate and retrieve tasks from projects they could not access.

**Recommended fix:** Use parameterized ORM filters, retain the server-side project-membership check, and add a regression test using the original injection payload.

### Curl proof

```bash
TOKEN=$(curl -sS -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"dev@example.com","password":"password123"}' | jq -r '.token')

PROJECT_ID=$(curl -sS http://localhost:8000/api/projects \
  -H "Authorization: Bearer $TOKEN" | \
  jq -r '.projects[] | select(.name == "Q3 Launch") | .id')

curl -sS --get "http://localhost:8000/api/projects/$PROJECT_ID/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "q=' OR 1=1) -- " | jq
```

Before the fix, the response included tasks from Customer Onboarding Revamp; after the fix, the payload is treated as literal search text and returns `{"tasks":[]}`.

## 2. Any authenticated user can update any task by ID

- **File and line:** `backend/projects/views.py`, lines 165-186
- **Category:** Security
- **Severity:** High

`TaskDetailView.patch` loads a task by UUID and applies changes without checking membership in the task's project or the caller's role. A viewer with a visible task ID—or any authenticated outsider who obtains one—can change task content, status, or assignment.

**Recommended fix:** Resolve membership through `task.project_id` before applying changes and allow updates only for project admins and members, with viewer and outsider regression tests.

## 3. Task assignees are not required to belong to the project

- **File and line:** `backend/projects/views.py`, lines 151-160 and 180-183; `backend/projects/models.py`, lines 45-50
- **Category:** Data Integrity
- **Severity:** High

Task creation and update assign the caller-provided UUID directly to `assignee_id`; the foreign key verifies that the user exists but not that they belong to the task's project. This permits cross-project assignments and can produce unhandled integrity errors for invalid IDs.

**Recommended fix:** Validate that a non-null assignee has a membership in the task's project before saving and return a controlled 400 response for invalid or ineligible assignees.

## 4. An admin can demote the project's sole admin

- **File and line:** `backend/projects/views.py`, lines 244-272; `backend/projects/models.py`, lines 18-29
- **Category:** Data Integrity
- **Severity:** Medium

The member endpoint permits an admin to change any existing membership, including their own, to `member` or `viewer` without ensuring another admin remains. Demoting the sole admin leaves the project without anyone able to manage membership, update it, or delete it.

**Recommended fix:** Reject role changes that would leave a project with no admin and preserve an explicit invariant between project ownership and administrative membership.
