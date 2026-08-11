# Assessment Terminal Log

## A. Setup output

```bash
docker-compose up --build
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py seed
```

```text
<PASTE_ACTUAL_SETUP_OUTPUT_HERE>
```

## B. Initial test run

```bash
docker-compose exec backend python -m pytest
docker-compose exec frontend npm test
```

```text
<PASTE_ACTUAL_INITIAL_TEST_OUTPUT_HERE>
```

## C. Bug curl proof BEFORE fix

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

```text
<PASTE_ACTUAL_BEFORE_FIX_CURL_OUTPUT_HERE>
```

## D. Same bug curl proof AFTER fix

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

```text
<PASTE_ACTUAL_AFTER_FIX_CURL_OUTPUT_HERE>
```

## E. Part 3c Airtable export demo

```bash
curl -sS -X POST "http://localhost:8000/api/projects/$PROJECT_ID/export" \
  -H "Authorization: Bearer $TOKEN" | jq
```

```text
<PASTE_ACTUAL_FIRST_AIRTABLE_EXPORT_OUTPUT_HERE>
```

## F. Second Airtable export proving no duplicates

```bash
curl -sS -X POST "http://localhost:8000/api/projects/$PROJECT_ID/export" \
  -H "Authorization: Bearer $TOKEN" | jq
```

```text
<PASTE_ACTUAL_SECOND_AIRTABLE_EXPORT_OUTPUT_HERE>
```

## G. Part 3a Comments demo

```bash
TASK_ID=$(curl -sS "http://localhost:8000/api/projects/$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.project.tasks[0].id')
curl -sS -X POST "http://localhost:8000/api/tasks/$TASK_ID/comments" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"body":"Assessment comments demo"}' | jq
curl -sS "http://localhost:8000/api/tasks/$TASK_ID/comments" \
  -H "Authorization: Bearer $TOKEN" | jq
```

```text
<PASTE_ACTUAL_COMMENTS_DEMO_OUTPUT_HERE>
```

## H. Final test run

```bash
docker-compose exec backend python -m pytest
```

```text
collected 42 items
projects/test_airtable_export.py ..........                              [ 23%]
projects/tests.py ........................                               [ 80%]
users/tests.py ........                                                  [100%]
======================= 42 passed, 16 warnings in 12.51s =======================
```

```bash
docker-compose exec frontend npm test
```

```text
Test Files  4 passed (4)
Tests  16 passed (16)
```

```bash
docker-compose exec frontend npm run build
```

```text
93 modules transformed.
dist/index.html                   0.41 kB | gzip:  0.28 kB
dist/assets/index-DG0oFOaN.css   10.50 kB | gzip:  2.87 kB
dist/assets/index-BYNmwral.js   224.16 kB | gzip: 69.54 kB
built in 2.47s
```

```bash
docker-compose exec backend python manage.py check
docker-compose exec backend python manage.py makemigrations --check --dry-run
```

```text
System check identified no issues (0 silenced).
No changes detected
```
