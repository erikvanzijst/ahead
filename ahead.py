#!/usr/bin/env python
from collections import defaultdict

import sys
import itertools
import time

from orochi.repo import Repo

path = '.'
bname = None
if len(sys.argv) > 2:
    # main branch specified
    bname = sys.argv[2]
if len(sys.argv) > 1:
    # repo path specified
    path = sys.argv[1]

r = Repo.open(path)
main = bname and r.getbranch(bname) or r.mainbranch()

if len(sys.argv) > 3:
    # branches specified
    branches = set([b for b in r.branches() if b.name in sys.argv[3:]] + [main])
else:
    branches = r.branches()
heads = set(itertools.chain(*[b.heads() for b in branches]))

start = time.time()
with r.walk(include=heads) as walker:

    b2c = {}
    c2b = defaultdict(set)
    for bh in [bh for bh in branches if bh != main]:
        b2c[bh.name] = (set(bh.heads()), 0)
        for head in bh.heads():
            c2b[head].add(bh.name)
    mcount = 0

    exclude = set(main.heads())
    include = heads - exclude

    class Done(Exception):
        pass

    def ahead(cs):
        if cs in exclude:
            parents = cs.parents()
            include.difference_update(parents)
            exclude.remove(cs)
            exclude.update(parents)

            for b in c2b.pop(cs, tuple()):
                parents, ahead = b2c[b]
                parents.remove(cs)
                b2c[b] = (parents, ahead)
            if not c2b:
                # all branches have been terminated
                raise Done

        elif cs in include:
            include.remove(cs)
            bnames = c2b.pop(cs)
            liveparents = set(cs.parents()) - exclude

            for b in bnames:
                next, ahead = b2c[b]
                next.remove(cs)
                next.update(liveparents)
                b2c[b] = (next, ahead + 1)

            for p in liveparents:
                c2b[p].update(bnames)
            include.update(liveparents)
        else:
            print 'WTF', cs.hash, cs.desc.split('\n')[:1][:30]

    funcs = {ahead}
    dead = set()

    for cs in walker:
        if not funcs:
            break
        for func in funcs:
            try:
                func(cs)
            except Done:
                dead.add(func)

        while dead:
            funcs.remove(dead.pop())

duration = time.time() - start
for bname, stats in b2c.items():
    print '%s [%d ahead] on %s' % (bname, stats[1], main.name)
    if stats[0]:
        print 'ERROR: parent nodes left for branch %s: %s' % (bname, stats[0])
print 'runtime: %.3f seconds' % duration