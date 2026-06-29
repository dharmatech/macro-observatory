# Signal Engine

Status: draft

The Signal Engine is a proposed Macro Observatory component for finding notable conditions in the datasets that the site already collects and publishes. The first version should be a quiet front-page summary, not a push-notification system.

Macro Observatory began with Fed Net Liquidity. That formula led naturally to its component systems: the Treasury General Account, reverse repo operations, and the Federal Reserve balance sheet. Each component is worth exploring, but daily manual review eventually becomes too much information. The Signal Engine should help with the monitoring phase by surfacing unusual conditions that deserve human attention.

## Purpose

Macro Observatory supports two modes of use:

- Learning mode: inspect datasets, drill into components, compare history, and build intuition.
- Monitoring mode: revisit the system regularly and ask whether anything unusual happened.

The Signal Engine is for monitoring mode. It should not replace the exploratory pages. It should point users back to those pages when something unusual is detected.

The initial user-facing feature can be a front-page section tentatively called Notable Observations. On ordinary days it may simply say that no notable observations were found. When a signal fires, the summary should show a short explanation and link to the relevant page.

## Scope

The first Signal Engine design should focus on:

- computing signals from local cached and derived datasets,
- publishing a static summary artifact during the site build,
- rendering a concise front-page summary,
- supporting conservative, explainable rules,
- backtesting rules before they are enabled,
- giving each signal enough context to inspect the underlying chart or table.

Signal delivery is a separate future concern. Email, SMS, social posting, paid alerts, and other push channels should not be part of the first implementation.

## Vocabulary

A candidate signal is a rule under investigation. Candidate rules can be backtested, tuned, or rejected without appearing on the public site.

A published signal is a rule that is allowed to appear in the static front-page summary.

An alert is a future push notification. Alerts should have a higher bar than published signals because push delivery creates interruption and alert fatigue.

A signal event is one specific observation produced by a rule for a dataset, series, and date.

## Rule Families

The rule catalog should grow slowly. The first rules should be conservative and easy to explain.

### Level Rules

Level rules inspect the value itself.

Examples:

- all-time high,
- all-time low,
- highest value in 6 months,
- lowest value in 1 year,
- value crosses a configured threshold.

Raw all-time high rules can be noisy for series that trend upward by construction. Eligibility rules and suppression are required before enabling them broadly.

### Change Rules

Change rules inspect the first difference, similar to velocity.

Examples:

- largest daily increase in 6 months,
- largest weekly decrease in 1 year,
- top 1% absolute daily move,
- daily move larger than a configured materiality threshold.

These are often more useful than level rules for detecting sudden changes in a familiar series.

### Percent Change Rules

Percent change rules inspect relative movement.

Examples:

- largest percentage increase in 1 year,
- top 1% percentage move,
- weekly percentage change exceeds a threshold.

These rules need guardrails because values near zero can produce meaningless or extreme percentages. A rule should define a minimum denominator or skip percent-change evaluation when the prior value is too small.

### Acceleration Rules

Acceleration rules inspect the change of the change, similar to a second difference.

Examples:

- the latest increase is much larger than the prior increase,
- the slope changes sharply,
- a series moves from steady decline to rapid increase.

These can be useful, but they are easier to overfit. They should remain candidate rules until backtesting shows that they are not too noisy.

### Structure And Drift Rules

Some important observations are not numerical outliers.

Examples:

- a Treasury category appears for the first time,
- a category disappears after being present regularly,
- an expected daily update is missing,
- a source schema changes,
- a category name changes and causes an apparent series break.

These rules are especially relevant for Treasury Fiscal Data, where category names and schemas can change over time.

## Noise Controls

The Signal Engine should prefer missing a marginal event over generating a noisy daily stream.

Potential controls:

