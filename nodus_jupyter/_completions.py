"""Completion and inspect data for the Nodus kernel."""

KEYWORDS = [
    "let", "fn", "if", "else", "return", "workflow", "step", "after",
    "goal", "spawn", "coroutine", "channel", "import", "true", "false",
    "nil", "checkpoint", "async", "not", "and", "or",
]

BUILTINS = {
    "print": "print(value) — write a value to stdout",
    "len": "len(value) — length of a list, map, or string",
    "type": "type(value) — returns the type name as a string",
    "range": "range(n) / range(start, stop) — list of integers",
    "push": "push(list, value) — append value to list, returns new list",
    "pop": "pop(list) — remove and return last element",
    "keys": "keys(map) — list of map keys",
    "values": "values(map) — list of map values",
    "channel": "channel() — create a new unbuffered channel",
    "send": "send(ch, value) — send value into channel",
    "recv": "recv(ch) — receive value from channel",
    "close": "close(ch) — close a channel",
    "int": "int(value) — convert to integer",
    "float": "float(value) — convert to float",
    "str": "str(value) — convert to string",
    "bool": "bool(value) — convert to boolean",
    "error": "error(message) — create an error value",
    "is_error": "is_error(value) — true if value is an error",
    "spawn": "spawn(coroutine) — schedule coroutine for concurrent execution",
    "sleep": "sleep(ms) — suspend current coroutine for N milliseconds",
    "now": "now() — current Unix timestamp in milliseconds",
}

STDLIB_MODULES = [
    "std:math", "std:string", "std:json", "std:time", "std:http",
    "std:hash", "std:path", "std:fs", "std:subprocess", "std:tool",
    "std:encoding", "std:channel", "std:identity", "std:effects",
]

STDLIB_DOCS = {
    "std:math": "Math functions: abs, sqrt, floor, ceil, round, min, max, pow, log",
    "std:string": "String functions: split, join, trim, upper, lower, starts_with, ends_with, replace, contains",
    "std:json": "JSON encode/decode: json.encode(value), json.decode(str)",
    "std:time": "Time utilities: time.now(), time.sleep(ms), time.format(ts, fmt)",
    "std:http": "HTTP client: http.get(url), http.post(url, body), http.put(url, body)",
    "std:hash": "Hashing: hash.sha256(data).to_hex(), hash.md5(data).to_hex()",
    "std:path": "Path utilities: path.join(a, b), path.basename(p), path.dirname(p), path.exists(p)",
    "std:fs": "File I/O: fs.read(path), fs.write(path, content), fs.list(dir)",
    "std:subprocess": "Run processes: subprocess.run(cmd, args)",
    "std:encoding": "Encoding: encoding.base64_encode(s), encoding.base64_decode(s)",
}


def completions_for(prefix: str, current_globals: dict) -> list[str]:
    """Return completion candidates matching prefix."""
    candidates = list(KEYWORDS) + list(BUILTINS) + STDLIB_MODULES
    candidates += [k for k in current_globals if not k.startswith("__")]
    return sorted({c for c in candidates if c.startswith(prefix)})


def inspect_token(token: str) -> str | None:
    """Return a plain-text doc string for token, or None if unknown."""
    if token in BUILTINS:
        return BUILTINS[token]
    if token in STDLIB_DOCS:
        return STDLIB_DOCS[token]
    return None
