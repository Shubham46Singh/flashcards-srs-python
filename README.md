# Flashcards with Spaced Repetition

**Language:** Python (FastAPI) &nbsp;|&nbsp; **Needs:** Postgres + Redis

This is a **starter**. The application already works. Your job is everything
that gets it building, tested and running in CI.

---

## You do not need Python installed

You will build this into a container, and the container brings its own
Python 3.12. You are not being asked to extend the app — you are being asked
to ship it.

---

## 1. What this app needs

| | |
|---|---|
| **Runtime** | Python 3.12 |
| **Install dependencies** | `pip install -r requirements.txt` |
| **Start the app** | `uvicorn app.main:app --host 0.0.0.0 --port 8080` |
| **Listens on** | port 8080, bound to `0.0.0.0` |
| **Environment variables** | `DATABASE_URL`, `REDIS_URL` |
| **Needs running first** | Postgres, Redis, and the migrations applied |

### What it does

Decks of cards, and an algorithm that decides which of them you see today. Grade each card 0 to 5 as you answer it; SM-2 turns that grade into an interval, so a card you find easy drifts out to months and one you fumble is back tomorrow. The day's queue is built once and popped from as you revise.

### Endpoints

```
GET  /health
GET  /decks?user=demo                   every deck with new / due / mature counts
POST /study/{user}/start?deck_id=1      build today's queue (idempotent)
GET  /study/{user}/next                 peek at the next card
POST /study/{user}/answer  {"card_id":2,"grade":4}
GET  /study/{user}/due                  what is due, straight from the database
GET  /stats/{user}                      answers per study day
```

`/health` reports Postgres and Redis **separately**. If it says
`postgres: false` the app started fine and your compose wiring is wrong —
do not go looking in the application code.

### Migrations

`migrations/` holds `.sql` files applied **in filename order** before the app
starts. They create the tables and insert sample data. A container running
`psql` over them in order is enough; you do not need a migration tool.

---

## 2. What you must write

| File | What it has to do |
|---|---|
| `Dockerfile` | Install dependencies **before** copying source, pin the base image, do not run as root. |
| `docker-compose.yml` | App + Postgres + Redis + a migration step, one `docker compose up`. |
| `.circleci/config.yml` | lint → unit tests → integration tests → secret scan → image build |
| Unit tests | For `app/schedule.py`. No database, no network. |
| Integration tests | Against a real Postgres and Redis as CircleCI service containers. |

Then push your image to **your own Docker Hub account**, tagged `:1.0`.

### When it works

```bash
docker compose up --build
curl localhost:8080/health
```

```json
{"status":"ok","postgres":true,"redis":true}
```

---

## Where the marks are

`app/schedule.py` is **pure logic** — plain functions over plain data, no
database and no HTTP. Start your tests there. Use pytest:
`pytest --cov=app --cov-report=term-missing`. Minimum 70%.

This module is close to perfect for unit testing - pure arithmetic with sharp boundaries and a published specification. Start with `next_ease` at every grade, then prove the 1.3 floor holds after ten failures in a row. Then `study_day`: 23:58 and 00:02 on consecutive dates must return the SAME day, and 03:59 and 04:00 must not.

## Why Redis is here

Today's due-card queue, per user, keyed by the **study day**. Working out what is due is a join over every card and every row of progress; redoing it after each answer is both slow and wrong, because answering a card changes what is due and the list would reshuffle under you mid-session. So it is built once, popped from as you go, and expires by itself. A card you fail goes to the back of the same queue rather than waiting until tomorrow.

## The hard part

**A card answered at 11:58pm and again at 12:02am is two sessions by the clock but one by intent.** Revising past midnight is the normal case, not the edge case. If 00:02 counts as a new day then the same card is shown twice in four minutes, its interval is advanced twice, and the schedule quietly stops meaning anything. Decide where your day boundary is, put the study day in the cache key rather than the calendar date, and decide what a second answer within one sitting is allowed to change. Say what you chose and why.

Write your answer in your README. It is worth more marks than the feature.

---

## Getting unstuck

