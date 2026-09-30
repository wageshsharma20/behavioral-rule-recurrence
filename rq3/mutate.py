"""Rule-blind first-order mutation of target functions (GOOD version) — AST based, deterministic.
Operators: SD statement->pass, NC negate if/while/ifexp test, SL non-empty str const -> "", CR comparison swap,
BD binop a+b -> a. Usage: python mutate.py <file> <Qualified.func,...> <outdir> [max=30] -> writes mutant files + index.json"""
import ast, copy, json, os, random, sys
SWAP = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.GtE, ast.GtE: ast.Lt, ast.Gt: ast.LtE, ast.LtE: ast.Gt,
        ast.In: ast.NotIn, ast.NotIn: ast.In, ast.Is: ast.IsNot, ast.IsNot: ast.Is}
def targets(tree, names):
    out = []
    def walk(node, prefix=""):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = prefix + ch.name
                if q in names: out.append(ch)
                walk(ch, q + ".")
            elif isinstance(ch, ast.ClassDef): walk(ch, prefix + ch.name + ".")
    walk(tree); return out
def sites(fn):
    s = []
    for n in ast.walk(fn):
        if n is fn: continue
        if isinstance(n, (ast.Assign, ast.AugAssign, ast.Expr, ast.AnnAssign)) and not (
                isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Constant)):
            s.append(("SD", n))
        if isinstance(n, (ast.If, ast.While, ast.IfExp)): s.append(("NC", n))
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value: s.append(("SL", n))
        if isinstance(n, ast.Compare) and type(n.ops[0]) in SWAP: s.append(("CR", n))
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add): s.append(("BD", n))
    return s
class Apply(ast.NodeTransformer):
    def __init__(self, op, lineno, col, kind): self.k = (op, lineno, col, kind); self.done = False
    def _match(self, n): return (getattr(n, "lineno", None), getattr(n, "col_offset", None), type(n).__name__) == self.k[1:]
    def generic_visit(self, node):
        super().generic_visit(node); return node
    def visit(self, node):
        if not self.done and self._match(node):
            op = self.k[0]; self.done = True
            if op == "SD": return ast.copy_location(ast.Pass(), node)
            if op == "NC":
                node.test = ast.UnaryOp(op=ast.Not(), operand=node.test); return node
            if op == "SL": return ast.copy_location(ast.Constant(value=""), node)
            if op == "CR":
                node.ops = [SWAP[type(node.ops[0])]()] + node.ops[1:]; return node
            if op == "BD": return node.left
        return super().visit(node)
def main(path, names, outdir, maxn=30):
    src = open(path).read(); tree = ast.parse(src); names = set(names.split(","))
    allsites = []
    for fn in targets(tree, names):
        for op, n in sites(fn):
            allsites.append((op, n.lineno, n.col_offset, type(n).__name__, fn.name))
    random.Random(0).shuffle(allsites); os.makedirs(outdir, exist_ok=True); idx = []
    for i, (op, ln, col, kind, fname) in enumerate(allsites[:maxn]):
        t = ast.parse(src); a = Apply(op, ln, col, kind); t = a.visit(t)
        if not a.done: continue
        ast.fix_missing_locations(t)
        try: code = ast.unparse(t)
        except Exception: continue
        mid = f"m{i:02d}_{op}_{fname}_L{ln}"; open(os.path.join(outdir, mid + ".py"), "w").write(code)
        idx.append({"id": mid, "op": op, "line": ln, "col": col, "kind": kind, "function": fname})
    json.dump({"source": path, "functions": sorted(names), "n_sites": len(allsites), "mutants": idx},
              open(os.path.join(outdir, "index.json"), "w"), indent=1)
    print(f"{path}: {len(allsites)} sites, {len(idx)} mutants written")
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 30)
