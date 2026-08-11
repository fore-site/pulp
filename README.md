# Pulp — Comic & Manga Bookstore

Pulp is a Django e-commerce application for comics and manga. It provides catalog browsing, search, HTMX-powered interactions, cart and checkout flows, Paystack payments, and order tracking.

Live deployment: [pulp](https://pulp-3koe.onrender.com/)

## Features

### Shopping

- Product and series browsing for comics and manga
- Search by title, author, or ISBN
- Sorting and filtering by price, genre, publisher, and discount on supported listings
- HTMX cart updates, checkout updates, and partial listing refreshes
- User accounts, session-backed guest carts, and cart merging on login
- Paystack payment initialization, callback verification, and webhook handling
- Order history, order lookup, and order details

### Catalog and recommendations

- New releases, bestsellers, hot deals, and trending sections
- Product recommendations with fallback layers: same genre, same author, same publisher, then trending books
- Product-view events recorded in `BookEvent` and daily analytics aggregation used to update trending scores
- Multiple SKU formats, publishers, inventory quantities, discounts, and discounted-price calculation

### Frontend

- Django templates with HTMX and vanilla JavaScript
- Tailwind CSS 4 built through the `theme/static_src` PostCSS pipeline
- Responsive, touch-aware product interactions
- ARIA labels and keyboard-friendly controls in the templates

## Tech stack

| Layer | Implementation |
|---|---|
| Backend | Django, Python |
| Database | PostgreSQL (PostgreSQL 13 in `docker-compose.yml`) |
| Frontend | Django templates, HTMX, Tailwind CSS, vanilla JavaScript |
| Payments | Paystack API |
| Deployment | Docker and Gunicorn |
| Caching | Django Redis cache backend, configured through `REDIS_URI` |
| Static files | WhiteNoise compressed static storage |

The Python and Django packages are intentionally not pinned in `requirements.txt`; the Docker image currently uses Python 3.13. The version badges in older versions of this document were therefore more specific than the repository configuration supports.

## Performance-related implementation

- `base_book_queryset()` applies inventory/deletion filters and uses `select_related()` for the book, series, and category relationships.
- Authors are prefetched with a restricted queryset.
- `distinct_sku()` uses a `RowNumber()` window function to select the lowest-price SKU per book and caches the resulting IDs for one hour.
- Category objects, trending results, and distinct-SKU ID lists are cached.
- Gunicorn is configured for one `gthread` worker with two threads and request recycling.
- Database indexes defined in the repository are limited to the daily analytics model's `(created_at, sku)` index plus Django's field/unique indexes. The repository does not define the composite SKU indexes described in the historical performance report.

The repository includes a lightweight endpoint benchmark command, but it does not include captured profiler output or historical raw benchmark artifacts. Exact query counts, timings, and memory figures should therefore be reported only from fresh benchmark JSON generated for the target dataset and environment. See [PERFORMANCE.md](PERFORMANCE.md) for the source-backed report and measurement caveats.

## Benchmarking

Use the checked-in benchmark command before making performance claims:

```sh
python manage.py benchmark_endpoint / --cold-cache --requests 20 --warmup 3 --output benchmarks/homepage-after.json
```

The command records status codes, response times, Django SQL query counts, SQL time, response size, and process peak RSS for one optional cold-cache request plus measured warm-cache requests. Run it against the same dataset and environment before and after a change, then base README or release-note claims on the saved JSON files. Because `--cold-cache` clears the configured Django cache, use it in local or staging environments unless you intentionally want to clear production cache.

Example before/after workflow:

```sh
python manage.py benchmark_endpoint / --cold-cache --requests 20 --warmup 3 --output benchmarks/homepage-before.json
# apply the performance change
python manage.py benchmark_endpoint / --cold-cache --requests 20 --warmup 3 --output benchmarks/homepage-after.json
```

For public benchmark claims, report the command, date, commit, dataset size, cache state, database location, Python/Django versions, worker configuration, and the raw JSON artifact path.

## Local development

Create a `.env` file with the database settings used by `config/settings.py` (`DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `REDIS_URI`, and `DEV_SECRET_KEY`). Paystack flows also require `PAYSTACK_TEST_SECRET_KEY`.

With Docker Compose:

```sh
docker compose up --build
```

The web service runs migrations, collects static files, and starts Gunicorn on port 8000. The application expects PostgreSQL and Redis to be available; Redis is configured in Django but is not declared as a service in the checked-in `docker-compose.yml`.

Run the Django test suite with:

```sh
python manage.py test
```
