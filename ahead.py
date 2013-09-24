#!/usr/bin/env python
#
# Oldest, clumsiest implementation. Orochi cset-based with parallel visitors.
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

class Done(Exception):
    pass

class Ahead(object):
    def __init__(self, branches, main):
        self.bmap = {bh.name: bh for bh in branches if bh != main}
        self.b2c = {}
        self.c2b = defaultdict(set)
        for bh in [bh for bh in branches if bh != main]:
            self.b2c[bh.name] = (set(bh.heads()), 0)
            for head in bh.heads():
                self.c2b[head].add(bh.name)

        self.exclude = set(main.heads())
        self.include = heads - self.exclude

    @property
    def counts(self):
        return {self.bmap[bname]: stats[1] for bname, stats in self.b2c.items()}

    def visit(self, cs):
        if cs in self.exclude:
            parents = cs.parents()
            self.include.difference_update(parents)
            self.exclude.remove(cs)
            self.exclude.update(parents)

            for b in self.c2b.pop(cs, tuple()):
                parents, ahead = self.b2c[b]
                parents.remove(cs)
                self.b2c[b] = (parents, ahead)
            if not self.c2b:
                # all branches have been terminated
                raise Done

        elif cs in self.include:
            self.include.remove(cs)
            bnames = self.c2b.pop(cs)
            liveparents = set(cs.parents()) - self.exclude

            for b in bnames:
                next, ahead = self.b2c[b]
                next.remove(cs)
                next.update(liveparents)
                self.b2c[b] = (next, ahead + 1)

            for p in liveparents:
                self.c2b[p].update(bnames)
            self.include.update(liveparents)
        else:
            print 'WTF', cs.hash, cs.desc.split('\n')[:1][:30]

class Behind(object):
    def __init__(self, branch, main):
        self.branch = branch
        self.exclude = set(branch.heads())
        self.include = set(main.heads()) - self.exclude
        self.count = 0

    def visit(self, cs):
        if not self.include:
            raise Done
        else:
            parents = cs.parents()
            if self.exclude and cs in self.exclude:
                self.include.difference_update(parents)
                self.exclude.remove(cs)
                # exclude its parents too:
                self.exclude.update(parents)
            elif cs in self.include:
                self.count += 1
                self.include.remove(cs)
                for p in parents:
                    if p not in self.exclude:
                        self.include.add(p)


start = time.time()
with r.walk(include=heads) as walker:

    ahead = Ahead(branches, main)
    behinds = {}
    for b in [b for b in branches if b != main]:
        behinds[b] = Behind(b, main)

    visitors = {ahead}
    visitors.update(behinds.values())
    dead = set()

    for cs in walker:
        if not visitors:
            break
        for visitor in visitors:
            try:
                visitor.visit(cs)
            except Done:
                dead.add(visitor)

        while dead:
            visitors.remove(dead.pop())

duration = time.time() - start
for b in [b for b in sorted(branches, key=lambda _b: _b.resolve().date, reverse=True) if b != main]:
    print '%s [%d ahead] [%d behind] on %s' % (b.name, ahead.counts[b], behinds[b].count, main.name)
print 'runtime: %.3f seconds' % duration