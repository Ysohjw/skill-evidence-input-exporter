"""Input-only collection/transport validation, extracted unchanged from core0.3.1/transport1.
No evaluation, reporting, hosted runtime, billing, trial ledger or network interface.
"""
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re

MAX_JSON = 2 * 1024 * 1024


NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


class InputError(ValueError):
    pass


def linked(path):
    try:
        return path.is_symlink() or bool(getattr(path.lstat(), "st_file_attributes", 0) & 0x400)
    except OSError:
        return False


def safe_path(path, boundary):
    path = path.absolute()
    if not path.is_relative_to(boundary):
        raise InputError("Path outside input boundary")
    current = path
    while True:
        if linked(current):
            raise InputError("Symlink/reparse point input is unsupported")
        if current == boundary:
            break
        current = current.parent
    return path


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def finite_float(token):
    value = float(token)
    if not math.isfinite(value):
        raise InputError("Non-finite JSON number")
    return value


def read_json(path, boundary):
    path = safe_path(path, boundary)
    if not path.is_file() or path.stat().st_size > MAX_JSON:
        raise InputError("Missing, non-file, or oversized JSON")
    data = path.read_bytes()
    try:
        obj = json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_pairs, parse_float=finite_float,
                         parse_constant=lambda x: (_ for _ in ()).throw(InputError("Non-finite JSON number")))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise InputError("Invalid UTF-8 JSON: " + str(exc)) from exc
    if not isinstance(obj, dict):
        raise InputError("Expected JSON object")
    return obj, hashlib.sha256(data).hexdigest()


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def load_request(path):
    """Reuse declared intent, never reconstruct it from surviving grading files."""
    obj, digest = read_json(path, path.absolute().parent)
    required = {"iteration", "evals", "candidate", "baseline", "runs"}
    if not required.issubset(obj) or set(obj) - required - {"review_context"}:
        raise InputError("Review request needs iteration, evals, candidate, baseline and runs; only review_context is optional")
    for key in ("iteration", "evals", "candidate", "baseline"):
        if not isinstance(obj[key], str) or not obj[key].strip():
            raise InputError("Review request " + key + " must be a nonempty string")
    if not integer(obj["runs"], 1) or obj["runs"] > 20:
        raise InputError("Review request runs must be an explicit integer from 1 to 20")
    context = obj.get("review_context", "")
    if not isinstance(context, str) or len(context) > 4000:
        raise InputError("Optional review_context must be text of at most 4000 characters")
    parent = path.absolute().parent
    return {**obj, "iteration": parent / obj["iteration"], "evals": parent / obj["evals"],
            "request_sha256": digest, "review_context": context}


MAX_BYTES = 8 * 1024 * 1024


MAX_FILE_BYTES = 2 * 1024 * 1024


MAX_FILES = 1000


MAX_DIRECTORIES = 3000


CONTROL_FILES = {"grading.json", "eval_metadata.json", "run_metadata.json", "timing.json"}


ARTIFACT_FOLDERS = {"outputs", "artifacts"}


TEXT_EXTENSIONS = {".json", ".txt", ".md", ".csv"}


RESERVED = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?\Z", re.I)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def safe_relative(value):
    if (not isinstance(value, str) or not value or len(value) > 500
            or any(ord(c) < 32 or ord(c) == 127 or c in '\\:<>"|?*' for c in value)):
        raise InputError("Unsupported relative evidence path")
    parts = value.split("/")
    if any(not x or x in (".", "..") or x.endswith((" ", ".")) or RESERVED.fullmatch(x) for x in parts):
        raise InputError("Evidence paths must be portable relative paths without traversal")
    return value


def bytes_for_text(value):
    if not isinstance(value, str):
        raise InputError("Evidence content must be UTF-8 text")
    try:
        data = value.encode("utf-8")
    except UnicodeError as exc:
        raise InputError("Evidence contains unsupported Unicode") from exc
    if len(data) > MAX_FILE_BYTES:
        raise InputError("One evidence file exceeds 2 MiB")
    return data


