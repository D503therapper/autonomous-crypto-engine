"""11/14 daily studies - the shared cell / placebo printer (TRAIN / each held season / HELD; z of the mean profit)."""
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402


class Out:
    def __init__(self, tag, train, held):
        self.tag, self.train, self.held, self.lines = tag, train, held, []
        self.c = defaultdict(list)          # name -> [(season, profit, odds)]

    def p(self, *a):
        s = " ".join(str(x) for x in a)
        print(s, flush=True)
        self.lines.append(s)

    def add(self, name, season, prof, odds=None):
        if prof is not None:
            self.c[name].append((season, prof, odds))

    def show(self, prefix=None, minn=1):
        res = {}
        for k in sorted(self.c):
            if prefix and not k.startswith(prefix):
                continue
            v = self.c[k]
            if len(v) < minn:
                continue
            r = lib.summ([(s, p) for s, p, _ in v], self.train, self.held)
            res[k] = r
            self.p(lib.fmt(k, r))
        return res

    def placebo(self, name, pool_name, n=2000, seed=7, fade=False):
        """How many of n random same-size sets from pool_name's rows did as well (fade: as badly)."""
        rs, pool = self.c.get(name, []), self.c.get(pool_name, [])
        if not rs or len(pool) < len(rs):
            return None
        got = sum(p for _, p, _ in rs) / len(rs)
        vals = [p for _, p, _ in pool]
        rnd = random.Random(seed)
        k = len(rs)
        if fade:
            hit = sum(1 for _ in range(n) if sum(rnd.sample(vals, k)) / k <= got)
        else:
            hit = sum(1 for _ in range(n) if sum(rnd.sample(vals, k)) / k >= got)
        self.p(f"  placebo {name} vs {pool_name}: {hit} of {n} random sets did as {'badly' if fade else 'well'}"
               f" (cell {got*100:+.1f}%, pool {sum(vals)/len(vals)*100:+.1f}% on {len(vals)})")
        return hit

    def save(self):
        open(os.path.join(os.path.dirname(os.path.abspath(__file__)), self.tag + "_out.txt"), "w").write(
            "\n".join(self.lines) + "\n")


def band(o):
    """'fav' (-150..-101), 'dog' (+100..+350), or None."""
    if o is None:
        return None
    if -150 <= o <= -101:
        return "fav"
    if 100 <= o <= 350:
        return "dog"
    return None
