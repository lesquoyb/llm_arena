# Variation between repetitions

The competition Summary includes **Variation between repetitions**. A point is
one preparation conversation/trajectory, not one message or provider request.
Select a model or round with the existing filters. Feedback and control tracks,
and different rounds, are always separate. Clicking a point opens its conversation.

## Performance and stability

Combat score is `(wins + 0.5 × draws) / completed fights`. Each row compares its
observed repetitions on the intersection of identical opponent **versions**, seed
and candidate starting side. Same-model opponents follow the overview's exclusions.
The selected tournament, fixed-baseline or previous-round category is respected.
Using the fixed baseline is preferable for comparisons across rounds, because a
changing tournament population changes the meaning of the score.

Every repetition receives equal weight. Missing submissions, failed engine fights,
unknown outcomes and unavailable seeds are never converted to zero scores. Coverage
and submission counts are shown; a partial run can have a very small common panel.
Coverage uses the configured repetition count under the current repetition filter,
including preparations that have not started yet. Invalid / checked excludes
strategies whose validation has not been reported.
This is a comparison conditional on the observed/evaluable repetitions, not proof
that failed or unfinished repetitions would have performed similarly.

The plot shows each repetition, the minimum–maximum line, the middle 50% box,
median and mean. Sample variance uses the sum of squared deviations divided by
`n − 1`; SD is its square root. SD/IQR for combat score are expressed in percentage
points, variance in squared percentage points. With fewer than two observations,
variance and SD are unknown. These spreads are not confidence intervals for a mean.

**Outcome disagreement** is the fraction of repetition pairs with different
win/draw/loss outcomes, averaged over their common fixtures. Two preparations can
both score 50% yet disagree on every fixture. Their average-score SD is zero but
their disagreement is 100%, revealing differences hidden by the mean.

## Other useful metrics

The Measure selector also plots preparation cost, recorded preparation time,
tool-call count and known token usage. These distributions use frozen submissions
with available measurements. They describe resource variability, not playing skill.
Submission coverage and invalid strategies remain visible separately. Existing
tool/compilation-error views are useful reliability measures alongside these scores.

Repeated calls inside a conversation are dependent: later calls use earlier work.
Later rounds in one repetition are dependent too. Measure dispersion within one
round/track; do not count every fight as another independent model sample. More
seeds refine each strategy's evaluation but do not increase the repetition count.
Observed spread still includes strategy–opponent/seed interactions. Isolating model
generation noise from combat randomness would require a balanced repeated-seed
experiment and a separate variance-component analysis.
Use the same provider model, prompt and generation parameters when interpreting
the result as model repeatability. Manual reasoning overrides or restarted attempts
can introduce additional configuration/selection effects; conversation provenance
is available from each point.

The chart uses compact results already loaded by Summary. It starts no model
requests, fights or replay downloads and recomputes when the selection changes.
