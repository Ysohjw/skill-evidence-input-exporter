# Skill Evidence Input Exporter

Version 1.0.0. Free input-only preparation tool. The four input-only files are licensed under MIT; see LICENSE. The hosted checker, report engine and billing implementations are not part of this distribution.

Python 3.10+; standard library only. No package installation or account is required. This package only collects and validates input. It does not evaluate Skills, run models, create review reports, upload files or charge users.

Bring the original evals.json plan, completed iteration directory, explicit candidate/baseline names and originally planned repeats. Save a review-request.json outside the iteration, for example:

```json
{"iteration":"iteration","evals":"evals.json","candidate":"new_skill","baseline":"old_skill","runs":2}
```

From the extracted package directory:

```text
python -B src/prepare_input.py --request /path/to/review-request.json --out /path/to/new-input.json --acknowledge-data
```

The output must be a new path outside the iteration and cannot replace the request or plan. Two repeats above are an example; preserve your actual original plan. Add --include-text-artifacts only after reviewing the selected text output/artifact files. Without it, artifact content is omitted.

Inspect the new JSON locally before any separately authorized upload. It includes directory names and selected record text, including prompts and grades; there is no automatic secret or personal-data redaction. Symlink/reparse inputs, ambiguous transport paths, excessive size/count and invalid requests are refused. No private evidence or hosted runtime files are bundled here.

Support: hjwysoserious@gmail.com. Send only a sanitized issue description. Do not send credentials or private evaluation files. No fixed response-time guarantee is offered.

## Review your prepared evidence

This free MIT exporter prepares input only. For a hosted evidence review, see [Skill Upgrade Evidence Check on Apify](https://apify.com/ysoserious_h/benchmark-evidence-preflight). It needs your original evaluation plan, completed grading folders, explicit candidate/baseline roles and originally planned repeats. It does not run Skills, regrade outputs or make an automatic upgrade decision.

Each user's first five delivered reports for this product are free once across all runs; after that, US$0.10 is charged per delivered report, including blocked comparisons. The allowance belongs to the Apify account that starts the run; it does not require a newly registered account and does not reset per run or month. Separate platform charges may apply. Review the platform's displayed charges before starting.

Inspect the exported JSON locally before any cloud submission. There is no automatic redaction; selected evidence and report files are stored on Apify when you submit them. Do not upload credentials, private customer records or material you lack permission to share. No paid companion package is required.

Synthetic illustration: one completed comparison had 4/4 planned evidence slots and equal 75% averages, yet contained one improved assertion and one regressed assertion. Inspect the underlying grades and actual task outputs before making a release decision. This is an illustration, not a customer result or a promised benefit.

If you try the workflow, optional feedback about setup difficulty or a finding that changed your review decision is welcome at the support address above. Send only a sanitized description; no private evaluation files or testimonial are requested. No fixed response-time guarantee is offered.
