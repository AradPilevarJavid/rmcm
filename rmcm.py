#! /usr/bin/env python3

def remove_comments_and_docstrings(source):

    import ast
    import io
    import tokenize

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
            if node.body and is_docstring_expression(node.body[0]):
                expression = node.body[0]
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
                    )
                )
        return spans

    def token_in_docstring(token, spans):
        start_line, start_col = token.start
        end_line, end_col = token.end
        for span_start_line, span_start_col, span_end_line, span_end_col in spans:
            starts_after = (start_line, start_col) >= (span_start_line, span_start_col)
            ends_before = (end_line, end_col) <= (span_end_line, span_end_col)
            if starts_after and ends_before:
                return True
        return False

    tree = ast.parse(source)
    spans = docstring_spans(tree, source)

    io_obj = io.StringIO(source)
    out_tokens = []

    last_lineno = -1
    last_col = 0

    tokens = tokenize.generate_tokens(io_obj.readline)

    for tok in tokens:
        token_type, token_string, start, end, line = tok
        start_line, start_col = start
        end_line, end_col = end

        if start_line > last_lineno:
            last_col = 0
        skip = token_in_docstring(tok, spans)
        if not skip and start_col > last_col:
            out_tokens.append(" " * (start_col - last_col))

        if skip or token_type == tokenize.COMMENT:
            pass
        else:
            out_tokens.append(token_string)

        last_lineno = end_line
        last_col = end_col

    cleaned = "".join(out_tokens)

    lines = cleaned.split("\n")
    result_lines = []
    blank_run = 0
    for ln in lines:
        if ln.strip() == "":
            blank_run += 1
            if blank_run <= 1:
                result_lines.append("")
        else:
            blank_run = 0
            result_lines.append(ln.rstrip())

    return "\n".join(result_lines).strip("\n") + "\n"

def main():
    from tokenize import TokenError
    from sys import stderr
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='path to input file', required=True)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('-o', '--output', help='path to output file')
    action.add_argument('-O', '--overwrite', action='store_true', help='overwrite input file')
    parser.add_argument('-p', '--print', action='store_true', help='print output to stdout')
    args = parser.parse_args()

    if not args.print and not args.overwrite and args.output is None:
        print("Select output format with -p, -O or -o {filepath}")
        exit(1)

    input_path = args.input
    output_path = args.input if args.overwrite else args.output

    with open(input_path, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        cleaned = remove_comments_and_docstrings(source)
    except TokenError as e:
        print(f"Failed to tokenize {input_path}: {e}", file=stderr)
        exit(1)

    if output_path is not None:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(cleaned)
        print(f"Wrote cleaned file to {output_path}")

    if args.print:
        print(cleaned)


if __name__ == "__main__":
    main()
