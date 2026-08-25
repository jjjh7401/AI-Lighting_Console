"""recv_frame 자리를 「실행 문맥」으로 분류한다 (census v2).

v1 의 결함(감사 DEBT-1): 부모 사슬을 함수 경계에서 끊어서, 얇은 래퍼 안의
recv_frame 을 SINGLE 로 셌다. 래퍼가 반복문에서 불리면 그 자리는 사실상
모으는 자리다 — 구문 문맥이 아니라 실행 문맥이 질문이었다.

v2: SINGLE 로 분류된 자리의 감싼 함수를 찾고, 그 함수가 반복문 안에서
불리는 자리가 있으면 COLLECTING(래퍼 경유)로 재분류한다.

[알려진 경계 — 이 계기가 답하지 못하는 것]
- 호출 추적은 1단계다. 래퍼의 래퍼는 안 따라간다.
- 이름 기준이라 동명 함수가 여러 파일에 있으면 합쳐서 본다(보수적: 과대 분류).
- 파이썬 동적 호출(getattr, 딕셔너리 디스패치)은 못 본다.
"""
import ast, pathlib

root = pathlib.Path("server/tests")
files = {}
for path in sorted(root.rglob("*.py")):
    try:
        files[path] = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        pass

for tree in files.values():
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent


def enclosing_func(node):
    cur = node
    while hasattr(cur, "parent"):
        cur = cur.parent
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur
    return None


def in_loop_within_function(node):
    cur = node
    while hasattr(cur, "parent"):
        cur = cur.parent
        if isinstance(cur, (ast.For, ast.While)):
            return True
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
            return False
    return False


def calls_of(name):
    out = []
    for path, tree in files.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                if (getattr(fn, "id", None) or getattr(fn, "attr", None)) == name:
                    out.append((path, node))
    return out


single, collecting, wrapper_mediated = [], [], []

for path, tree in files.items():
    if path.name == "conftest.py":
        continue
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if (getattr(fn, "id", None) or getattr(fn, "attr", None)) != "recv_frame":
            continue
        entry = f"{path.name}:{node.lineno}"
        if in_loop_within_function(node):
            collecting.append(entry)
            continue
        holder = enclosing_func(node)
        promoted = False
        if holder is not None:
            for cpath, cnode in calls_of(holder.name):
                if in_loop_within_function(cnode):
                    wrapper_mediated.append(
                        entry + "  (via " + holder.name + " @ " + cpath.name + ":" + str(cnode.lineno) + ")"
                    )
                    promoted = True
                    break
        if not promoted:
            single.append(entry)

print("COLLECTING (직접 반복문 안) =", len(collecting))
for e in collecting:
    print("   ", e)
print("COLLECTING (래퍼 경유) =", len(wrapper_mediated))
for e in wrapper_mediated:
    print("   ", e)
print("SINGLE =", len(single))
print("TOTAL =", len(single) + len(collecting) + len(wrapper_mediated))