- cooldown windows after a rule fires,
- materiality thresholds before reporting a new high or low,
- minimum age since the prior high or low,
- rolling-window variants instead of all-time variants,
- series classification before enabling rules,
- suppression of repeated alerts for slow structural trends,
- severity levels such as info, watch, and alert.

For example, an all-time high rule may only be useful when the previous all-time high was at least 180 days ago and the new value exceeds the old high by a meaningful amount.

## Series Classification

Rules should not be enabled blindly across every series.

Possible series classifications:

- stock: a balance or level measured at a point in time,
- flow: an amount over a period,
- trending: a series that commonly grows over time,
- bounded: a series with a known practical range,
- mean-reverting: a series that tends to return toward a normal zone,
- sparse: a series with many missing or zero values.

The classification does not need to be perfect in the first version. It exists to keep obviously inappropriate rules from firing on the wrong series.

## Backtesting

Every candidate rule should be backtested before publication.

Backtesting should answer:

- how often would this rule have fired historically,
- which dates would have appeared,
- whether those dates look genuinely notable,
- whether the rule is redundant with another rule,
- whether the rule needs a cooldown or materiality threshold.

A useful workflow is to generate a historical report for a candidate rule, review the firing dates, then decide whether to promote, tune, or reject the rule.

## External Observation Calibration

Real-world observations can be used to calibrate the rule catalog.

When a person on Twitter, in the news, or in another source notices something unusual, Macro Observatory should be able to record that example and ask whether the Signal Engine could have caught it.

A calibration note should capture:

```text
Observation:
  What did the outside source notice?

Source:
  Link, date, and author when available.

Dataset And Series:
  Which local dataset and field represent the event?

Candidate Rule:
  What rule would have fired?

Backtest Result:
  How often would this rule have fired historically?

Decision:
  Promote, tune, keep as candidate, or reject.
```

This keeps the rule catalog empirical. The goal is not to invent clever anomaly detection in isolation. The goal is to catch the kinds of events informed humans care about, without producing excessive noise.

## Published Artifact

A future implementation can publish a static artifact such as:

```text
site/data/signals.json
```

A signal event might look like:

```json
{
  "date": "2026-06-25",
  "severity": "watch",
  "dataset": "fed_net_liquidity",
  "series": "WALCL",
  "rule": "rolling_high_6m",
  "title": "Fed balance sheet reached a 6-month high",
  "detail": "Latest WALCL value is the highest observation since 2025-12-24.",
  "url": "pages/fed-net-liquidity/"
}
```

The exact schema can change when implementation begins. The important requirement is that each event be explainable, linkable, and tied back to a rule.

## First Implementation Shape

A conservative first implementation could include:

1. A small Python signal module that loads selected derived datasets.
2. A few candidate rules for Fed Net Liquidity components.
3. A command to backtest those rules locally.
4. A build step that writes `site/data/signals.json`.
5. A front-page Notable Observations section that reads that artifact.
6. A default state that clearly says when no notable observations were found.

Initial candidate rules could include:

- all-time high or low with cooldown and materiality controls,
- largest absolute move in 6 months,
- top 1% historical absolute move,
- missing expected update for daily or weekly source data.

## Non-Goals For The First Version

- Email, SMS, or push notifications.
- Paid alert delivery.
- Social posting automation.
- Machine-learning anomaly detection.
- A large rule catalog.
- Real-time intraday monitoring.
- Replacing the individual exploratory pages.

## Open Questions

- What should the first enabled rules inspect: Fed Net Liquidity, TGA Explorer categories, Treasury securities net issuance, or the Fed balance sheet?
- Should signal output be one combined artifact or split by page/dataset?
- How should candidate-rule backtest reports be stored?
- What severity levels should be user-facing?
- How should a user dismiss or hide a noisy signal on a static site?
- Should the public site show only current-day signals, or a short recent history?

## Next Step

Do not implement the Signal Engine yet. The next practical step is to continue building exploratory pages and collect examples of real-world observations that we would want Macro Observatory to catch later.
