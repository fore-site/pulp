# Recommended for low-memory environments: 1 worker only
workers = 1

# Threads allow concurrency without the heavy memory cost of a new process
threads = 2

# The 'gthread' worker is a good default when using threads
worker_class = 'gthread'

# Restart workers after a few hundred requests to prevent gradual memory leaks
max_requests = 500
max_requests_jitter = 50

# A conservative timeout to avoid hanging processes
timeout = 60