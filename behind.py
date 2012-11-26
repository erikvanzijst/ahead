#!/usr/bin/env python

import sys
import time

from orochi.repo import Repo
from orochi.utils import aheadandbehind

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
    branches = set([b for b in r.branches() if b.name in sys.argv[3:]])
else:
    branches = set(r.branches()) - {main}

start = time.time()
stats = aheadandbehind(r, branches, main)
duration = time.time() - start

for b, counts in sorted(stats.items(), key=lambda _tup: _tup[0].lookup().date, reverse=True):
    print '%s [%d ahead] [%d behind] on %s' % (b.name, counts[0], counts[1], main.name)
print 'runtime: %.3f seconds' % duration
