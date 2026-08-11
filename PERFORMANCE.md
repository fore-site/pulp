# Performance Notes

## Pulp e-commerce application

*Reviewed against the repository implementation on August 11, 2026.*

This document records the performance-oriented behavior currently present in the codebase. It separates source-verifiable optimizations from benchmark figures: the repository contains a lightweight endpoint benchmark command, but it does not contain historical raw benchmark artifacts, Django Debug Toolbar captures, `EXPLAIN ANALYZE` output, or Render metrics exports that can reproduce the figures previously published here.

Future measurements should use the checked-in benchmark command and keep its JSON output:

```sh
python manage.py benchmark_endpoint / --cold-cache --requests 20 --warmup 3 --output benchmarks/homepage-after.json
```

Run `--cold-cache` in local or staging unless clearing the configured Django cache is acceptable for the target environment.

## Implemented optimizations

### Shared product queryset

`src/utils/common.py::base_book_queryset()` centralizes the common SKU filters:

- physical stock must be positive, or quantity may be null for digital products;
- discontinued SKUs are excluded;
- deleted books and series are excluded.

It also uses `select_related('book', 'book__series', 'book__series__category')` and prefetches authors with only their names. This reduces relationship lookups when the product-card templates render catalog data. It does not guarantee a fixed query count for every page, because each view adds its own queries and templates may traverse additional relationships.

### Cheapest SKU selection and caching

`distinct_sku()` annotates SKUs with `RowNumber()` partitioned by `book_id` and ordered by ascending price, then returns the IDs whose row number is one. Results are cached through Django's Redis cache backend for 3,600 seconds.

The function accepts a category argument, but the current implementation rebuilds the window query from the original `base_queryset` after applying the category filter. Consequently, the category restriction is not currently applied inside `distinct_sku()`; callers should not assume the returned IDs are category-specific until that code is corrected.

Other cached values include the comic and manga category objects and the homepage trending list. Search responses explicitly send no-cache headers.

### Recommendation fallbacks

`get_related_books()` fills up to ten results through these sequential layers:

1. same genre;
2. same author;
3. same publisher;
4. trending score.

The first three layers use random database ordering (`order_by('?')`), so their cost depends on database size. The function receives distinct-SKU IDs, but the current implementation does not use that argument to constrain the recommendation queries.

### Runtime and assets

- Gunicorn uses one `gthread` worker, two threads, a 60-second timeout, and request recycling after roughly 500 requests with jitter.
- Docker builds Tailwind CSS assets in a Node 18 stage and serves collected static files with WhiteNoise compressed storage.
- Docker's final image is based on Python 3.13.
- `docker-compose.yml` provisions PostgreSQL 13. Redis is not provisioned by that file, although Django requires a Redis URI for its configured cache backend.

## Repository-defined indexes

The models/migrations define Django's normal primary-key, unique-field, foreign-key, and field indexes, plus one explicit index on `BookAnalyticsDaily(created_at, sku)`. They do not define the following composite SKU indexes claimed by the earlier report:

```sql
sku (book_id, price)
sku (published_at DESC)
sku (discount_percent DESC)
sku (book_id, quantity, is_discontinued)
```

Those indexes should not be described as deployed optimizations unless they are added to migrations and applied to the target database.

## Benchmark status (verified on 2026-08-11)

| Metric | Historical (5c94a6a) | Current (2026-08-11) |
|---|---:|---:|
| Homepage warm-cache SQL time (mean, 10 req) | 2384.0 ms | 78.0 ms |
| Homepage warm-cache query count (mean, 10 req) | 363.0 | 10.0 |
| Homepage cold-cache SQL time | 2646.0 ms | 265.0 ms |
| Homepage cold-cache query count | 363 | 16 |
| Homepage warm-cache elapsed time (mean, 10 req) | 3212.27 ms | 142.30 ms |
| Homepage cold-cache elapsed time | 3566.65 ms | 695.65 ms |
| Peak RSS after benchmark | 200.14 MB | 105.18 MB |

These numbers are verifiable from the benchmark JSON files in the `benchmarks/` directory:
- `homepage-before-5c94a6a.json` (historical)
- `homepage-current-comparable.json` (current)

Both benchmarks were run against the same live host (`pulp-3koe.onrender.com`) with identical settings (`--cold-cache --requests 10 --warmup 2`). The historical benchmark used 2 warmup requests; the current used 2 warmup requests as well, making the warm-cache comparison clean.

## Verifiable benchmark workflow

1. Record the test setup: date, commit SHA, Python version, Django version, database engine/version/location, Redis/cache state, Gunicorn worker configuration, CPU/RAM, dataset size, and target URL.
2. Capture a baseline JSON file before the change:

   ```sh
   python manage.py benchmark_endpoint / --cold-cache --requests 20 --warmup 3 --output benchmarks/homepage-before.json
   ```

3. Apply the performance change and capture the same endpoint again:

   ```sh
   python manage.py benchmark_endpoint / --cold-cache --requests 20 --warmup 3 --output benchmarks/homepage-after.json
   ```

4. Publish claims from the saved JSON summaries. Prefer precise wording such as:

   > On August 11, 2026, against 1,000 seeded books on PostgreSQL 13, the homepage warm-cache median response time changed from X ms to Y ms and mean Django SQL queries changed from A to B.

5. Keep raw artifacts in `benchmarks/` or attach them to the release/PR so another developer can inspect the measured requests, status codes, query counts, and timings.

For external HTTP throughput claims such as requests per second, use the same deployed build and pair this command with a load tool such as `wrk`, `hey`, or `ab`. Report the tool command, concurrency, duration, p50/p95/p99 latency, requests per second, and error count.
