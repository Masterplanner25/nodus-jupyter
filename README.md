# nodus-jupyter

> **Status:** v0.1.0 — published on [PyPI](https://pypi.org/project/nodus-jupyter/).

Jupyter kernel for the [Nodus](https://github.com/Masterplanner25/Nodus) language. Write and run `.nd` files directly in JupyterLab, Jupyter Notebook, or VS Code notebooks.

## Install

```
pip install nodus-jupyter
python -m nodus_jupyter install
```

Then start Jupyter and select **Nodus** from the kernel list.

## Features

- **Persistent state** — variables and functions defined in one cell are available in all subsequent cells
- **Tab completion** — keywords, builtins, stdlib modules, and user-defined names
- **Hover docs** — inspect builtin functions and stdlib modules inline
- **Multiline detection** — open braces trigger continuation mode automatically

## Requirements

- Python ≥ 3.10
- `nodus-lang >= 4.0.0`
- `ipykernel >= 6.0`

## Example

```nodus
# Cell 1
fn greet(name) {
    return "Hello, \(name)!"
}
```

```nodus
# Cell 2 — function from Cell 1 is available
print(greet("Nodus"))
```

## VS Code

Works with VS Code notebooks via the [Nodus Language](https://marketplace.visualstudio.com/items?itemName=MasterplanInfiniteWeave.nodus-lang) extension. Select the Nodus kernel in the notebook kernel picker.

## License

MIT
