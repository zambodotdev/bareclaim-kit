#!/usr/bin/env python3
"""bareclaim: audit an agent's report against the job's receipts.

A bareclaim is a claim in an agent's report with no receipt under it.
Receipts prove what happened and that the record was not changed.
Zamback checks the record against rules written before the run.
Bareclaim checks the story told after the run against the record.

Every checkable claim in the report comes back as one of:

  BACKED       a receipt in the record backs the claim (named)
  BARE         nothing in the record backs the claim (a bareclaim)
  CONTRADICTED a receipt for the same step exists, but its saved
               values contradict the claim (the real values named)

A claim is checkable when it carries a number, names a tool that
appears in the record, or counts receipts/calls/steps. Everything
else is narrative and is skipped, never graded.

Usage:
  python3 bareclaim.py                      run the built-in demo
  python3 bareclaim.py report.txt record.json
  python3 bareclaim.py --json report.txt record.json
  python3 bareclaim.py --init               scaffold example files

The record is a JSON job record: a Zambo/AER-1 shaped object
{"receipts": [{"id", "tool", "input", "output"}, ...]}, or a plain
framework export {"steps": [...]}, or a bare list of steps, or
JSONL, one receipt per line. Aliases accepted: name for tool,
result/response for output, receipt_id for id. "-" reads stdin.

Exit code 0 when every checkable claim is backed, 1 when any claim
is bare or contradicted, 2 on usage errors. Stdlib only.

MIT License. From Brennan Zambo, creator of Zambo and AER-1, the
agent execution receipt standard. https://zambo.dev
"""

import json
import re
import sys

# ---------------------------------------------------------------- numbers

NUM_RE = re.compile(r"\$?\d[\d,]*\.?\d*%?")

def norm_num(tok):
    """Normalize a numeric token so $64,291.72, 64291.72 and 64,291.72
    compare equal. Returns None for tokens that are not numbers."""
    t = tok.replace("$", "").replace(",", "").replace("%", "").strip()
    if not t or t in (".",):
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    if v == int(v) and "." not in t:
        return str(int(v))
    return ("%.10f" % v).rstrip("0").rstrip(".")

UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)

def numbers_in(text):
    # Receipt ids are labels, not values: never let a UUID's digit runs
    # pose as numbers in a claim or a record.
    text = UUID_RE.sub(" ", text or "")
    out = []
    for m in NUM_RE.finditer(text):
        n = norm_num(m.group(0))
        if n is not None:
            out.append(n)
    return out

# ---------------------------------------------------------------- records

def _coerce_receipt(obj, idx):
    if not isinstance(obj, dict):
        return None
    tool = obj.get("tool") or obj.get("name") or obj.get("action") or ""
    rid = obj.get("id") or obj.get("receipt_id") or obj.get("receipt") or ""
    inp = obj.get("input") or obj.get("args") or obj.get("arguments") or ""
    out = obj.get("output")
    if out is None:
        out = obj.get("result")
    if out is None:
        out = obj.get("response")
    if out is None:
        out = ""
    blob = json.dumps(inp, sort_keys=True, default=str) + " " + json.dumps(out, sort_keys=True, default=str)
    return {
        "id": str(rid) if rid else "step-%d" % (idx + 1),
        "tool": str(tool),
        "blob": blob,
        "values": set(numbers_in(blob)),
    }

def load_record(text):
    text = text.strip()
    receipts = []
    data = None
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    if data is None:
        # JSONL: one receipt object per line
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            r = _coerce_receipt(obj, len(receipts))
            if r:
                receipts.append(r)
        return receipts
    if isinstance(data, dict):
        rows = data.get("receipts") or data.get("steps") or data.get("calls") or []
    elif isinstance(data, list):
        rows = data
    else:
        rows = []
    for i, obj in enumerate(rows):
        r = _coerce_receipt(obj, i)
        if r:
            receipts.append(r)
    return receipts

class Record:
    def __init__(self, receipts):
        self.receipts = receipts
        self.values = {}          # normalized number -> first receipt id holding it
        self.by_tool = {}         # tool -> [receipts]
        for r in receipts:
            for v in r["values"]:
                self.values.setdefault(v, r["id"])
            if r["tool"]:
                self.by_tool.setdefault(r["tool"], []).append(r)
        self.tools = set(self.by_tool)

    def tool_match(self, claim_text):
        """Tools from the record named in the claim, by full name or by
        the name with underscores read as spaces."""
        low = claim_text.lower()
        hits = []
        for tool in self.tools:
            name = tool.lower()
            if name in low or name.replace("_", " ") in low:
                hits.append(tool)
        return hits

