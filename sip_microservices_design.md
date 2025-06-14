# SIP System Design Document (Backend-Only, Microservices Architecture)

## 1. Objective

Design a scalable backend system for a Systematic Investment Plan (SIP) platform that supports 10 million users. The system must manage:

- User authentication
- SIP setup and execution
- Portfolio valuation
- NAV updates
- Charting/visibility
- Notifications

## 2. Architecture Overview

### 2.1 High-Level Components

```
+---------------------------+
|       API Gateway        |
| (GraphQL Federation)     |
+-----------+--------------+
            |
  +---------+----------+----------+----------+----------+
  | SIP Service | NAV Service | Portfolio Service | Graph Service | Notification Service
  +-------------+-------------+------------------+---------------+---------------------+
            |
  +---------+----------+----------+
  | Celery Task Queue / Kafka (Background Jobs)
  +-------------------------------+
            |
+----------------------------+
|      Data Layer (DBs)      |
| PostgreSQL / TimescaleDB   |
| Redis (caching)            |
+----------------------------+
```

### 2.2 Communication

- Inter-service: gRPC or REST (internal)
- External client: GraphQL
- Events: Kafka or Redis Streams for decoupled workflows

## 3. Microservices Design

### 3.1 Auth Service

- **Responsibility**: User registration, login, JWT issuance
- **Tools**: Supabase Auth or Auth0
- **Schema**:
  - `users(id UUID PK, username TEXT, email TEXT, created_at TIMESTAMP)`

### 3.2 SIP Service

- **Responsibility**: Create, modify, list SIPs
- **Endpoints**:
  - `createSIP(userId, schemeName, amount, startDate)`
  - `getSIPs(userId)`
- **Schema**:
  - `sips(id UUID PK, user_id UUID FK, scheme_name TEXT, monthly_amount INT, start_date DATE, created_at TIMESTAMP)`
- **Indexes**:
  - `BTREE on user_id`
  - `BTREE on scheme_name`

### 3.3 NAV Service

- **Responsibility**: Fetch/store NAVs from external APIs (AMFI/BSE), serve latest NAV
- **Endpoints**:
  - `getLatestNAV(schemeName)`
- **Schema**:
  - `navs(scheme_name TEXT, nav DECIMAL, date DATE, updated_at TIMESTAMP)`
- **Indexes**:
  - `BTREE on (scheme_name, date)`
  - `UNIQUE (scheme_name, date)`

### 3.4 Portfolio Service

- **Responsibility**: Calculate invested amount, current value, returns
- **Endpoints**:
  - `getPortfolio(userId)`
- **Schema**:
  - `investments(id UUID PK, user_id UUID, scheme_name TEXT, date DATE, amount DECIMAL, nav DECIMAL, units DECIMAL)`
  - `portfolio_snapshots(user_id UUID, date DATE, invested_value DECIMAL, current_value DECIMAL)`
- **Indexes**:
  - `BTREE on user_id`
  - `BTREE on (scheme_name, date)`

### 3.5 Graph Service

- **Responsibility**: Prepare graph data for visibility (pie, line, bar)
- **Endpoints**:
  - `getGraphData(userId, type)`
- **Schema**:
  - `visibility_graphs(user_id UUID, graph_type TEXT, config JSONB, created_at TIMESTAMP)`

### 3.6 Notification Service

- **Responsibility**: Email, SMS, Push alerts for SIP execution or NAV alerts
- **Queue-driven**: Listens for events from Celery or Kafka
- **Schema**:
  - `notifications(id UUID PK, user_id UUID, type TEXT, status TEXT, payload JSONB, created_at TIMESTAMP)`

## 4. Task Schedulers

### 4.1 Tools

- **Celery** (with Redis broker and result backend)
- **APScheduler** (lightweight jobs)
- **Kafka** (for event-driven workflows)

### 4.2 Scheduled Jobs

| Task                  | Frequency        | Responsible Service    |
| --------------------- | ---------------- | ---------------------- |
| NAV fetch & update    | Daily            | NAV Service            |
| SIP execution         | Monthly          | SIP Service via Worker |
| Portfolio snapshots   | Hourly           | Portfolio Service      |
| Notification dispatch | Realtime (event) | Notification Service   |

## 5. Caching Strategy

### Tools

- **Redis** (clustered)

### Cached Data

| Cache Key                | Value                       | TTL    |
| ------------------------ | --------------------------- | ------ |
| `nav:{scheme_name}`      | latest NAV                  | 24h    |
| `portfolio:{user_id}`    | snapshot summary            | 15 min |
| `graph:{user_id}:{type}` | pre-aggregated graph config | 30 min |

## 6. Indexing Strategy

### Postgres / TimescaleDB Indexes

- `sips`: `user_id`, `scheme_name`
- `navs`: `scheme_name, date`
- `investments`: `user_id`, `scheme_name`
- `portfolio_snapshots`: `user_id, date`

### Redis Keys (Logical)

- Use consistent key prefixes for service separation
- Store computed summaries, invalidate on mutation

## 7. Visibility & Observability

### Tools

- **Prometheus + Grafana** for metrics
- **Jaeger** for distributed tracing
- **ELK or Loki** for logs
- **Sentry** for error tracking

### Key Metrics

| Metric                | Description                  |
| --------------------- | ---------------------------- |
| API latency per route | Response time breakdown      |
| Job execution time    | SIP/NAV background task time |
| Cache hit rate        | Redis usage efficiency       |
| DB query times        | Performance of core queries  |
| Queue size            | Backpressure detection       |

---

## Summary

This backend design supports scalability, isolation of concerns, and extensibility. Each microservice owns its schema and logic and can scale independently. Background tasks handle heavy-lifting operations like SIP executions and NAV syncs, and Redis improves read performance with caching. Observability tools ensure reliability for 10M+ users at scale.