def validate_payload(payload):
    if not isinstance(payload, dict) or set(payload) != {"dataHandlingAcknowledged", "evidence"}:
        raise InputError("Provide only dataHandlingAcknowledged and evidence")
    if payload["dataHandlingAcknowledged"] is not True:
        raise InputError("Review the exported data, then explicitly acknowledge data handling")
    evidence = payload["evidence"]
    required = {"format", "planText", "candidate", "baseline", "runs", "directories", "files", "artifactPolicy"}
    if not isinstance(evidence, dict) or not required.issubset(evidence) or set(evidence) - required - {"reviewContext"}:
        raise InputError("Evidence needs the original plan, explicit roles/repeats, directory/file lists and artifact policy")
    if evidence["format"] != "skill-evidence-files-v1":
        raise InputError("Unsupported evidence format")
    roles = [evidence["candidate"], evidence["baseline"]]
    if not all(isinstance(x, str) and NAME.fullmatch(x) for x in roles) or roles[0] == roles[1]:
        raise InputError("Provide distinct explicit candidate and baseline directory names")
    if type(evidence["runs"]) is not int or not 1 <= evidence["runs"] <= 20:
        raise InputError("Provide original planned repeats from 1 to 20")
    context = evidence.get("reviewContext", "")
    if not isinstance(context, str) or len(context) > 4000:
        raise InputError("Review context must be text of at most 4000 characters")
    if evidence["artifactPolicy"] not in ("omitted", "explicit_text_only"):
        raise InputError("Unsupported artifact policy")
    directories, files = evidence["directories"], evidence["files"]
    if not isinstance(directories, list) or len(directories) > MAX_DIRECTORIES:
        raise InputError("Directory list exceeds 3000 entries or is invalid")
    if not isinstance(files, list) or len(files) > MAX_FILES:
        raise InputError("File list exceeds 1000 entries or is invalid")
    plan = bytes_for_text(evidence["planText"])
    total_bytes = len(plan)
    seen, file_names, materialized = {}, set(), []

    def register(path, kind):
        path = safe_relative(path)
        key = path.casefold()
        if key in seen:
            raise InputError("Duplicate or case-colliding evidence paths")
        seen[key] = (path, kind)
        return path

    for path in directories:
        register(path, "directory")
        total_bytes += len(path.encode("utf-8"))
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "kind", "text"}:
            raise InputError("Each file needs path, kind and text")
        path = register(item["path"], "file")
        parts = PurePosixPath(path).parts
        artifact = any(x in ARTIFACT_FOLDERS for x in parts[:-1])
        kind = item["kind"]
        if kind == "record":
            if artifact or parts[-1] not in CONTROL_FILES:
                raise InputError("Only recognized evidence record names may use record kind")
        elif kind == "artifact_text":
            if not artifact or evidence["artifactPolicy"] != "explicit_text_only" or PurePosixPath(path).suffix.lower() not in TEXT_EXTENSIONS:
                raise InputError("Artifact contents require explicit text-only inclusion")
        elif kind == "layout_marker":
            if artifact or item["text"] != "" or not (parts[-1] in ("runs", *roles) or parts[-1].startswith("run-")):
                raise InputError("Unsupported layout marker")
        else:
            raise InputError("Unsupported file kind")
        data = bytes_for_text(item["text"])
        total_bytes += len(data) + len(path.encode("utf-8"))
        if total_bytes > MAX_BYTES:
            raise InputError("Evidence text exceeds 8 MiB")
        materialized.append((path, data, kind))
        file_names.add(path.casefold())
    for path, _ in seen.values():
        parts = path.split("/")
        for n in range(1, len(parts)):
            parent = "/".join(parts[:n])
            key = parent.casefold()
            if key in file_names or key not in seen or seen[key][0] != parent:
                raise InputError("Declare every parent directory consistently; files cannot contain other paths")
    if len(json_bytes(payload)) > MAX_BYTES:
        raise InputError("Transport JSON exceeds 8 MiB")
    return evidence, plan, materialized
