import sys

from . import build, fetch, gloss


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in {"fetch", "gloss", "build", "all"}:
        sys.exit("usage: python3 -m vira {fetch|gloss|build|all}")
    cmd = sys.argv.pop(1)
    if cmd in ("fetch", "all"):
        fetch.run()
    if cmd in ("gloss", "all"):
        gloss.run()
    if cmd in ("build", "all"):
        build.run()


if __name__ == "__main__":
    main()
