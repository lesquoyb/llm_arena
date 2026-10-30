# JVM tuning for repeated arena fights

The native pooled default is now `throughput`: `-Xms32m -Xmx512m
-XX:+UseSerialGC -XX:TieredStopAtLevel=1`. Slots retain the 32-request recycling default,
configurable with `ARENA_JVM_RECYCLE_MATCHES`. Idle slots still close after
30 seconds. Isolated processes retain the previous startup preset.

## Measurements

Measured on Linux x86-64, Oracle HotSpot 25.0.5.0.3, with four CPU cores available
through the container quota. These are engine benchmarks without LLM or network
calls, not forecasts for a Windows host. Exact results and options are saved in
[jvm-benchmark.json](jvm-benchmark.json).

Forty-eight CPU-oriented level-300 fights, four concurrent JVM slots, three seeds:

| Preset | Seconds | Fights/min | Java CPU seconds | Retained JVM RSS, total |
|---|---:|---:|---:|---:|
| Previous startup / default GC | 12.38 | 232.6 | 47.57 | 1,470 MiB |
| Full JIT / default GC | 25.29 | 113.9 | 99.12 | 2,132 MiB |
| Full JIT / Serial GC / 32 MiB initial heap | 20.50 | 140.5 | 79.32 | 1,306 MiB |
| C1 / Serial GC | 10.48 | 274.7 | 39.64 | 1,579 MiB |
| **Selected: C1 / Serial GC / 32 MiB initial heap** | **10.87** | **264.9** | **41.37** | **1,185 MiB** |

The selected preset improves measured throughput by about 14% and reduces retained
RSS by about 19% relative to the previous startup preset. The slightly faster
large-initial-heap variant was not selected because each concurrent slot consumes
additional memory. Separate screening used eight-turn fights and 1,000-turn draws.
Every tested option preserved replay hashes and deterministic metrics; elapsed
nanoseconds were excluded from those comparisons.

C2 is not universally faster here. Each request intentionally gets fresh game and
compiler classes to isolate mutable statics and player code. JVM/JDK code and
infrastructure warm up across requests, but compiled game methods are not simply
kept alive as they would be in an ordinary server with one permanent classloader.
C2 can therefore spend CPU optimizing code that is discarded after that fight.
More expensive/longer strategies can have a different tradeoff: use `optimizing`
to test full tiered JIT with Serial GC and two compiler threads, or `full` for the
unmodified HotSpot defaults. No single preset is asserted to win for every script.

A separate 40-fight mixed run compared 32-request recycling with 256-request
recycling using the selected preset and one worker. It measured 24.74 versus
26.74 seconds and sampled peak RSS of 573 versus 739 MiB. This single comparison
does not establish a universal optimal lifetime, but provides no basis for
increasing the default. The longer lifetime remains an explicit local experiment.

## What the upstream sources say

