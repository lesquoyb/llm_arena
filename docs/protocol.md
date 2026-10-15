# Experiment protocol

The experiment measures models writing, debugging and improving Leek Wars combat
strategies under controlled documentation and shared game rules. Preparation
limits are optional; unrestricted runs measure final quality alongside the
resources each model actually consumed. It measures programming
and strategy in this environment, not general coding ability.

This document records the protocol rationale. See the [implementation status](implementation-status.md)
and [complete workflow](complete-experiment.md) for delivered behavior.

## Runtime and scope

Use LeekScript 4 with the pinned official generator, not the Leek Wars website
frontend. Python and JavaScript strategies are possible later extensions;
TypeScript is outside scope. The game injects its functions and constants.
Native Windows and Linux use Java 25 and Gradle 9.3.1. The unused Linux polyglot
binary is excluded from the LeekScript build.

Polyglot per-turn timeouts and LeekScript operation budgets are different limits.
The 5-second safeguard and three allowed timeouts concern the optional polyglot
path. LeekScript uses entity cores for its operation budget. A whole-process
timeout is an infrastructure safeguard, not a loss assigned to a participant.
See the [engine audit](engine-audit.md).

## Experimental units

Identify a strategy by exact model, language, repetition, generation and feedback
condition. Each repetition starts an independent conversation. Later generations
continue its history with the same context policy. Pin engine, game data,
compiler, prompts and documents by version and hash.

Declare the team-building mode: shared teams/equipment or participant-selected
team size, per-member code and equipment under common level/slot/allowlist rules.
Per-member builds may differ. Realistic mode uses pinned official capital
allocation rules without components; free mode permits raw experimental stats. Initial demos use symmetric 2-vs-2 teams sharing an
entry point; a script can choose different roles through the API. Additional
scenarios should be reported separately. Deliverables are source folders with
a declared entry point, frozen and hashed on submission or at an explicitly configured deadline. Do not manually select
the best repetition or repair invalid final code outside the declared policy.

All participants receive the same preparation tools and local documentation.
They cannot read competitor folders, provider keys or held-out evaluation seeds.
Submitted code needs resource limits and execution isolation. Infrastructure
failures follow a recorded retry policy; compilation and strategy runtime errors
remain observed outcomes.

## Budgets and usage

Limit model calls, tool calls, preparation tests, elapsed time, cumulative input
and billable output tokens, and cost. Publish the budget remaining at each call.
Use exact model IDs, supported parameters, dated prices and raw usage receipts.
Treat reasoning tokens according to the provider contract to avoid double counting.

Token counts from different tokenizers are not a universal work unit. Report
token-budget and equal-cost comparisons separately. Track local infrastructure
costs separately from provider API costs. Missing usage or prices stay unknown.
Reservations are conservative estimates and cannot guarantee billing across
all providers. Unknown remote outcomes must not be retried blindly.

## Match schedule

Separate preparation, feedback and held-out final seeds and scenarios. For every
pair, play the same seeds in both positions, including strategies from different
repetitions of the same model. Check what swapping sides changes in placement
and initiative. Self-matches are separate mirror diagnostics.

With N strategies and S seeds, a ranked round robin in two positions contains
`N * (N - 1) * S` matches. Exact deterministic repeats do not add independent
information; use distinct seeds/scenarios for evaluation and deliberate repeats
for determinism checks.

## Improvement and feedback

After initial strategy, clone each conversation and source checkpoint into two paired branches:

- Control: an improvement request without match results.
- Feedback: the same request and budget, plus bounded structured results and logs.

Both retain equal preparation rights. Opponent source code remains hidden in the
main condition. A separate disclosure condition could measure that effect later.
Freeze every submission before running the next tournament.

Evaluate new strategies against contemporaries, frozen initial strategies and fixed
handwritten controls. Use common opponents and scenarios to compare control and
feedback; changing contemporary rankings alone do not measure progress. Hold
final evaluation seeds out of preparation tools. Report improved strategy costs and cumulative
trajectory costs without charging shared initial strategy calls twice in actual experiment totals.

## Analysis

Report matrices, wins/draws/losses, validity, missing submissions, failures and
mean score `(wins + 0.5 * draws) / completed matches`. Weight models, conversations
and scenarios explicitly. Retain same-model matches in the matrix and identify
them in aggregates. Elo is optional; matrices remain necessary when strategies
form cycles.

Use independent conversations as the primary resampling unit. Keep paired sides
and fixtures together. Hundreds of matches from one script do not replace
independent generations. Small pilots produce exploratory estimates, not a
stable model ranking. Scores conditional on surviving submissions must be
separated from generation success rates; predeclare any penalty policy.

Report operation counts, game resource use, elapsed time, errors and limits.
CPU and memory measurements require separate instrumentation and controlled
hardware; elapsed time is not CPU time. Prefer performance/budget curves and
cost/performance frontiers over a single quality/price quotient.

## Pilot and cost control

A technical pilot can start with three models and three conversations each.
Nine strategies on ten seeds require 720 ranked matches plus 90 mirrors if
enabled. Improvement branches and reference panels add more matches; use the planner.
Three conversations per model are insufficient for a definitive ranking.
Choose available exact model IDs and authorize paid calls explicitly. Configure
a spending limit only when it is part of the intended comparison or cost control.

Keep stable prompt prefixes, verify actual cache usage, index local documents,
page logs and bound returned feedback. Cache matches only by source, engine,
configuration and seed after validating determinism. Batch APIs help independent
calls when supported; tool loops still require multiple orchestration steps.

Sources reviewed on 13 October 2026: [generator](https://github.com/leek-wars/leek-wars-generator),
[polyglot guide](https://github.com/leek-wars/leek-wars-generator/blob/master/POLYGLOT_PORTING_GUIDE.md)
and [LeekScript](https://github.com/leek-wars/leekscript).
