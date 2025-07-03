#!/usr/bin/env python3

import time
import random
import os
import sys
from datetime import datetime, timezone

# Initial values
total = random.randint(50, 120)
failed = 0
retries = random.randint(1, 30)
queue_lag = random.randint(5, 15)

# Read from env or CLI
output_path = os.getenv("LOG_FILE")
if len(sys.argv) > 1:
    output_path = sys.argv[1]

output_file = open(output_path, "a") if output_path else None

def log_line(msg: str):
    print(msg, flush=True)  # always print to console
    if output_file:
        output_file.write(msg + "\n")
        output_file.flush()

while True:
    total += random.randint(1, 3)
    if random.random() < 0.4:
        failed += 1
    retries = max(0, retries + random.randint(-2, 2))
    queue_lag = max(0, queue_lag + random.randint(-3, 4))

    msgs = f"[{datetime.now(timezone.utc).isoformat()}] MESSAGES: total={total}; failed={failed}; retries={retries}; queue_lag={queue_lag}ms;"
    log_line(msgs)
    jobs = f"[{datetime.now(timezone.utc).isoformat()}] JOBS: total={total}; failed={failed}; retries={retries}; queue_lag={queue_lag}ms;"
    log_line(jobs)

    time.sleep(random.uniform(2.0, 8.0))
