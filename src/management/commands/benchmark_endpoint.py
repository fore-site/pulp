import json
import platform
import resource
import statistics
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit

from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, reset_queries
from django.test import Client
from django.test.utils import CaptureQueriesContext


def percentile(values, percent):
    if not values:
        return None
    ordered = sorted(values)
    index = round((len(ordered) - 1) * (percent / 100))
    return ordered[index]


def summarize(samples):
    elapsed = [sample["elapsed_ms"] for sample in samples]
    queries = [sample["query_count"] for sample in samples]
    sql = [sample["sql_ms"] for sample in samples]

    return {
        "requests": len(samples),
        "status_counts": {
            str(status): sum(1 for sample in samples if sample["status_code"] == status)
            for status in sorted({sample["status_code"] for sample in samples})
        },
        "elapsed_ms": {
            "min": min(elapsed) if elapsed else None,
            "mean": statistics.fmean(elapsed) if elapsed else None,
            "median": statistics.median(elapsed) if elapsed else None,
            "p95": percentile(elapsed, 95),
            "p99": percentile(elapsed, 99),
            "max": max(elapsed) if elapsed else None,
        },
        "query_count": {
            "min": min(queries) if queries else None,
            "mean": statistics.fmean(queries) if queries else None,
            "median": statistics.median(queries) if queries else None,
            "max": max(queries) if queries else None,
        },
        "sql_ms": {
            "min": min(sql) if sql else None,
            "mean": statistics.fmean(sql) if sql else None,
            "median": statistics.median(sql) if sql else None,
            "p95": percentile(sql, 95),
            "p99": percentile(sql, 99),
            "max": max(sql) if sql else None,
        },
    }


def peak_rss_mb():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return rss / (1024 * 1024)
    return rss / 1024


class Command(BaseCommand):
    help = "Benchmark a Django endpoint with query counts, SQL time, response time, and memory."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default="/", help="Local URL path to benchmark, for example / or /books/deals")
        parser.add_argument("--requests", type=int, default=20, help="Number of measured warm-cache requests")
        parser.add_argument("--warmup", type=int, default=3, help="Warm-up requests before measured warm-cache runs")
        parser.add_argument("--cold-cache", action="store_true", help="Clear Django cache and record one cold-cache request")
        parser.add_argument("--host", default="pulp-3koe.onrender.com", help="HTTP host sent to Django's test client")
        parser.add_argument("--output", help="Optional JSON output path for raw benchmark results")

    def handle(self, *args, **options):
        path = self.clean_path(options["path"])
        requests = options["requests"]
        warmup = options["warmup"]

        if requests < 1:
            raise CommandError("--requests must be at least 1")
        if warmup < 0:
            raise CommandError("--warmup cannot be negative")

        client = Client(HTTP_HOST=options["host"])
        result = {
            "target": {
                "path": path,
                "host": options["host"],
            },
            "config": {
                "requests": requests,
                "warmup": warmup,
                "cold_cache": options["cold_cache"],
            },
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "peak_rss_mb_before": peak_rss_mb(),
            },
            "cold": None,
            "warmup": [],
            "warm": [],
        }

        if options["cold_cache"]:
            cache.clear()
            result["cold"] = self.measure_request(client, path)

        for _ in range(warmup):
            result["warmup"].append(self.measure_request(client, path))

        for _ in range(requests):
            result["warm"].append(self.measure_request(client, path))

        result["summary"] = {
            "cold": summarize([result["cold"]]) if result["cold"] else None,
            "warmup": summarize(result["warmup"]),
            "warm": summarize(result["warm"]),
        }
        result["environment"]["peak_rss_mb_after"] = peak_rss_mb()

        self.print_summary(result)

        if options["output"]:
            output_path = Path(options["output"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Wrote raw benchmark JSON to {output_path}"))

    def clean_path(self, path):
        parsed = urlsplit(path)
        if parsed.scheme or parsed.netloc:
            raise CommandError("Pass a local path such as / or /books/deals, not a full URL")
        if not path.startswith("/"):
            raise CommandError("Path must start with /")
        return path

    def measure_request(self, client, path):
        reset_queries()
        with CaptureQueriesContext(connection) as queries:
            started = perf_counter()
            response = client.get(path)
            elapsed_ms = (perf_counter() - started) * 1000

        sql_ms = 0.0
        for query in queries.captured_queries:
            try:
                sql_ms += float(query.get("time", 0)) * 1000
            except (TypeError, ValueError):
                pass

        return {
            "status_code": response.status_code,
            "elapsed_ms": elapsed_ms,
            "query_count": len(queries),
            "sql_ms": sql_ms,
            "content_bytes": len(response.content),
            "peak_rss_mb": peak_rss_mb(),
        }

    def print_summary(self, result):
        self.stdout.write(f"Benchmark target: {result['target']['path']} on host {result['target']['host']}")
        if result["cold"]:
            self.print_section("Cold cache", result["summary"]["cold"])
        self.print_section("Warm cache", result["summary"]["warm"])

    def print_section(self, title, summary):
        elapsed = summary["elapsed_ms"]
        queries = summary["query_count"]
        sql = summary["sql_ms"]
        self.stdout.write(
            (
                f"{title}: {summary['requests']} request(s), statuses={summary['status_counts']}, "
                f"elapsed mean={elapsed['mean']:.2f}ms p95={elapsed['p95']:.2f}ms, "
                f"queries mean={queries['mean']:.1f}, SQL mean={sql['mean']:.2f}ms p95={sql['p95']:.2f}ms"
            )
        )
