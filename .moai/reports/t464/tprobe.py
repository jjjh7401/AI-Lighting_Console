"""console_probe.main 을 감싸 >>>/<<< 줄 앞에 벽시계(ms)를 붙인다 (t464).

프로젝트 루트에서 실행한다::

    .venv/bin/python .moai/reports/t464/tprobe.py --listen-port 9005 --pause 1.0 STEP ...
"""

import builtins
import datetime
import importlib.util
import sys

_print = builtins.print


def _timed_print(*args, **kwargs):
    stamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    if args and isinstance(args[0], str) and args[0].lstrip("\n").startswith((">>>", "<<<")):
        first = args[0].replace(">>>", f"[{stamp}] >>>", 1).replace("<<<", f"[{stamp}] <<<", 1)
        args = (first, *args[1:])
    _print(*args, **kwargs)


def main() -> int:
    sys.path.insert(0, ".")
    builtins.print = _timed_print
    spec = importlib.util.spec_from_file_location("console_probe", "tools/console_probe.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
