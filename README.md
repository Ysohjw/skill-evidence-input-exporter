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
