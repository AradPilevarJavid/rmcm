# rmcm

`rmcm` removes Python comments and docstrings while preserving executable
code. It uses Python's tokenizer and syntax tree, so comment-like text inside
strings is kept. Files must contain valid Python syntax. Shebangs and encoding
cookies are preserved, and empty function/class bodies receive `pass` after
their docstrings are removed.

## Requirements

Python 3.8 or newer. The command has no third-party Python dependencies.

## Install

### NixOS / Nix

Add the flake as an input:

```nix
inputs.rmcm.url = "github:thecosmomancer/rmcm";
```

Then add `inputs.rmcm.packages.${system}.default` to
`environment.systemPackages` (or to `home.packages` in Home Manager). To run
without installing, use `nix run github:thecosmomancer/rmcm -- --help`.

### Other systems

Clone the repository and install the script on your PATH:

```sh
git clone https://github.com/thecosmomancer/rmcm.git
cd rmcm
python3 --version
chmod +x rmcm.py
sudo install -m 755 rmcm.py /usr/local/bin/rmcm
```

Alternatively, run it directly as `python3 rmcm.py ...`. The `setup.sh`
script performs the same system-wide install and requires `sudo` access to
`/usr/local/bin`.

## Commands

```text
rmcm --help
```

`--help` displays the available options and exits. The complete help output is:

```text
usage: rmcm [-h] -i INPUT [-o OUTPUT | -O] [-p]

Remove comments and docstrings from Python files.

options:
  -h, --help           show this help message and exit
  -i INPUT, --input INPUT
                       path to input file ('-' for stdin)
  -o OUTPUT, --output OUTPUT
                       path to output file
  -O, --overwrite      overwrite input file
  -p, --print          print output to stdout
```

`-i` / `--input` is required. Give it a Python file path, or `-` to read from
standard input. Choose at least one destination:

- `-o PATH` / `--output PATH` writes the cleaned source to `PATH` without
  changing the input. The output file is written atomically.
- `-O` / `--overwrite` replaces the input file. This cannot be used with
  standard input.
- `-p` / `--print` writes the cleaned source to standard output. It can be
  combined with either file destination.

`-o` and `-O` are mutually exclusive. `-p` alone is a valid destination.

Examples:

```sh
# Write a separate output file
rmcm -i script.py -o script.clean.py

# Replace the input file in place
rmcm -i script.py -O

# Print cleaned source to the terminal
rmcm -i script.py -p

# Read from a pipe and print the result
cat script.py | rmcm -i - -p

# Save to a file and also print the result
rmcm --input script.py --output script.clean.py --print
```

Successful file writes print a short status message to standard output. Use
`-p` when you want the transformed source on standard output. Invalid Python
or file read/write errors are reported to standard error, and the command
returns a nonzero exit status.

## License

MIT. See [LICENSE](LICENSE) if present in the source distribution.
