> [!WARNING]
> **Work in Progress**
>
> DebugMate is under active development. Features, APIs, data models, and
> architecture may change as the project evolves. This worker currently covers
> event normalization, fingerprinting, incident detection, OpenSearch event
> indexing, and relational incident storage.

## About DebugMate

DebugMate is an AI-powered observability assistant designed to help engineers
understand production issues faster.

Modern distributed systems generate a large volume of logs, infrastructure
events, and deployment notifications. DebugMate collects these events,
normalizes and groups similar occurrences, detects potential incidents, and
prepares the data needed for incident analysis.

The project is currently split across services:

- **debugMate-api** - Event ingestion API built with FastAPI.
- **debugMate-worker** - Background processing service responsible for event
  normalization, fingerprint generation, grouping, incident detection, and
  persistence.

## debugMate-worker

`debugMate-worker` is a Celery worker that consumes the event batches published
by `debugMate-api`, normalizes event messages, detects incident patterns,
indexes events into OpenSearch, and saves incidents plus event-to-incident
associations in PostgreSQL. It listens for the `process_events` task on the
shared Celery broker (Redis locally, SQS otherwise) and is the component that
writes to the data stores the API later reads from.

### Workflow

```text
Application logs
        |
        v
   debugMate-api
        |
        v
   Celery broker
   Redis locally / SQS outside local
        |
        v
 debugMate worker
        |
        +--> OpenSearch: normalized events
        |
        +--> PostgreSQL: incidents and event associations
```

The worker exposes a Celery task named `process_events`. For each incoming
batch it:

1. Validates raw event payloads with Pydantic models.
2. Normalizes volatile message values such as emails, URLs, UUIDs, IPs, tokens,
   paths, and numbers.
3. Creates deterministic event fingerprints from service, severity,
   environment, event type, and normalized message.
4. Fetches nearby stored events from OpenSearch to evaluate a wider time
   window.
5. Filters incident detection to `error` and `critical` events that are not
   already associated with an incident.
6. Detects incidents by fingerprint threshold first, then by
   environment/service threshold.
7. Indexes normalized events into OpenSearch.
8. Saves detected incidents and event associations to PostgreSQL.

Incident detection is threshold-based. Events are grouped first by fingerprint
and then by environment/service, and a group becomes an incident when it reaches
the configured threshold (`INCIDENT__FINGERPRINT_THRESHOLD` or
`INCIDENT__SERVICE_ENV_THRESHOLD`) within the configured time interval. When a
group spans longer than the interval, a sliding time window is used to carve out
qualifying bursts. Fingerprint incidents take precedence: events already claimed
by a fingerprint incident are excluded from environment/service detection, so an
event belongs to at most one incident per run.

## Project Layout

```text
app.py                         Celery task entrypoint
src/config/                    Pydantic settings and logging
src/core/events.py             Event normalization and fingerprinting
src/core/incidents.py          Incident detection rules
src/core/model/                SQLModel tables and OpenSearch index mappings
src/core/schemas/              Event and incident Pydantic models
src/services/celery/worker.py  Celery app factory
src/services/db/               PostgreSQL persistence client
src/services/search/           OpenSearch client
test/core/                     Unit tests for core event and incident logic
dependencies/                  Runtime dependency pins
dependencies/dev/              Development dependency pins
dev/                           Production Dockerfile
dev/local/                     Local Dockerfile
generate_events.py             Local sample event generator
```

## Configuration

Configuration is loaded from environment variables, with `.env` support via
`pydantic-settings`. Nested settings use `__` as the delimiter.

Start from `.env.example`:

```bash
cp .env.example .env
```

Important local settings:

```text
DEBUG=false
ENVIRONMENT=local
LOG_LEVEL=INFO

OPENSEARCH__URL=http://localhost:9200
OPENSEARCH__USERNAME=admin
OPENSEARCH__PASSWORD=admin
OPENSEARCH__USE_SSL=false
OPENSEARCH__VERIFY_CERTS=false
OPENSEARCH__SSL_ASSERT_HOSTNAME=false
OPENSEARCH__SSL_SHOW_WARN=false

CELERY__BROKER_URL=redis://localhost:6379/0
CELERY__TASK_NAME=process_events
CELERY__QUEUE_NAME=debugmate-queue

DB_URL=postgresql://user:password@localhost:5432/mydatabase
```

When `ENVIRONMENT=local`, Celery uses Redis as the broker. For non-local
environments, Celery uses SQS and expects AWS credentials plus queue settings
such as `AWS__ACCESS_KEY_ID`, `AWS__SECRET_ACCESS_KEY`, `AWS__REGION`,
`CELERY__QUEUE_NAME`, and `CELERY__QUEUE_URL`.

Incident detection can be tuned with:

```text
INCIDENT__TIME_INTERVAL=300
INCIDENT__FINGERPRINT_THRESHOLD=5
INCIDENT__SERVICE_ENV_THRESHOLD=10
```

## Local Setup

Create a virtual environment and install local plus development dependencies:

```bash
python3.13 -m venv venv
source venv/bin/activate
pip install -r dependencies/requirements-local.txt
pip install -r dependencies/dev/requirements-dev.txt
```

The worker expects reachable OpenSearch and PostgreSQL instances. In local mode,
it also expects a reachable Redis broker.

Run the worker:

```bash
celery -A app:celery_app worker --loglevel=INFO
```

## Data Stores

### OpenSearch

The OpenSearch client creates the event index on startup if it does not already
exist:

```text
debugmate-events
```

Index settings use `OPENSEARCH__INDEX_CONFIG__NUMBER_OF_SHARDS` and
`OPENSEARCH__INDEX_CONFIG__NUMBER_OF_REPLICAS`, defaulting to one shard and zero
replicas.

### PostgreSQL

The database client creates SQLModel tables on startup:

```text
incidents
events_in_incidents
```

Incidents are stored in `incidents`. Event membership is stored in
`events_in_incidents`, keyed by event UUID and incident ID.

## Sample Events

Generate a local JSON payload file with synthetic events:

```bash
python generate_events.py
```

By default this writes `generated_events.json` and includes repeated error or
critical bursts that should satisfy the default fingerprint incident threshold.

## Dependencies

Dependency pins are split by target:

```text
dependencies/requirements-base.txt    Shared runtime deps (Pydantic, OpenSearch, SQLModel, psycopg2)
dependencies/requirements-local.txt   Base + Celery with Redis broker
dependencies/requirements-prod.txt    Base + Celery with SQS broker (boto3)
dependencies/dev/requirements-dev.txt Tooling (pytest, ruff, mypy, pre-commit)
```

## Development Checks

Run formatting and linting:

```bash
ruff check .
ruff format .
```

Run type checking:

```bash
mypy
```

Run tests:

```bash
pytest test
```

The current test suite covers event normalization, fingerprint generation,
incident grouping, incident detection thresholds, and the public
`check_for_incidents` flow with fake OpenSearch and database clients.

Or install and run the configured pre-commit hooks:

```bash
pre-commit install
pre-commit run --all-files
```

## Docker

Production image:

```bash
docker build -f dev/Dockerfile -t debugmate-worker .
```

Local image:

```bash
docker build -f dev/local/Dockerfile -t debugmate-worker-local .
```
