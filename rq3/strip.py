"""Remove comments (and Python docstrings) so no fix rationale leaks through code; string literals preserved."""
import io, tokenize, ast, re
def strip_python(src):
    # drop docstrings
    try:
        t = ast.parse(src); drop = set()
        for n in ast.walk(t):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)) and n.body:
                b = n.body[0]
                if isinstance(b, ast.Expr) and isinstance(getattr(b, "value", None), ast.Constant) and isinstance(b.value.value, str):
                    drop.update(range(b.lineno, b.end_lineno + 1))
        lines = [l for i, l in enumerate(src.splitlines(), 1) if i not in drop]; src = "\n".join(lines) + "\n"
    except SyntaxError:
        pass
    out = []; 
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
        src = tokenize.untokenize([(t.type, t.string) if t.type != tokenize.COMMENT else (tokenize.COMMENT, "") for t in toks]) if False else src
        # line-wise removal of comment tokens keeping layout
        lines = src.splitlines()
        for t in toks:
            if t.type == tokenize.COMMENT:
                r, c = t.start; lines[r - 1] = lines[r - 1][:c].rstrip()
        src = "\n".join(lines)
    except (tokenize.TokenError, IndentationError):
        src = "\n".join(re.sub(r"\s+#.*$", "", l) if not l.lstrip().startswith("#") else "" for l in src.splitlines())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(l for l in src.splitlines() if l.strip() != "" or True))
def strip_c(src):
    out, i, n = [], 0, len(src); st = None
    while i < n:
        c = src[i]; nx = src[i:i+2]
        if st is None:
            if nx == "//":
                j = src.find("\n", i); i = n if j < 0 else j; continue
            if nx == "/*":
                j = src.find("*/", i + 2); i = n if j < 0 else j + 2; continue
            if c in "\"'":
                st = c
            elif src.startswith('r#"', i) or src.startswith('r"', i):
                pass
            out.append(c); i += 1; continue
        out.append(c)
        if c == "\\": out.append(src[i+1:i+2]); i += 2; continue
        if c == st: st = None
        i += 1
    s = "".join(out)
    s = "\n".join(l.rstrip() for l in s.splitlines())
    return re.sub(r"\n\s*\n(\s*\n)+", "\n\n", s)
def strip(src, lang):
    return strip_python(src) if lang == "python" else strip_c(src)
