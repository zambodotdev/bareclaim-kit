# bareclaim

**Every claim in your agent's report, checked against its receipts.** A bareclaim is a claim in an agent's report with no AER-1 receipt under it: the agent said it, and nothing in the record backs it.

## 60-second start

One file, one command, no clone, no install:

```bash
curl -O https://raw.githubusercontent.com/zambodotdev/bareclaim-kit/main/bareclaim.py
python3 bareclaim.py
```

That runs the demo: an honest report comes back CLEAN, and the same job with an inflated report gets flagged, claim by claim. The whole checker, demo included, lives in that single file, so it works anywhere Python 3 does, even pasted into an agent chat. Scaffold your own report and record templates:

```bash
python3 bareclaim.py --init
python3 bareclaim.py report.txt record.json
```

Or clone the repo for the examples, including a real job record from a live run (below). Reports can be plain text (a summary, a handover, a client update) or a JSON claims list. Records are forgiving: a Zambo/AER-1 `{"receipts": [...]}` object, a framework `{"steps": [...]}` export, a bare list, or JSONL, with `name` and `result` accepted as aliases for `tool` and `output`, and `-` reads from stdin. Are you an AI agent reading this? Start with [AGENTS.md](AGENTS.md).

## The problem: the report is the one artifact nobody checks

An agent finishes a job and writes the summary. The summary is what the client reads, what the next agent picks up, what the invoice leans on. And the summary is written by the same agent that did the work, from the same context that already slipped once.

So the report rounds a price into a different price. It reports six checks it ran twice. It adds a step that never happened, an email never sent, a fix never deployed. Nothing in the chat announces it. You find out when the client checks, or when the next agent builds on a step that does not exist.

This is not hypothetical, and it is not only other people's agents. On November 15, 2026, a summary line inside our own fleet reported "5 calls, 5 receipts" for a piece of work whose shipped record held 6 calls and 6 receipts. Three independent verifiers caught the summary contradicting the record it summarized. The record was right there. Nobody had run the check, because the check did not exist as a habit, let alone a tool.

