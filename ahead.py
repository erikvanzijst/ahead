#!/usr/bin/env python
from collections import defaultdict

import sys
import itertools
import time

from orochi.repo import Repo

path = '.'
bname = None
if len(sys.argv) > 2:
    bname = sys.argv[2]
if len(sys.argv) > 1:
    path = sys.argv[1]

r = Repo.open(path)
main = bname and r.getbranch(bname) or r.mainbranch()

branches = set(itertools.chain(*[b.heads() for b in r.branches()]))
start = time.time()
with r.walk(include=branches) as walker:

    b2c = {}
    c2b = defaultdict(set)
    for bh in [bh for bh in r.branches() if bh != main]:
        b2c[bh.name] = (set(bh.heads()), 0, 0)
        for head in bh.heads():
            c2b[head].add(bh.name)
    mcount = 0

    exclude = set(main.heads())
    include = branches - exclude

    for cs in walker:
        if cs in exclude:
            print 'exclude', cs.hash, cs.desc.split('\n')[:1][:30]
            parents = cs.parents()
            include.difference_update(parents)
            exclude.remove(cs)
            exclude.update(parents)

            for b in c2b.pop(cs, tuple()):
                parents, ahead, behind = b2c[b]
                parents.remove(cs)
                b2c[b] = (parents, ahead, mcount)
            if not c2b:
                # all branches have been terminated
                break
            mcount += 1

        elif cs in include:
            print 'include', cs.hash, cs.desc.split('\n')[:1][:30]
            include.remove(cs)
            parents = cs.parents()
            branches = c2b.pop(cs)

            for b in branches:
                next, ahead, behind = b2c[b]
                next.remove(cs)
                next.update(parents)
                b2c[b] = (next, ahead + 1, behind)

            for p in parents:
                c2b[p].update(branches)
                if p not in exclude:
                    include.add(p)
        else:
            print 'WTF', cs.hash, cs.desc.split('\n')[:1][:30]

duration = time.time() - start
for bname, stats in b2c.items():
    print '%s [%d ahead] [%s behind] on %s' % (bname, stats[1], stats[2], main.name)
    if stats[0]:
        print 'ERROR: parent nodes left for branch %s: %s' % (bname, stats[0])
print 'runtime: %.3f seconds' % duration