| Symptom | Almost always |
|---|---|
| `/health` says `postgres: false` | Wrong hostname. In compose the host is the **service name**, not `localhost`. |
| Page will not load, logs fine | No `ports:` mapping, or bound to `127.0.0.1` not `0.0.0.0`. |
| `relation "..." does not exist` | Migrations did not run, or the app started before they finished. |
| Build takes minutes each time | `COPY . .` is above your dependency install. |
| CI cannot reach the database | In CircleCI service containers the host **is** `localhost` — opposite of compose. |

---

---

## 3. Project Implementation

This project has been containerized, tested, and integrated with a CI pipeline using Docker, Docker Compose, PostgreSQL, Redis, pytest, Ruff, Gitleaks, and CircleCI.

### Docker Setup

The Dockerfile uses Python 3.12.12-slim as its base image. Dependencies are installed before copying the application source code to improve Docker layer caching. The application runs as a non-root user and listens on port 8080.

Docker Compose manages four services:

- **app:** Runs the FastAPI application.
- **db:** Runs PostgreSQL for persistent data storage.
- **redis:** Manages study queues and temporary session data.
- **migrate:** Applies SQL migration files before the application starts.

### Running the Application

Run the following command from the project directory:

```bash
docker compose up --build
```

Open the health endpoint:

```text
http://localhost:8080/health
```

Expected response:

```json
{
  "status": "ok",
  "postgres": true,
  "redis": true
}
```

### Testing

Unit tests are implemented in `tests/test_schedule.py` to verify the spaced repetition scheduling logic, including grade boundaries, ease factor calculations, and study-day behavior.

Integration tests are implemented in `tests/test_integration.py` to verify application behavior using real PostgreSQL and Redis services.

Run the tests and generate a coverage report:

```bash
python -m pytest --cov=app --cov-report=term-missing
```

The project was tested successfully with 28 unit tests and 10 integration tests. Coverage checks meet the required 70% threshold.

### CircleCI Pipeline

The CI pipeline is configured in `.circleci/config.yml` and runs the following jobs in order:

1. **Lint:** Checks Python code using Ruff.
2. **Unit Tests:** Runs pytest against the scheduling module.
3. **Integration Tests:** Tests the application using PostgreSQL and Redis service containers.
4. **Secret Scan:** Scans the Git repository using Gitleaks.
5. **Docker Image Build:** Builds the application container image.

All five jobs completed successfully in CircleCI Pipeline #2.

### Docker Hub

The application image is published on Docker Hub.

**Repository:** `diyaa02/flashcards-srs`

**Image tag:** `1.0`

Pull the image using:

```bash
docker pull diyaa02/flashcards-srs:1.0
```

Docker Hub repository:

https://hub.docker.com/r/diyaa02/flashcards-srs

## 4. Study-Day Boundary and Same-Session Repetition

### Why the study day starts at 04:00

The application uses a 04:00 study-day boundary instead of midnight because users may continue studying after 12:00 AM.

For example, a student reviewing flashcards at 11:58 PM and continuing at 12:02 AM should remain in the same study session.

With a 04:00 boundary:

- 11:58 PM and 12:02 AM belong to the same study day.
- 03:59 AM belongs to the previous study day.
- 04:00 AM begins the new study day.

This prevents the daily queue from resetting unnecessarily at midnight and keeps study progress consistent.

### Why Redis uses the study day

Redis stores the daily flashcard queue using a key containing the user and study day.

For example:

```text
queue:demo:2026-10-09
```

The queue is generated once for the study day and processed as the user answers cards. This prevents the application from recalculating and reshuffling the entire queue after every answer.

### How same-session repetition works

When a student fails a flashcard, it can be placed at the back of the same study queue for additional practice.

This allows the student to review difficult cards again without waiting until the following day.

The distinction between the daily study schedule and same-session practice is important: repeating a failed card should support learning without incorrectly treating the repeat as an entirely new study day.

When a flashcard is answered more than once within the same study day, the application records the new answer but does not advance its repetitions or review interval again. Only the ease factor is adjusted based on the new grade. This prevents multiple answers within one sitting from artificially increasing the long-term review interval. A failed card is returned to the end of the current Redis queue on its first answer of the day, allowing additional practice without treating it as a new study day.

### Design Decision

Using a 04:00 study-day boundary and a Redis queue keyed by study day makes the system more consistent for students who study late at night.

It prevents accidental queue resets at midnight, supports repeated practice of difficult flashcards, and helps preserve the intended spaced repetition schedule.