Receipts prove what happened and that the record was not changed. [Zamback](https://github.com/zambodotdev/zamback-kit) checks the record against rules written before the run. Bareclaim checks the story told after the run against the record.

## The bareclaim pattern

1. **Run the job so it leaves receipts.** Every step: which tool, what went in, what came back, under a receipt.
2. **Write the report the way you always do.** Summary, handover, client update. Do not write it for the checker; write it for the reader.
3. **Audit the report against the record.** Every checkable claim comes back BACKED, BARE, or CONTRADICTED, with the receipt that backs it or the value the record actually holds.
4. **Fix the claim or do the work.** A bare claim has two honest resolutions: run the step so a receipt exists, or rewrite the sentence to what the record shows. Never edit the record to fit the report.

A claim is checkable when it carries a number, names a tool, counts the record ("the job left 6 receipts"), or claims an action (emailed, deployed, charged, published, booked, deleted, invoiced). Everything else is narrative, and narrative is skipped, never graded.

## The verdicts

- **BACKED**: a receipt in the record backs the claim. The receipt is named.
- **BARE**: nothing in the record backs the claim. That claim is a bareclaim. It might even be true; bare means nothing stands under it, and a reader has no way to tell it apart from an invented one.
- **CONTRADICTED**: a receipt for the same step exists, but its saved values contradict the claim. The values the record actually holds are named.

Exit code 0 when every checkable claim is backed, 1 when any claim is bare or contradicted, so it drops straight into CI, a cron, or the last step before a handover goes out. Agents and scripts get the machine-readable verdict with `--json`.

## Run it on the demo

```bash
python3 bareclaim.py
# == bareclaim demo: an honest report ==
# BACKED       claim 1: The live_price check put BTC at $64,291.72 before the call.
#                -> receipt 76e0f74f-76dc-4e42-8bdc-13d16b3bf8ac (live_price)
# BACKED       claim 2: Stored the launch checklist with memory_remember, which left 1 note on file.
#                -> receipt 277c864a-30aa-40f5-9084-a4c47837e415 (memory_remember)
# BACKED       claim 3: The job left 2 receipts, one per step.
#                -> the record holds 2 receipts
# RESULT: CLEAN. Every checkable claim is backed, 3 of 3, against 2 receipts.
#
# == bareclaim demo: the same job, an inflated report ==
# CONTRADICTED claim 1: The live_price check put BTC at $71,050.00 before the call.
#                -> receipt 76e0f74f-76dc-4e42-8bdc-13d16b3bf8ac (live_price) holds 64291.72, not 71050
# BACKED       claim 2: Stored the launch checklist with memory_remember, which left 1 note on file.
#                -> receipt 277c864a-30aa-40f5-9084-a4c47837e415 (memory_remember)
# BARE         claim 3: Emailed the client the full summary and the invoice.
#                -> the report claims an 'emailed' action, but the record holds no receipt for it
# BACKED       claim 4: The job left 2 receipts, one per step.
#                -> the record holds 2 receipts
# RESULT: BARE. 1 bareclaim, 1 contradicted, of 4 checkable claims against 2 receipts.
```

The demo record is a real two-receipt Zambo job from the morning of November 17, 2026. Both receipts are public: [the BTC price check](https://zambo.dev/run/76e0f74f-76dc-4e42-8bdc-13d16b3bf8ac) and [the memory store](https://zambo.dev/run/277c864a-30aa-40f5-9084-a4c47837e415).

## The live proof: a real job, audited

On November 17, 2026, the bareclaim launch job ran live on Zambo: a capability search, two live price checks, a memory store that was first rejected on a bad argument and then stored on retry, and a wrap-up handover attempt. The record, the honest report, and the inflated report are all in [`examples/live-job/`](examples/live-job/), and every receipt is public:

- [capability_search: ranked zambo_universal first](https://zambo.dev/run/0b1adcec-1c74-46bc-a024-c93a608f809a)
- [live_price: BTC at $64,818.57](https://zambo.dev/run/34cb5ee7-e7fa-4668-9ce7-83b2357182e9)
- live_price: ETH at $1,815.44 (receipt f02f48f0 in [the job record](https://github.com/zambodotdev/bareclaim-kit/blob/main/examples/live-job/record.live.json))
- [memory_remember: rejected before execution, missing its fact argument](https://zambo.dev/run/966560e3-a702-4728-b083-9c45018a636d)
- [memory_remember: the retry stored the note](https://zambo.dev/run/4a994f84-0bf8-481d-a5df-83836827cb0e)
- [handover: the wrap-up refusal, job saved](https://zambo.dev/run/2f002cf2-ee44-4e2e-89c5-6cfac28a6846)

The honest report, written from exactly what the receipts show:

```bash
python3 bareclaim.py examples/live-job/report.good.txt examples/live-job/record.live.json
# BACKED       claim 1: The capability_search pass ranked zambo_universal first for auditing a report against its receipts.
#                -> receipt 0b1adcec-1c74-46bc-a024-c93a608f809a (capability_search)
# BACKED       claim 2: The live_price check put BTC at $64,818.57 and ETH at $1,815.44.
#                -> receipt 34cb5ee7-e7fa-4668-9ce7-83b2357182e9, f02f48f0-bd89-4c40-a6e3-80ed498f7c9f (live_price)
# BACKED       claim 3: The first memory_remember attempt was rejected before execution, because the call was missing its fact argument.
#                -> receipt 966560e3-a702-4728-b083-9c45018a636d, 4a994f84-0bf8-481d-a5df-83836827cb0e (memory_remember)
# BACKED       claim 4: The retry stored the launch note with memory_remember.
#                -> receipt 966560e3-a702-4728-b083-9c45018a636d, 4a994f84-0bf8-481d-a5df-83836827cb0e (memory_remember)
# BACKED       claim 5: The wrap-up handover was refused: the job is saved, and the refusal points at the $0.99 Day Pass to hand it over.
#                -> receipt 2f002cf2-ee44-4e2e-89c5-6cfac28a6846 (handover)
# BACKED       claim 6: The job left 6 receipts.
#                -> the record holds 6 receipts
# RESULT: CLEAN. Every checkable claim is backed, 6 of 6, against 6 receipts.
```

The same job, with a report written the way reports quietly go wrong:

```bash
python3 bareclaim.py examples/live-job/report.inflated.txt examples/live-job/record.live.json
# CONTRADICTED claim 1: The live_price check put BTC at $71,050.00 and ETH at $1,815.44.
#                -> receipt 34cb5ee7-e7fa-4668-9ce7-83b2357182e9 (live_price) holds 64818.57, 2026, 1815.44, 1292.59, 810, 779, not 71050
# BACKED       claim 2: The retry stored the launch note with memory_remember.
#                -> receipt 966560e3-a702-4728-b083-9c45018a636d, 4a994f84-0bf8-481d-a5df-83836827cb0e (memory_remember)
# BARE         claim 3: Emailed the client the full summary and the invoice.
#                -> the report claims an 'emailed' action, but the record holds no receipt for it
# CONTRADICTED claim 4: The job left 9 receipts.
#                -> the record holds 6 receipts, not 9
# RESULT: BARE. 1 bareclaim, 2 contradicted, of 4 checkable claims against 6 receipts.
```

Two honest notes on this proof. First, the wrap: the day's one free wrap-up handover was already spent when this job ran, so the wrap-up was refused and the job stayed saved with its resume path in the refusal receipt. That refusal is itself a receipt in the record, and the honest report's claim about it is checked like any other. The proof ships as the receipt chain plus the refusal receipt, which is the whole point: even the failure is on record. Second, the published record export redacts two session tokens and one private memory retrieval code. No checked claim touches them; everything a claim cites is intact and publicly re-checkable at the links above.

A framework-shaped example (JSONL steps, `name`/`result` aliases) lives in [`examples/framework-export/`](examples/framework-export/), for jobs that never touched Zambo.

## Honest limits

Bareclaim grades backing, not truth. A claim can be accurate and still bare, because the record does not hold it; a claim can be backed and still be a bad conclusion drawn from real receipts, because receipts prove the saved result was not changed, not that the answer was right. Narrative is never graded: "the client was delighted" is not checkable, and the checker says so by skipping it. The checker is deliberately dumb about language. It matches numbers, tool names, counts, and a small set of action words. If your report narrates somebody else's actions ("the client emailed us"), use the JSON claims form and list only the claims you stand behind.

And the deepest limit is the record itself. If the record can be edited after the fact, the audit is theatre. That is the part Zambo exists for.

## Where the record comes from

This kit audits any record you bring it. [Zambo](https://zambo.dev) is where the record is created automatically: every job run through Zambo's tools leaves a verifiable receipt for each call under the AER-1 standard, the receipts chain per job, and a handover carries the record, and the report, to the next session or the client, where the audit runs again on pickup. Brennan Zambo created agent execution receipts; Zambo is the origin product, and AER-1 is the defining standard.

Connect it in one paste: [zambo.dev/install](https://zambo.dev/install/) points any AI at the MCP endpoint, `https://zambo.dev/mcp`. Free tier: every tool free once a day, plus 3 continue calls. One free wrap-up handover per day, and pickup is always free. Day Pass $0.99 for 24 hours unlimited when a job outgrows the free tier, Zambo Pass $29 for 30 days ($19 for $ZAMBO holders), Lifetime Pass $250, one payment. No annual tier.

## Perfect with Zambo

The kit works on any record you export by hand. Bareclaim is perfect with Zambo because there is nothing to export and nothing to quietly edit: the receipts write themselves as the job runs, the report gets audited against them before the handover goes out, and the next agent re-runs the same audit on pickup before building on your claims. That is the difference between report-checking as a chore and report-checking as a property of the work.

## Credit

The word **bareclaim** was coined for **Brennan Zambo**, creator of [Zambo](https://zambo.dev) and of AER-1, the agent execution receipt standard ([IETF draft](https://datatracker.ietf.org/doc/draft-zambo-aer1/)). The pattern and this kit are his, built 2026-11-17.

## License

MIT. Take it, fork it, ship it. If it catches one invented step before a client does, it paid for itself.