# ---------------------------------------------------------------- claims

COUNT_RE = re.compile(r"(\d[\d,]*)\s+(receipts?|calls?|steps?|checks?|tool calls?)\b", re.I)

def split_claims(report_text):
    claims = []
    for line in report_text.splitlines():
        line = line.strip().lstrip("-*").strip()
        if not line:
            continue
        # split a line into sentences, keep short lines whole
        parts = re.split(r"(?<=[.!?])\s+", line)
        for p in parts:
            p = p.strip()
            if p:
                claims.append(p)
    return claims

def load_report(text):
    text = text.strip()
    if text.startswith("{") or text.startswith("["):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                rows = data.get("claims") or []
            else:
                rows = data
            out = []
            for row in rows:
                if isinstance(row, dict):
                    out.append(str(row.get("claim") or row.get("text") or ""))
                else:
                    out.append(str(row))
            return [c for c in out if c]
        except ValueError:
            pass
    return split_claims(text)

# Action families: words a report uses for an action, and the tool-name
# fragments that would leave a receipt for that action. A claim that
# names an action with no matching receipt anywhere is bare even when
# it carries no number ("emailed the client the summary").
ACTION_FAMILIES = [
    (("emailed", "email", "emails"), ("email", "mail", "gmail")),
    (("deployed", "deploy", "deployment"), ("deploy",)),
    (("published", "publish"), ("publish",)),
    (("charged", "charge"), ("charge", "payment", "stripe")),
    (("invoiced", "invoice"), ("invoice", "billing")),
    (("booked", "booking"), ("book", "reservation")),
    (("deleted", "delete"), ("delete", "remove")),
]

def action_match(claim, record):
    """Returns (word, [receipts]) for the first action family named in
    the claim, or None. Receipts is empty when the record holds no
    receipt for that action at all."""
    low = " " + re.sub(r"[^a-z0-9_ ]", " ", claim.lower()) + " "
    for words, needles in ACTION_FAMILIES:
        for w in words:
            if " %s " % w in low or " %ss " % w in low:
                recs = []
                for tool, trecs in record.by_tool.items():
                    if any(n in tool.lower() for n in needles):
                        recs.extend(trecs)
                return (w, recs)
    return None

def audit_claim(claim, record):
    """Returns (verdict, detail) for one claim, or None if the claim
    is narrative (not checkable)."""
    nums = numbers_in(claim)
    tools = record.tool_match(claim)
    counts = COUNT_RE.findall(claim)
    action = None
    if not tools:
        action = action_match(claim, record)
    if not nums and not tools and not counts and not action:
        return None
    if action and not action[1]:
        return ("BARE", "the report claims an '%s' action, but the record holds no receipt for it" % action[0])
    if action and action[1] and not tools:
        tools = [action[1][0]["tool"]]

    # Count claims about the record itself: "ran 6 checks", "6 receipts".
    for raw_n, noun in counts:
        n = norm_num(raw_n)
        if n is not None and noun.lower().startswith(("receipt", "call", "step", "check", "tool")):
            actual = len(record.receipts)
            if int(float(n)) != actual:
                return ("CONTRADICTED",
                        "the record holds %d receipts, not %s" % (actual, n))
            return ("BACKED", "the record holds %d receipts" % actual)

    if tools:
        tool = tools[0]
        trecs = record.by_tool.get(tool, [])
        if not trecs:
            return ("BARE", "no receipt for tool '%s' in the record" % tool)
        tool_values = set()
        for r in trecs:
            tool_values |= r["values"]
        missing = [n for n in nums if n not in tool_values]
        if missing:
            seen = sorted(tool_values, key=lambda x: float(x), reverse=True)[:6]
            return ("CONTRADICTED",
                    "receipt %s (%s) holds %s, not %s" % (
                        trecs[0]["id"], tool,
                        ", ".join(seen) if seen else "no numbers",
                        ", ".join(missing)))
        ids = [r["id"] for r in trecs]
        cite = ", ".join(ids[:3]) + (" +%d more" % (len(ids) - 3) if len(ids) > 3 else "")
        return ("BACKED", "receipt %s (%s)" % (cite, tool))

    # Numbers but no named tool: every number must live somewhere in the record.
    missing = [n for n in nums if n not in record.values]
    if missing:
        return ("BARE", "the number %s appears nowhere in the record" % ", ".join(missing))
    cite = record.values[nums[0]] if nums else ""
    return ("BACKED", "receipt %s" % cite)

