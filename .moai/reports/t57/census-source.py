"""recv_frame 호출이 반복문 안에 있는지 AST 로 판별한다."""
import ast, pathlib, sys

root = pathlib.Path("server/tests")
single, collecting = [], []

for path in sorted(root.rglob("*.py")):
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        continue
    # 각 노드에 부모 링크
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = getattr(fn, "id", None) or getattr(fn, "attr", None)
        if name != "recv_frame":
            continue
        # conftest 정의 내부 호출은 제외
        if path.name == "conftest.py":
            continue
        cur, in_loop = node, False
        while hasattr(cur, "parent"):
            cur = cur.parent
            if isinstance(cur, (ast.For, ast.While)):
                in_loop = True
                break
            if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
                break
        entry = f"{path.name}:{node.lineno}"
        (collecting if in_loop else single).append(entry)

print("COLLECTING(반복문 안) =", len(collecting))
for e in collecting:
    print("   ", e)
print("SINGLE(한 장) =", len(single))
print("TOTAL =", len(single) + len(collecting))
