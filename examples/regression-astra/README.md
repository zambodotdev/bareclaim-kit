# Regression cases: the launch-day outside test

These fixtures come from a test run against the shipped checker on
launch day (2026-11-17) by Astra Fieldnotes on The Colony. Both cases
originally returned BACKED / CLEAN, exit 0. Both were real defects,
and both are fixed. They stay here so the fixes cannot quietly
regress.

## Case 1: an explicit failure backing a success claim

```bash
python3 bareclaim.py report.failure.txt record.failure.json
# CONTRADICTED claim 1: Emailed the client the summary.
#                -> receipt synthetic-1 (send_email) shows sent: false; error: rejected before execution, not the success the claim states
# RESULT: BARE. 0 bareclaims, 1 contradicted, of 1 checkable claims against 1 receipts.
```

The record's only receipt for the claimed action states the action
did not happen (`sent: false`, plus an error). Presence of the tool
is not backing when the receipt itself says failure. Controls: the
same claim against `{"sent": true}` is BACKED / CLEAN, removing the
step entirely is BARE, and a claim that itself reports the failure
is BACKED by the failure receipt:

```bash
python3 bareclaim.py report.acknowledged.txt record.failure.json
# BACKED       claim 1: The send_email attempt was rejected before execution, so no email was sent.
#                -> receipt synthetic-1 (send_email)
# RESULT: CLEAN. Every checkable claim is backed, 1 of 1, against 1 receipts.
```

## Case 2: swapped numbers passing as a set match

```bash
python3 bareclaim.py report.swapped.txt record.swapped.json
# CONTRADICTED claim 1: The lookup check put apples at 20 and pears at 10.
#                -> receipt synthetic-2 (lookup) holds apples 10, not 20
# RESULT: BARE. 0 bareclaims, 1 contradicted, of 1 checkable claims against 1 receipts.
```

The claim's numbers both lived in the receipt, bound to the wrong
fields. A number a claim binds to a named field now has to equal
that field's recorded value. The correct version of the claim
(apples at 10, pears at 20) is BACKED / CLEAN.

## The boundary that remains

Beyond explicit failure markers and named-field values, BACKED is a
lexical and value match, not a judgment of a tool's private success
semantics. A record carrying no failure marker and no named field
for a claim gives the checker nothing deeper to check.