def audit(report_text, record_text):
    record = Record(load_record(record_text))
    claims = load_report(report_text)
    results = []
    narrative = 0
    for i, claim in enumerate(claims, 1):
        got = audit_claim(claim, record)
        if got is None:
            narrative += 1
            continue
        verdict, detail = got
        results.append({"n": i, "claim": claim, "verdict": verdict, "detail": detail})
    return results, narrative, len(record.receipts)

# ---------------------------------------------------------------- output

def render(results, narrative, n_receipts, as_json):
    bare = [r for r in results if r["verdict"] == "BARE"]
    contra = [r for r in results if r["verdict"] == "CONTRADICTED"]
    backed = [r for r in results if r["verdict"] == "BACKED"]
    if as_json:
        print(json.dumps({
            "receipts_in_record": n_receipts,
            "checkable_claims": len(results),
            "narrative_lines_skipped": narrative,
            "backed": len(backed),
            "bareclaims": len(bare),
            "contradicted": len(contra),
            "results": results,
            "verdict": "CLEAN" if not bare and not contra else "BARE",
        }, indent=2))
    else:
        for r in results:
            print("%-12s claim %d: %s" % (r["verdict"], r["n"], r["claim"]))
            print("%-12s   -> %s" % ("", r["detail"]))
        if bare or contra:
            print("RESULT: BARE. %d bareclaim%s, %d contradicted, of %d checkable claims against %d receipts." % (
                len(bare), "" if len(bare) == 1 else "s", len(contra), len(results), n_receipts))
        else:
            print("RESULT: CLEAN. Every checkable claim is backed, %d of %d, against %d receipts." % (
                len(backed), len(results), n_receipts))
    return 0 if not bare and not contra else 1

# ---------------------------------------------------------------- demo

DEMO_RECORD = {
    "receipts": [
        {"id": "76e0f74f-76dc-4e42-8bdc-13d16b3bf8ac", "tool": "live_price",
         "input": {"symbol": "BTC"}, "output": {"symbol": "BTC", "price": 64291.72}},
        {"id": "277c864a-30aa-40f5-9084-a4c47837e415", "tool": "memory_remember",
         "input": {"note": "launch checklist"}, "output": {"stored": True, "notes_total": 1}},
    ]
}

DEMO_GOOD = """The live_price check put BTC at $64,291.72 before the call.
Stored the launch checklist with memory_remember, which left 1 note on file.
The job left 2 receipts, one per step."""

DEMO_BARE = """The live_price check put BTC at $71,050.00 before the call.
Stored the launch checklist with memory_remember, which left 1 note on file.
Emailed the client the full summary and the invoice.
The job left 2 receipts, one per step."""

def run_demo():
    rec = json.dumps(DEMO_RECORD)
    print("== bareclaim demo: an honest report ==")
    results, narrative, n = audit(DEMO_GOOD, rec)
    code = render(results, narrative, n, False)
    print()
    print("== bareclaim demo: the same job, an inflated report ==")
    results, narrative, n = audit(DEMO_BARE, rec)
    code2 = render(results, narrative, n, False)
    print()
    print("Demo done: the honest report is CLEAN, the inflated one is BARE.")
    return 0 if code == 0 and code2 == 1 else 1

INIT_REPORT = """The live_price check put BTC at $0.00 before the call.
Stored the launch checklist with memory_remember, which left 1 note on file.
The job left 2 receipts, one per step.
"""

INIT_RECORD = {
    "receipts": [
        {"id": "receipt-id-from-your-record", "tool": "live_price",
         "input": {"symbol": "BTC"}, "output": {"symbol": "BTC", "price": 0.00}},
        {"id": "receipt-id-from-your-record", "tool": "memory_remember",
         "input": {"note": "launch checklist"}, "output": {"stored": True, "notes_total": 1}},
    ]
}

def run_init():
    with open("report.example.txt", "w") as fh:
        fh.write(INIT_REPORT)
    with open("record.example.json", "w") as fh:
        json.dump(INIT_RECORD, fh, indent=2)
    print("Wrote report.example.txt and record.example.json.")
    print("Replace the values with your agent's report and your job record, then run:")
    print("  python3 bareclaim.py report.example.txt record.example.json")
    return 0

# ---------------------------------------------------------------- main

def read_arg(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()

def main(argv):
    args = [a for a in argv[1:] if a != "--json"]
    as_json = "--json" in argv
    if "--init" in argv:
        return run_init()
    if len(args) == 0:
        return run_demo()
    if len(args) != 2:
        print("usage: bareclaim.py [--json] report.txt record.json | --init", file=sys.stderr)
        return 2
    report_text = read_arg(args[0])
    record_text = read_arg(args[1])
    results, narrative, n = audit(report_text, record_text)
    return render(results, narrative, n, as_json)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
