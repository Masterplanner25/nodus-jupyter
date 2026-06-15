"""Nodus Jupyter kernel."""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from typing import cast

from ipykernel.kernelbase import Kernel

from nodus_jupyter import __version__
from nodus_jupyter._completions import completions_for, inspect_token

# Unique string printed between accumulated source and the current cell.
# Splitting stdout on this lets us return only the current cell's output
# even though all previous cells are re-executed to restore function state.
_CELL_SENTINEL = "__NODUS_CELL_BOUNDARY_3f8a1c__"


class NodusKernel(Kernel):
    implementation = "nodus_jupyter"
    implementation_version = __version__
    language = "nodus"
    language_version = "4.0"
    language_info = {
        "name": "nodus",
        "mimetype": "text/x-nodus",
        "file_extension": ".nd",
        "pygments_lexer": "text",
        "codemirror_mode": "python",
    }
    banner = "Nodus — workflow scripting language (nodus-lang)"

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        # All successfully executed cell sources, in order.  Re-compiled as a
        # prefix on each new cell so that function definitions persist across
        # cells without stale bytecode references.
        self._session_source: list[str] = []
        # Latest VM globals — used only for tab completion candidates.
        self._cell_globals: dict = {}

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    def _run_cell(self, code: str) -> tuple[str, str, str | None]:
        """Compile and run *code* in the accumulated session context.

        Returns ``(stdout, stderr, error_message)``.  On success
        ``error_message`` is ``None``.

        All previous cells are prepended and re-executed silently; a sentinel
        print statement marks the boundary so only the current cell's output
        is returned.  This ensures functions defined in earlier cells remain
        callable without requiring bytecode-level address rewriting.
        """
        from nodus.compiler.compiler import normalize_bytecode
        from nodus.runtime.module_loader import ModuleLoader
        from nodus.vm.vm import VM

        if self._session_source:
            prefix = "\n".join(self._session_source)
            full_source = f'{prefix}\nprint("{_CELL_SENTINEL}")\n{code}'
        else:
            full_source = code

        try:
            loader = ModuleLoader(project_root=None)
            raw_bytecode, functions, code_locs = loader.compile_only(
                full_source, module_name="<cell>"
            )
            _, instructions = normalize_bytecode(raw_bytecode)
        except Exception as exc:
            return "", "", f"Compile error: {exc}"

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        child_vm = VM(cast(list, instructions), functions, code_locs=code_locs)

        def _split_output(raw: str) -> str:
            if not self._session_source:
                return raw
            parts = raw.split(_CELL_SENTINEL + "\n", 1)
            return parts[1] if len(parts) > 1 else raw

        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                child_vm.run()

            self._cell_globals = dict(child_vm.globals)
            self._session_source.append(code)

            return _split_output(stdout_buf.getvalue()), stderr_buf.getvalue(), None

        except Exception as exc:
            return (
                _split_output(stdout_buf.getvalue()),
                stderr_buf.getvalue(),
                str(exc),
            )

    def do_execute(
        self,
        code: str,
        silent: bool,
        store_history: bool = True,
        user_expressions: dict | None = None,
        allow_stdin: bool = False,
        *,
        cell_id: object = None,
    ) -> dict:
        if not code.strip():
            return {
                "status": "ok",
                "execution_count": self.execution_count,
                "payload": [],
                "user_expressions": {},
            }

        stdout, stderr, error = self._run_cell(code)

        if not silent:
            if stdout:
                self.send_response(
                    self.iopub_socket, "stream", {"name": "stdout", "text": stdout}
                )
            if stderr:
                self.send_response(
                    self.iopub_socket, "stream", {"name": "stderr", "text": stderr}
                )

        if error is not None:
            if not silent:
                self.send_response(
                    self.iopub_socket,
                    "stream",
                    {"name": "stderr", "text": error + "\n"},
                )
            return {
                "status": "error",
                "execution_count": self.execution_count,
                "ename": "NodusError",
                "evalue": error,
                "traceback": [],
            }

        return {
            "status": "ok",
            "execution_count": self.execution_count,
            "payload": [],
            "user_expressions": {},
        }

    # ------------------------------------------------------------------
    # Tab completion
    # ------------------------------------------------------------------

    def do_complete(self, code: str, cursor_pos: int) -> dict:
        text = code[:cursor_pos]
        token_start = cursor_pos
        for i in range(cursor_pos - 1, -1, -1):
            if not (code[i].isalnum() or code[i] in ("_", ":", ".")):
                break
            token_start = i
        prefix = text[token_start:]

        matches = completions_for(prefix, self._cell_globals)

        return {
            "status": "ok",
            "matches": matches,
            "cursor_start": token_start,
            "cursor_end": cursor_pos,
            "metadata": {},
        }

    # ------------------------------------------------------------------
    # Hover / inspect
    # ------------------------------------------------------------------

    def do_inspect(
        self,
        code: str,
        cursor_pos: int,
        detail_level: int = 0,
        omit_sections: object = (),
    ) -> dict:
        start = cursor_pos
        for i in range(cursor_pos - 1, -1, -1):
            if not (code[i].isalnum() or code[i] in ("_", ":", ".")):
                break
            start = i
        token = code[start:cursor_pos]

        doc = inspect_token(token)
        if doc is None:
            return {"status": "ok", "found": False, "data": {}, "metadata": {}}

        return {
            "status": "ok",
            "found": True,
            "data": {"text/plain": doc},
            "metadata": {},
        }

    # ------------------------------------------------------------------
    # Completeness check (multiline input detection)
    # ------------------------------------------------------------------

    def do_is_complete(self, code: str) -> dict:
        opens = code.count("{") + code.count("(") + code.count("[")
        closes = code.count("}") + code.count(")") + code.count("]")
        if opens > closes:
            return {"status": "incomplete", "indent": "    "}
        return {"status": "complete"}
