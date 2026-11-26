#! /usr/bin/env python3

import argparse
import ast
import io
import os
import re
import sys
import tempfile
import tokenize

CODING_COOKIE = re.compile(r"^[ \t\f]*#.*?coding[:=][ \t]*[-_.a-zA-Z0-9]+")

STRUCTURAL_TOKENS = {
    tokenize.NEWLINE,
    tokenize.NL,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.ENDMARKER,
}


def is_docstring_expression(node):
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def character_column(line, byte_column):
    """Convert an AST UTF-8 byte offset to a Python string column."""
    return len(line.encode("utf-8")[:byte_column].decode("utf-8"))


def docstring_spans(tree, source_text):
    spans = []
    lines = source_text.splitlines(keepends=True)
    for node in ast.walk(tree):
        if not isinstance(
            node,
            (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue
        if not node.body or not is_docstring_expression(node.body[0]):
            continue
        expression = node.body[0]
        needs_pass = not isinstance(node, ast.Module) and len(node.body) == 1
        spans.append(
            (
                expression.lineno,
                character_column(
                    lines[expression.lineno - 1], expression.col_offset
                ),
                expression.end_lineno,
                character_column(
                    lines[expression.end_lineno - 1], expression.end_col_offset
                ),
                needs_pass,
            )
        )
    return spans


def find_span(token, spans):
    start_line, start_col = token.start
    end_line, end_col = token.end
    for span in spans:
        starts_after = (start_line, start_col) >= (span[0], span[1])
        ends_before = (end_line, end_col) <= (span[2], span[3])
        if starts_after and ends_before:
            return span
    return None


def is_protected_comment(token, source_lines):
    if token.type != tokenize.COMMENT:
        return False
    line_no = token.start[0]
    if line_no == 1 and token.string.startswith("#!"):
        return True
    if line_no <= 2 and CODING_COOKIE.match(source_lines[line_no - 1]):
        return True
    return False


def remove_comments_and_docstrings(source):
    tree = ast.parse(source)
    spans = docstring_spans(tree, source)
    source_lines = source.splitlines(keepends=True)

    io_obj = io.StringIO(source)
    out_tokens = []
    protected_lines = set()

    last_lineno = -1
    last_col = 0
    line_index = 0
    emitted_pass = set()
    removed_docstring_end = None

    for tok in tokenize.generate_tokens(io_obj.readline):
        token_type, token_string, start, end, line = tok
        start_line, start_col = start
        end_line, end_col = end

        if start_line > last_lineno:
            last_col = 0

        span = find_span(tok, spans)
        needs_pass = span is not None and span[4] and span not in emitted_pass
        emit = span is None or needs_pass

        if token_type == tokenize.OP and token_string == ";" and removed_docstring_end:
            if removed_docstring_end[0] == start_line and removed_docstring_end[1] <= start_col:
                # The separator after a removed inline docstring is redundant.
                emit = False
            removed_docstring_end = None

        if emit and start_col > last_col:
            out_tokens.append(" " * (start_col - last_col))

        if needs_pass:
            out_tokens.append("pass")
            emitted_pass.add(span)
        elif span is not None:
            removed_docstring_end = (end_line, end_col)
        elif not emit:
            pass
        elif token_type == tokenize.COMMENT:
            if is_protected_comment(tok, source_lines):
                out_tokens.append(token_string)
        else:
            out_tokens.append(token_string)

        if token_type not in STRUCTURAL_TOKENS and "\n" in token_string:
            protected_lines.update(
                range(line_index, line_index + token_string.count("\n") + 1)
            )
        line_index += token_string.count("\n")

        last_lineno = end_line
        last_col = end_col

    cleaned = "".join(out_tokens)

    lines = cleaned.split("\n")
    result_lines = []
    blank_run = 0
    for index, ln in enumerate(lines):
        if index in protected_lines:
            result_lines.append(ln)
            blank_run = 0
            continue
        if ln.strip() == "":
            blank_run += 1
            if blank_run <= 1:
                result_lines.append("")
        else:
            blank_run = 0
            result_lines.append(ln.rstrip())

    return "\n".join(result_lines).strip("\n") + "\n"


def remove_slash_comments(source, line_comments=True):
    """Remove C/CSS comments without interpreting comment markers in strings."""
    result = []
    i = 0
    state = "code"
    quote = None
    while i < len(source):
        char = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
        if state == "line_comment":
            if char in "\r\n":
                result.append(char)
                state = "code"
            else:
                result.append(" " if char != "\t" else "\t")
            i += 1
            continue
        if state == "block_comment":
            if char == "*" and nxt == "/":
                result.extend((" ", " "))
                i += 2
                state = "code"
            else:
                if char in "\r\n":
                    result.append(char)
                else:
                    result.append("\t" if char == "\t" else " ")
                i += 1
            continue
        if state == "string":
            result.append(char)
            if char == "\\" and nxt:
                result.append(nxt)
                i += 2
                continue
            if char == quote:
                state = "code"
                quote = None
            i += 1
            continue
        if char in ("'", '"'):
            result.append(char)
            quote = char
            state = "string"
            i += 1
            continue
        if char == "/" and nxt == "*":
            result.extend((" ", " "))
            i += 2
            state = "block_comment"
            continue
        matched = line_comments and source.startswith("//", i)
        if matched:
            result.extend((" ", " "))
            i += 2
            state = "line_comment"
            continue
        result.append(char)
        i += 1
    return "".join(result)


def clean_source(source, language):
    if language == "python":
        return remove_comments_and_docstrings(source)
    if language == "c":
        return remove_slash_comments(source)
    if language == "css":
        return remove_slash_comments(source, line_comments=False)
    raise ValueError(f"unsupported language: {language}")


def read_source(path):
    if path == "-":
        return sys.stdin.read(), "utf-8"
    with tokenize.open(path) as f:
        return f.read(), f.encoding


def write_atomic(path, text, encoding):
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".rmcm-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
            f.write(text)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="rmcm",
        description="Remove comments from source files (Python is the default).",
    )
    parser.add_argument(
        "-i",
        "--input",
        help="path to input file ('-' for stdin)",
        required=True,
    )
    parser.add_argument(
        "-l",
        "--language",
        "--lang",
        choices=("python", "c", "css"),
        default="python",
        help="source language (default: python)",
    )
    parser.add_argument(
        "--python",
        dest="language",
        action="store_const",
        const="python",
        help="select Python (the default)",
    )
    parser.add_argument(
        "-c",
        dest="language",
        action="store_const",
        const="c",
        help="select C-style comments",
    )
    parser.add_argument(
        "--css",
        dest="language",
        action="store_const",
        const="css",
        help="select CSS comments",
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("-o", "--output", help="path to output file")
    action.add_argument(
        "-O", "--overwrite", action="store_true", help="overwrite input file"
    )
    parser.add_argument(
        "-p", "--print", action="store_true", help="print output to stdout"
    )
    args = parser.parse_args(argv)

    if not args.print and not args.overwrite and args.output is None:
        parser.error("select an output with -p, -O or -o {filepath}")

    if args.overwrite and args.input == "-":
        parser.error("cannot overwrite stdin")

    output_path = args.input if args.overwrite else args.output

    try:
        source, encoding = read_source(args.input)
        cleaned = clean_source(source, args.language)
    except (SyntaxError, tokenize.TokenError, UnicodeDecodeError, ValueError) as e:
        print(f"rmcm: failed to process {args.input}: {e}", file=sys.stderr)
        return 1

    if output_path is not None:
        try:
            write_atomic(output_path, cleaned, encoding)
        except OSError as e:
            print(f"rmcm: failed to write {output_path}: {e}", file=sys.stderr)
            return 1
        print(f"Wrote cleaned file to {output_path}")

    if args.print:
        sys.stdout.write(cleaned)

    return 0


if __name__ == "__main__":
    sys.exit(main())
