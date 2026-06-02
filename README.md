> [!WARNING]
> **Work in Progress**
>
> DebugMate is currently under active development. Features, APIs, data models, and architecture may change as the project evolves. The current implementation represents an early MVP focused on event ingestion, event processing, incident detection, and AI-assisted incident analysis.

## About DebugMate

DebugMate is an AI-powered observability assistant designed to help engineers understand production issues faster.

Modern distributed systems generate a large volume of logs, infrastructure events, and deployment notifications. DebugMate collects these events, normalizes and groups similar occurrences, detects potential incidents, and generates concise summaries to help engineers identify the most likely root causes.

The project is currently being developed as a collection of microservices:

- **debugMate-api** — Event ingestion API built with FastAPI.
- **debugMate-worker** — Background processing service responsible for event normalization, fingerprint generation, grouping, incident detection, and AI-powered analysis.

### MVP Goals

The initial version focuses on:

- Receiving application and infrastructure events
- Normalizing event messages
- Grouping related events using fingerprints
- Detecting incidents based on event patterns and thresholds
- Storing events in OpenSearch
- Generating AI-assisted incident summaries

### Example Workflow

```text
Application Logs
        |
        v
   FastAPI API
        |
        v
       SQS
        |
        v
 Celery Workers
        |
        +--> OpenSearch (events and incidents)
        |
        +--> AI Analysis

## debugMate-worker
`debugMate-worker` is a Celery worker that consumes event batches, normalizes
event messages, detects incident patterns, and persists both events and
incidents to OpenSearch.

## What It Does

The worker exposes a Celery task named `process_events`. For each incoming batch
it:

1. Validates raw event payloads with Pydantic models.
2. Normalizes volatile message values such as emails, URLs, UUIDs, IPs, tokens,
   paths, and numbers.
3. Creates deterministic event fingerprints from service, severity,
   environment, event type, and normalized message.
4. Looks for incidents among current events plus nearby stored events.
5. Indexes normalized events into OpenSearch.
6. Indexes detected incidents into OpenSearch.
7. Updates event documents with their associated incident IDs.

Incident detection currently focuses on error and critical events. It creates
incidents when enough events share either the same fingerprint or the same
service/environment within the configured time window.

## Project Layout

```text
app.py                         Celery task entrypoint
src/config/                    Pydantic settings and logging
src/core/events.py             Event normalization and fingerprinting
src/core/incidents.py          Incident detection rules
src/core/schemas/              Event and incident Pydantic models
src/services/celery/worker.py  Celery app factory
src/services/search/           OpenSearch client and index mappings
test/core/                     Unit tests for core event and incident logic
dependencies/                  Runtime dependency pins
dependencies/dev/              Development dependency pins
dev/                           Production Dockerfile
dev/local/                     Local Dockerfile
```

## Configuration

Configuration is loaded from environment variables, with `.env` support via
`pydantic-settings`. Nested settings use `__` as the delimiter.

Start from `.env.example`:

```bash
cp .env.example .env
```

Important settings:

```text
ENVIRONMENT=local
LOG_LEVEL=INFO

OPENSEARCH__URL=http://localhost:9200
OPENSEARCH__USERNAME=admin
OPENSEARCH__PASSWORD=admin
OPENSEARCH__USE_SSL=false
OPENSEARCH__VERIFY_CERTS=false

CELERY__BROKER_URL=redis://localhost:6379/0
CELERY__TASK_NAME=process_events
CELERY__QUEUE_NAME=debugmate-queue
```

When `ENVIRONMENT=local`, Celery uses Redis as the broker. For non-local
environments, it uses SQS and expects the AWS and queue-related settings to be
provided.

## Local Setup

Create a virtual environment and install local plus development dependencies:

```bash
python3.13 -m venv venv
source venv/bin/activate
pip install -r dependencies/requirements-local.txt
pip install -r dependencies/dev/requirements-dev.txt
```

Run the worker:

```bash
celery -A app:celery_app worker --loglevel=INFO
```

The worker expects a reachable OpenSearch instance. In local mode, it also
expects a reachable Redis broker.

## OpenSearch Indexes

The OpenSearch client creates these indexes on startup if they do not already
exist:

```text
debugmate-events
debugmate-incidents
```

Index settings use `OPENSEARCH__INDEX_CONFIG__NUMBER_OF_SHARDS` and
`OPENSEARCH__INDEX_CONFIG__NUMBER_OF_REPLICAS`, defaulting to one shard and zero
replicas.

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
`check_for_incidents` flow with a fake OpenSearch client.

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
