"""Live integration test — drives the Nodus kernel via jupyter_client
without needing a browser or JupyterLab UI."""

import queue
import sys
import time

import jupyter_client


def run_cell(kc, code, timeout=15):
    """Execute code and return (stdout, stderr, error)."""
    msg_id = kc.execute(code)
    stdout_parts = []
    stderr_parts = []
    error = None

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            msg = kc.get_iopub_msg(timeout=1.0)
        except queue.Empty:
            continue
        mt = msg["msg_type"]
        content = msg["content"]
        if mt == "stream":
            if content["name"] == "stdout":
                stdout_parts.append(content["text"])
            else:
                stderr_parts.append(content["text"])
        elif mt == "error":
            error = content.get("evalue", "unknown error")
        elif mt == "status" and content.get("execution_state") == "idle":
            break

    stderr = "".join(stderr_parts)
    # Kernel sends errors as stderr stream messages; treat non-empty stderr as error.
    if error is None and stderr:
        error = stderr
    return "".join(stdout_parts), stderr, error


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f": {detail}" if detail else ""))
    return condition


def main():
    print("Starting Nodus kernel via jupyter_client...")
    km = jupyter_client.KernelManager(kernel_name="nodus")
    km.start_kernel()
    kc = km.client()
    kc.start_channels()

    # Wait for kernel to be ready
    try:
        kc.wait_for_ready(timeout=15)
    except RuntimeError as e:
        print(f"Kernel failed to start: {e}")
        km.shutdown_kernel()
        sys.exit(1)

    print("Kernel ready. Running tests...\n")
    all_pass = True

    # --- Test 1: Simple expression ---
    print("Test 1: Simple expression")
    stdout, _, error = run_cell(kc, "let x = 6 * 7\nprint(x)\n")
    all_pass &= check("no error", error is None, error)
    all_pass &= check("output is 42", "42" in stdout, repr(stdout))

    # --- Test 2: Variable persists to next cell ---
    print("\nTest 2: Variable persistence across cells")
    run_cell(kc, "let greeting = \"hello\"\n")
    stdout, _, error = run_cell(kc, "print(greeting)\n")
    all_pass &= check("no error", error is None, error)
    all_pass &= check("greeting visible", "hello" in stdout, repr(stdout))

    # --- Test 3: Function defined in one cell, called in next ---
    print("\nTest 3: Cross-cell function call")
    run_cell(kc, "fn square(n) {\n    return n * n\n}\n")
    stdout, _, error = run_cell(kc, "print(square(9))\n")
    all_pass &= check("no error", error is None, error)
    all_pass &= check("result is 81", "81" in stdout, repr(stdout))

    # --- Test 4: Syntax error returns error, server stays alive ---
    print("\nTest 4: Syntax error — server survives")
    _, _, error = run_cell(kc, "let x = }\n")
    all_pass &= check("error returned", error is not None, repr(error))
    stdout, _, error2 = run_cell(kc, "print(\"still alive\")\n")
    all_pass &= check("kernel still alive after error", error2 is None, error2)
    all_pass &= check("can print after error", "still alive" in stdout, repr(stdout))

    # --- Test 5: String interpolation ---
    print("\nTest 5: String interpolation")
    stdout, _, error = run_cell(kc, "let name = \"Nodus\"\nprint(\"Welcome to \\(name)!\")\n")
    all_pass &= check("no error", error is None, error)
    all_pass &= check("interpolation works", "Welcome to Nodus!" in stdout, repr(stdout))

    # --- Test 6: List and map operations ---
    print("\nTest 6: Lists and maps")
    stdout, _, error = run_cell(kc, "let nums = [10, 20, 30]\nprint(len(nums))\n")
    all_pass &= check("list len", "3" in stdout, repr(stdout))
    stdout, _, error = run_cell(kc, "let m = {\"a\": 99}\nprint(m[\"a\"])\n")
    all_pass &= check("map access", "99" in stdout, repr(stdout))

    # --- Done ---
    print(f"\n{'='*40}")
    print(f"Result: {'ALL PASS' if all_pass else 'SOME FAILURES'}")

    kc.stop_channels()
    km.shutdown_kernel()
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
