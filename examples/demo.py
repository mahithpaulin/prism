"""Prism demo: notice a cycle, attempt a proof, combine honestly."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prism import Prism

CLOSURE = (
    "edge(a, b).\nedge(b, c).\n"
    "path(X, Y) :- edge(X, Y).\n"
    "path(X, Z) :- path(X, Y), edge(Y, Z).\n"
    "?- path(a, c).\n"
)


def main():
    p = Prism()
    print("health:", p.health())
    obs = p.notice(list("ABC" * 10))
    print("notice:", obs["status"], "|", str(obs.get("explanation", ""))[:160])
    print("patterns:", len(obs.get("patterns", [])), "anomalies:", len(obs.get("anomalies", [])))
    pf = p.prove(CLOSURE)
    print("prove:", pf.get("status"), "|", pf.get("summary", ""))
    combo = p.notice_then_prove(list("ABC" * 10), CLOSURE)
    print("verdict:", combo["verdict"]["verdict"], "via", combo["verdict"]["source"])


if __name__ == "__main__":
    main()
