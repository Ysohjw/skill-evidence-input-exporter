"""Create a NEW local transport JSON from a declared native review request."""
import argparse
from pathlib import Path
import sys

from input_validation import (ARTIFACT_FOLDERS, CONTROL_FILES, MAX_BYTES, MAX_DIRECTORIES, MAX_FILES,
                              TEXT_EXTENSIONS, InputError, bytes_for_text, json_bytes, safe_relative, validate_payload,
                              linked, load_request, safe_path)


def collect(request_path, include_text_artifacts=False):
    request = load_request(request_path.absolute())
    root = request["iteration"].absolute()
    if not root.is_dir() or linked(root):
        raise InputError("Iteration must be an ordinary directory")
    safe_path(request["evals"].absolute(), request["evals"].absolute().parent)
    if request["evals"].stat().st_size > 2 * 1024 * 1024:
        raise InputError("Original plan exceeds 2 MiB")
    plan_bytes = request["evals"].read_bytes()
    plan = plan_bytes.decode("utf-8")
    collected_bytes = len(plan_bytes)
    directories, files, omitted = [], [], 0
    stack = [root]
    visited = 0
    while stack:
        folder = stack.pop()
        entries = []
        for path in folder.iterdir():
            visited += 1
            if visited > 10000:
                raise InputError("Collection exceeds 10000 inspected entries; use the native local entry")
            entries.append(path)
        for path in sorted(entries, key=lambda p: p.name):
            safe_path(path, root)
            relative = safe_relative(path.relative_to(root).as_posix())
            collected_bytes += len(relative.encode("utf-8"))
            if collected_bytes > MAX_BYTES:
                raise InputError("Evidence exceeds 8 MiB; use the native local entry")
            artifact = any(x in ARTIFACT_FOLDERS for x in path.relative_to(root).parts[:-1])
            if path.is_dir():
                directories.append(relative)
                stack.append(path)
                if len(directories) > MAX_DIRECTORIES:
                    raise InputError("Too many directories for transport")
                continue
            if not path.is_file():
                raise InputError("Unsupported special file")
            kind = None
            if not artifact and path.name in CONTROL_FILES:
                kind = "record"
            elif artifact and include_text_artifacts and path.suffix.lower() in TEXT_EXTENSIONS:
                kind = "artifact_text"
            elif not artifact and (path.name in ("runs", request["candidate"], request["baseline"]) or path.name.startswith("run-")):
                kind = "layout_marker"
            if kind is None:
                omitted += 1
                continue
            if kind == "layout_marker":
                content = ""
            else:
                if path.stat().st_size > 2 * 1024 * 1024:
                    raise InputError("One selected file exceeds 2 MiB")
                data = path.read_bytes()
                collected_bytes += len(data)
                if collected_bytes > MAX_BYTES:
                    raise InputError("Evidence exceeds 8 MiB; use the native local entry")
                content = data.decode("utf-8")
                bytes_for_text(content)
            files.append({"path": relative, "kind": kind, "text": content})
            if len(files) > MAX_FILES:
                raise InputError("Too many selected files for transport")
    payload = {"dataHandlingAcknowledged": True, "evidence": {
        "format": "skill-evidence-files-v1", "planText": plan,
        "candidate": request["candidate"], "baseline": request["baseline"], "runs": request["runs"],
        "reviewContext": request["review_context"],
        "directories": sorted(directories), "files": sorted(files, key=lambda x: x["path"]),
        "artifactPolicy": "explicit_text_only" if include_text_artifacts else "omitted"}}
    validate_payload(payload)
    return payload, {"selected_files": len(files), "directories": len(directories), "omitted_files": omitted,
                     "warning": "Directory names and all text inside selected records remain. No automatic secret or personal-data redaction."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--include-text-artifacts", action="store_true")
    parser.add_argument("--acknowledge-data", action="store_true", help="Confirm review of selected evidence; never authorizes upload")
    args = parser.parse_args()
    try:
        if not args.acknowledge_data:
            raise InputError("Explicit data acknowledgement is required")
        request = load_request(args.request.absolute())
        target = args.out.absolute()
        if target.resolve().is_relative_to(request["iteration"].resolve()) or target.resolve() in (args.request.resolve(), request["evals"].resolve()):
            raise InputError("Export must be outside the input iteration and must not replace request or plan")
        payload, summary = collect(args.request, args.include_text_artifacts)
        with target.open("xb") as handle:
            handle.write(json_bytes(payload))
        print(json_bytes({"status": "LOCAL_EXPORT_CREATED_NOT_UPLOADED", **summary}).decode("utf-8"), end="")
        return 0
    except (InputError, OSError, ValueError, UnicodeError):
        print("INPUT_ERROR: export not completed. Check the request, ordinary UTF-8 files, documented limits, new output path and --acknowledge-data.", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
