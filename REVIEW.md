# TaskBoard Production Code Review

## 1. Task search SQL injection bypasses the project boundary

- **Category:** Security
- **Severity:** Critical
- **File:** `backend/projects/views.py`
- **Lines:** 110-123, especially 114-120

The `q` query parameter and `project_id` are interpolated directly into a SQL string before it is executed. Although the endpoint first verifies membership in the project named in the URL, an attacker can alter the SQL predicate so that the query returns tasks belonging to every project. More destructive stacked SQL may also be accepted by the database driver, making the impact larger than cross-project disclosure.

An authenticated viewer is sufficient to exploit this. With the documented seed data, `dev@example.com` is a viewer of Q3 Launch but is not a member of Customer Onboarding Revamp. The injected search below returns tasks outside Q3 Launch, including onboarding tasks.

### Curl reproduction

Requires `curl` and `jq`; run against the documented seeded database.

```bash
# Authenticate as the seeded viewer.
TOKEN=$(curl -sS -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"dev@example.com","password":"password123"}' | jq -r '.token')

# Obtain the ID of the one project this viewer may access.
PROJECT_ID=$(curl -sS http://localhost:8000/api/projects \
  -H "Authorization: Bearer $TOKEN" | \
  jq -r '.projects[] | select(.name == "Q3 Launch") | .id')

# Escape the project filter through the injectable q parameter.
curl -sS --get "http://localhost:8000/api/projects/$PROJECT_ID/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "q=' OR 1=1) -- " | jq
```

**Expected behavior:** The query is treated as literal search text and returns no matches from Q3 Launch; no task from another project is disclosed.

**Actual behavior:** The API returns HTTP 200 with tasks from all projects, including Customer Onboarding Revamp tasks that the viewer is not authorized to access.

**Business impact:** Any user with membership in any single project can read task titles, descriptions, assignee IDs, creator IDs, workflow state, and timestamps across all tenants/projects. Direct SQL interpolation also places the entire application database at risk.

## 2. Any authenticated user can update any task by ID

- **Category:** Security
- **Severity:** High
- **File:** `backend/projects/views.py`
- **Lines:** 164-185

`TaskDetailView.patch` loads a task by its global UUID and immediately applies changes. Unlike the adjacent delete handler at lines 187-200, it never resolves the task's project membership and never calls `_can_edit_tasks`. A viewer can obtain task IDs from project detail responses, and task IDs exposed elsewhere can be used by authenticated non-members.

**Exploit/failure path:** Authenticate as seeded viewer `dev@example.com`, read a Q3 Launch task ID through the permitted project-detail endpoint, then send `PATCH /api/tasks/{task_id}` with a new title, status, description, or assignee. The request succeeds with HTTP 200 even though viewers are intended to be read-only. A user outside the project succeeds as well if they know the UUID.

**Business impact:** Unauthorized users can falsify task content, move work through workflow states, or change assignments. This undermines project isolation and auditability.

## 3. Task assignees are not required to belong to the task's project

- **Category:** Data Integrity
- **Severity:** High
- **File:** `backend/projects/views.py`
- **Lines:** 151-159 and 180-182
- **Related model:** `backend/projects/models.py`, lines 45-50

Both task creation and task update write a caller-supplied user UUID directly to `assignee_id`. The foreign key proves only that the user exists; neither path verifies that the user has a `Membership` for the task's project. The unrestricted PATCH described in issue 2 makes the update path even easier to abuse, but the defect also exists independently for otherwise-authorized admins and members creating tasks.

**Exploit/failure path:** A Q3 Launch member submits the UUID of a user who belongs only to another project (or to no project) as `assigneeId`. Django accepts the foreign key and saves the assignment. Invalid user IDs instead surface as an unhandled database integrity error rather than a controlled validation response.

**Business impact:** Projects can assign work to users who cannot access that work, leak user relationships across project boundaries, and accumulate inconsistent task/membership state. Malformed IDs can also turn client input into HTTP 500 responses.

## 4. An admin can demote the project's sole admin and orphan the project

- **Category:** Data Integrity
- **Severity:** Medium
- **File:** `backend/projects/views.py`
- **Lines:** 203-231, especially 222-229
- **Related model:** `backend/projects/models.py`, lines 18-29

The member endpoint doubles as a role-update endpoint. It allows an admin to update any existing membership—including their own—to `member` or `viewer`. There is no validation that the project retains at least one admin, and the database model has no invariant tying `Project.owner` to an admin membership.

**Exploit/failure path:** With the seed data, Meera is the only member/admin of Internal Tools Cleanup. If Meera posts her own email with role `viewer` to that project's members endpoint, the update succeeds. No remaining user can update or delete the project, add/promote members, or restore an admin through the API.

**Business impact:** A valid API call can leave a project permanently unmanageable, requiring database/operator intervention and breaking the ownership model.
