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
        b2c[bh.name] = (set(bh.heads()), 0, 0)
        for head in bh.heads():
            c2b[head].add(bh.name)
    mcount = 0

    exclude = set(main.heads())
    include = heads - exclude

    for cs in walker:
        if cs in exclude:
#            print 'exclude', cs.hash, mcount, cs.desc.split('\n')[:1][:30]
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
#                print 'breaking out'
                break
            mcount += 1

        elif cs in include:
#            print 'include', cs.hash, mcount, cs.desc.split('\n')[:1][:30]
            include.remove(cs)
            bnames = c2b.pop(cs)
            liveparents = set(cs.parents()) - exclude

            for b in bnames:
                next, ahead, behind = b2c[b]
                next.remove(cs)
                next.update(liveparents)
                b2c[b] = (next, ahead + 1, mcount)

            for p in liveparents:
#                print 'add live parent', p.hash, mcount, p.desc.split('\n')[:1][:30]
                c2b[p].update(bnames)
#            else:
#                print 'dead parents', cs.parents(), exclude
            include.update(liveparents)
        else:
            print 'WTF', cs.hash, cs.desc.split('\n')[:1][:30]

duration = time.time() - start
for bname, stats in b2c.items():
    print '%s [%d ahead] [%s behind] on %s' % (bname, stats[1], stats[2], main.name)
    if stats[0]:
        print 'ERROR: parent nodes left for branch %s: %s' % (bname, stats[0])
print 'runtime: %.3f seconds' % duration