The pinned [generator README](https://github.com/leek-wars/leek-wars-generator/blob/b99a174dd938260d9e47b2e65a208cb32230e26e/README.md)
and [Dockerfile](https://github.com/leek-wars/leek-wars-generator/blob/b99a174dd938260d9e47b2e65a208cb32230e26e/Dockerfile)
document standalone execution and largely use JVM defaults. They do not publish a
production GC/JIT recipe or enough server deployment information to infer one.

[LeekScript's compiler](https://github.com/leek-wars/leekscript/blob/8152f399faf7b418bbc5b2216d755c3822cda23b/src/main/java/leekscript/compiler/JavaCompiler.java)
has signature-checked compiled-class caches backed by soft references. Our current
per-request classloader isolation does not preserve that game/compiler cache
between fights; enabling such reuse would require a separate state-isolation and
source-versioning change, not just another JVM flag.

[AI.checkRamOverflow](https://github.com/leek-wars/leekscript/blob/8152f399faf7b418bbc5b2216d755c3822cda23b/src/main/java/leekscript/runner/AI.java)
uses `System.gc()` when checking tracked script RAM. `DisableExplicitGC` is
therefore deliberately absent: disabling those calls can alter script failures.
No engine operation limits, RAM limits, source validation or timeouts were removed.

The [JDK 25 GC guide](https://docs.oracle.com/en/java/javase/25/gctuning/)
and [Java option reference](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html)
explain the throughput/latency tradeoff and compiler-thread ergonomics. A worker
runs one fight at a time with a small heap, so Serial GC avoids multiplying GC
threads across many independent JVMs. Full JIT compiler threads are bounded only
in the optional `optimizing` preset, not by imposing a cap on arena fight workers.
`AlwaysPreTouch` and fixed large initial heaps are not enabled: their memory and
startup cost multiplies with slot count. The heap limit is not a whole-process
memory limit; class metadata, JIT code and native stacks also contribute to RSS.

## Reproduce on your machine

After the normal engine setup:

```sh
python scripts/benchmark_engine.py --profiles startup throughput optimizing full --matches 64 --workers 4
```

Choose `--workload short`, `long` or `compute` instead of the default mixed set.
`--recycle 32` versus `--recycle 256` compares process lifetimes. Use a new `--out`
directory to keep results. The tool records cold starts, per-profile flags, CPU
seconds, sampled peak RSS when supported, and replay equality. It bypasses the
reference replay cache and never calls a model provider. Repeat in different
profile orders and at the worker count you actually intend to use.

Set `ARENA_JVM_PROFILE` to `startup`, `throughput`, `optimizing` or `full` before
starting the app. JVM options and recycling limits are runtime provenance:
resuming can change tuning without discarding prior fights or treating it as a
new game engine. Earlier and later artifacts retain their actual JVM settings.

Set `ARENA_JVM_RECYCLE_MATCHES=0` before starting the web server to disable periodic JVM replacement. Slots are then reused until shutdown, idle eviction or an engine failure; garbage collection continues normally. The default remains 32 because the measured longer lifetime increased peak retained memory. Recycling replaces a JVM process; it is not a garbage collection cycle. Compare throughput and memory on your workload before choosing a longer lifetime.

## Throughput plateaus

**Activity → Engine performance** (also in **More**) reads small telemetry files,
without auditing all fights. Copy the report after a slow and a fast interval.
Samples are appended every five seconds and retained in
`fight-performance-history.jsonl` with an 8 MB rotation limit.

The coordinator dispatches jobs to real Python OS threads. Each fight runs in a
separate JVM process, independently of Python's GIL. Completed results move into
a bounded publication queue, freeing compute slots before their result is saved.
The coordinator alone updates the journal and standings.

Useful distinctions in the copied data:

- `computing_workers` versus `publication_queue`: unfinished tasks versus completed
  results awaiting publication. A configured worker count is not CPU utilization.
- `python_cpu_cores` versus `coordinator_cpu_cores`: process and coordinator CPU
  seconds divided by sample wall time. 1.0 means one fully occupied logical core,
  not 100% of the whole machine. Python workers may also spend time in native code.
- `verification_seconds`, `verification_cache_flush_seconds`,
  `standings_report_seconds` and `journal_publication_seconds`: result checks,
  cached proofs, reporting and journal publication.
- `java_process_seconds` and `java_cpu_seconds`: JVM elapsed versus CPU time for
  completed requests. `script_execution_seconds` is time reported for AI turns;
  it excludes other engine work and cannot isolate compilation by subtraction.
- `jvm_output_check_seconds`: time checking output file sizes while waiting for
  the JVM. The existing output size limit and polling frequency are unchanged.
- `io_delta`: JSON reads/parsing/writes, hash reads/computation and Windows atomic
  replace backoffs. These measure this worker process, not physical disk traffic.
- `cpu_capacity`: GIL status and process affinity. Windows affinity refers to the
  processor mask exposed by GetProcessAffinityMask.

Phase and I/O durations sum overlapping work across threads and completed jobs.
They must not be added together as wall-time percentages. Samples can span JVM
startup, recycling and different opponents, so compare their phase breakdown as
well as fight/turn/operation rates. Low MB/s does not rule out metadata latency,
sharing violations, paging or antivirus activity; these are hypotheses until
supported by measurements. No antivirus exclusions or OS priorities are changed.

### Reproduce a slow competition fight

Activity > Engine performance lists the slowest fights of the current batch,
including their artifact directories and Java/script/CPU durations.
To isolate engine capacity from scheduling and changing strategies, repeat one
archived fight outside the competition (no provider calls and no result edits):

```sh
python scripts/benchmark_engine.py --fight-artifact "PATH/TO/MATCH" --profiles throughput --matches 32 --workers 1
python scripts/benchmark_engine.py --fight-artifact "PATH/TO/MATCH" --profiles throughput --matches 32 --workers 8
```

Each invocation writes a separate benchmark directory. Frozen sources and the
original scenario and seed are checked before execution. Compare wall time,
throughput and JVM CPU/RSS on this identical workload. Run the benchmark while
the competition is stopped to avoid competing for resources. Increasing workers
without increasing throughput indicates a shared capacity limit; it does not
by itself identify which resource is limiting. Java CPU far below Java wall time
suggests waiting or preemption; script time measures elapsed turn execution,
not CPU time, and can include pauses.
