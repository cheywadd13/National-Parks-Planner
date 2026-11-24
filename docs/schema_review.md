# Relational design review

## Catalog evidence

The inspected server is PostgreSQL 17.11. The snapshot used repeatable-read
isolation with transaction_read_only set to on. Full definitions are retained
in reports/catalog.json.

| Relation | Grain and primary key | Foreign keys | Existing indexes |
| --- | --- | --- | --- |
| parks | One reporting record, park_code | None | Unique B-tree on park_code |
| visitation | One park-year-month, (park_code, year, month) | park_code references parks | Unique composite B-tree on the PK |
| weather | One point-based park-year-month, (park_code, year, month) | park_code references parks | Unique composite B-tree on the PK |

The primary keys enforce uniqueness and NOT NULL on their key columns.
Both FKs are validated. They use default NO ACTION referential behavior.
No separate UNIQUE or domain CHECK constraints were found. Non-key columns
are nullable. There is no FK between weather and visitation. This permits
weather-only months and preserves their independent coverage.

## Functional dependencies and normal forms

The intended dependencies are:

- park_code determines park_name, state, latitude, and longitude.
- (park_code, year, month) determines recreation_visits.
- (park_code, year, month) determines avg_temp_c, total_precip_mm, and total_snowfall_cm.

No measurement depends only on park_code, year, or month individually.
The monthly relations therefore have no intended partial-key or transitive
non-key dependencies and satisfy 3NF under these semantics. The catalog and
data can support these assumptions but cannot prove all future business rules.

The parks.state column stores values such as CA,NV and ID,MT,WY. If state means
a membership in a state or territory, these encode multiple values in one cell.
Under that interpretation the complete current design cannot be certified as
strict 3NF because the state membership representation needs 1NF decomposition.
Treating the value as an indivisible display label is possible, but limits
relational filtering and state-level integrity.

The proposed decomposition retains parks, removes state membership from it,
and adds state(state_code PK, state_name) and
park_state(park_code FK, state_code FK, PK(park_code, state_code)).
The app could reconstruct the current display string through string_agg.
The proposed ERD is in proposed_normalization.mmd.

## Proposed improvements for owner review

| Priority | Proposed change | Rationale and tradeoff |
| --- | --- | --- |
| P1 | Normalize park_state membership | Supports exact state joins and membership FKs, requires a migration and app query adjustment |
| P1 | Add month BETWEEN 1 AND 12 checks | Reject impossible monthly keys at the persistence layer |
| P1 | Add nonnegative visit, precipitation and snow checks, including finite floating values | Complements the application validator and prevents invalid future loads |
| P1 | Require names and coordinates where the inventory guarantees them | Existing values pass, optional records or future geographic uncertainty need a defined policy |
| P1 | Use a dedicated SELECT-only application role | The inspected connection has INSERT, UPDATE and DELETE privileges even though transactions are read-only |
| P2 | Retain source artifacts, retrieval timestamps, model/timezone/units and ETL run hashes | Enables historical reproducibility and investigation of revised source data |
| P2 | Model source-code mappings separately | Makes SEQU + KICA to SEKI aggregation explicit and permits dated mapping changes |
| P3 | Consider year-leading indexes only after workload measurement | The existing PK indexes support park-specific ranges and FK lookups; nationwide year filters have a different leading column |

The representative ACAD history query was measured with EXPLAIN ANALYZE and
BUFFERS. Its exact plan is in reports/query_plans.json. One execution is a
diagnostic sample, with cache and server-load effects. Full scans can be
appropriate for tables with about sixteen thousand rows. An additional
park_code-only index would duplicate the leading prefix of the existing PKs.

## Relationships and reporting choices

A park may have zero or many rows in each monthly relation. Each monthly row
belongs to exactly one park. Matching weather and visitation keys create an
optional one-to-one analytical relationship, without implying shared coverage
or a direct FK. A single wide table would repeat names and coordinates and make
source coverage harder to represent independently.

SEKI is one inventory record for a combined reporting series. Source visitation
counts are summed across SEQU and KICA. Individuals visiting both parks can
contribute to both component statistics. Weather represents a single point.
Inventory counts must be described as park records.

## Access observations

RLS is disabled for the three inspected tables. This audit does not establish
whether anonymous REST access is allowed, because that depends on grants and
API roles outside the inspected app connection. Review those grants before a
public deployment. A read-only app transaction limits accidental writes during
this session; a dedicated least-privilege role would enforce that boundary
across sessions. All role, RLS, schema and index changes remain proposals.

PostgreSQL documents key enforcement and FK behavior in its constraints guide.
[PostgreSQL 17 constraints](https://www.postgresql.org/docs/17/ddl-constraints.html)
