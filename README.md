# rmcm

`rmcm` removes comments from Python, C, and CSS source files. Python is the
default and its docstrings are removed as well. The C and CSS scanners preserve
quoted strings and newlines while replacing comments with whitespace, so code
before and after a comment does not accidentally join together.

## Requirements and installation

Python 3.8 or newer is required. The program itself has no runtime
dependencies.

Install from a cloned source tree for the current user:

```sh
git clone https://github.com/thecosmomancer/rmcm.git
cd rmcm
python3 -m pip install --user .
```

The `bash setup.sh` script runs the same install. Make sure Python's user
`bin` directory is on your `PATH`. To install into an active virtual
environment, run `python3 -m pip install .` instead. You can also run the
source directly: `python3 rmcm.py --help`.

The project includes `pyproject.toml`, so standard Python packaging tools can
build and install a wheel or source archive. The license and README are included
as project metadata. Nix users can add `inputs.rmcm.packages.${system}.default`
to `environment.systemPackages` or Home Manager's `home.packages`; for a
one-off invocation use:

```sh
nix run github:thecosmomancer/rmcm -- --help
```

## Help

Run `rmcm --help` for the options supported by the installed command:

```text
usage: rmcm [-h] (-i INPUT | -a [DIRECTORY]) [-l {python,c,css,rust}]
            [--python] [-c] [--css] [-r] [-o OUTPUT | -O] [-p]

Remove comments from source files (Python is the default).

options:
  -h, --help            show this help message and exit
  -i, --input INPUT     path to input file ('-' for stdin)
  -a, --all [DIRECTORY]
                        recursively remove comments from every supported file
                        under DIRECTORY (default: current directory)
  -l, --language, --lang {python,c,css,rust}
                        source language (default: python)
  --python              select Python (the default)
  -c                    select C-style comments
  --css                 select CSS comments
  -r, --rust            select Rust comments
  -o, --output OUTPUT   path to output file
  -O, --overwrite       overwrite input file
  -p, --print           print output to stdout
```

Python is selected by default. Use `--python` or `--lang python` to state it
explicitly. `-p` retains its existing meaning: print the cleaned source to
standard output.

## Commands

Select a target with either `-i PATH` / `--input PATH` or `-a [DIRECTORY]` /
`--all [DIRECTORY]`.

### Single files

Set the source language with one of:

- `--python` or `--lang python` for Python (the default). Removes Python
  comments and module, class, and function docstrings.
- `-c` or `--lang c` for standard C line (`//`) and block (`/* ... */`)
  comments.
- `--css` or `--lang css` for CSS block (`/* ... */`) comments.
- `-r`, `--rust`, or `--lang rust` for Rust `//` comments and nested
  `/* ... */` comments. Rust raw strings, byte strings, character literals,
  and lifetimes are preserved.

The C selector handles standard C lexical strings and character literals; it
does not claim C++-specific syntax. CSS line comments are not treated as
comments. In all modes, `-i -` reads source from standard input.

### Whole directories

`-a` / `--all` walks the directory (the current directory when no path is given)
recursively and cleans every supported file in place. The language is chosen by
file extension: `.py` and `.pyw` as Python, `.c` and `.h` as C, `.css` as CSS,
and `.rs` as Rust. Other files are left untouched, as are hidden directories
and `__pycache__`/`node_modules`. Failed files are reported and left as they
were; the command exits nonzero if any file failed.

```sh
# Clean every supported file under the current directory
rmcm -a

# Clean a project subtree
rmcm -a src
```

### Output

Choose where the result goes:

- `-o PATH` / `--output PATH` writes to a separate file atomically.
- `-O` / `--overwrite` replaces the input file. This cannot be used with
  standard input.
- `-p` / `--print` prints the result to standard output. It can be combined
  with either file destination; by itself it is enough to select an output.

`-o` and `-O` are mutually exclusive. These options apply to `-i` only and are
rejected with `-a`, which always writes in place. File output prints a status
message to standard output. Errors go to standard error and return a nonzero
exit status.

Examples:

```sh
# Python is the default; write cleaned source separately
rmcm -i input.py -o output.py

# Select Python explicitly (the -p option below means print)
rmcm --python -i input.py -p

# Remove C comments as requested
rmcm -c -i input.c -o output.c

# Remove CSS comments in place
rmcm --css -i styles.css -O

# Remove Rust comments while preserving Rust literals
rmcm --rust -i src/main.rs -o /tmp/main.cleaned.rs

# Read Python source from a pipe and print the result
cat input.py | rmcm -i - -p
```

## License

MIT. See [LICENSE](LICENSE).
