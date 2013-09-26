#!/usr/bin/env python
#
# Improves on bhead.py removing the inner loop over all the refs for every
# commit. About twice as fast as bhead.py on the confluence repo.
from collections import defaultdict

import sys
import time


def walk(f, includes):
    for line in f:
        if not includes:
            break
        bits = line.split()
        sha = bits[0]
        parents = bits[1:]

        try:
            includes.remove(sha)
            yield (sha, parents)
            includes.update(parents)
        except KeyError:
            pass

f = len(sys.argv) > 1 and open(sys.argv[1]) or sys.stdin

class Ref(object):
    def __init__(self, name):
        self.name = name
        self.ahead, self.behind = 0, 0

based = defaultdict(set)
live = defaultdict(set)
while True:
    line = f.readline().rstrip()
    if not line:
        break
    if line.startswith('#'):
        continue
    if not based:
        based[line] = set()
    else:
        live[line].add(Ref(line))

refs = set().union(*live.values())
refcount = len(refs)

start = time.time()
for sha, parents in walk(f, set().union(live.keys(), based.keys())):
    on_main = sha in based
    if on_main:
        basedrefs = based.pop(sha)
        for p in parents:
            based[p].update(basedrefs)

    if sha in live:
        liverefs = live.pop(sha)
        if on_main:
            basedrefs.update(liverefs)
            for p in parents:
                based[p].update(liverefs)
        else:
            for p in parents:
                live[p].update(liverefs)
            for ref in liverefs:
                ref.ahead += 1
    if on_main:
        for r in refs.difference(basedrefs):
            r.behind += 1
        if not live:
            for p, _refs in based.iteritems():
                if refcount != len(_refs):
                    break
            else:
                break

duration = time.time() - start
for ref in sorted(refs, key=lambda r: r.name):
    print '%s: %d ahead / %d behind' % (ref.name, ref.ahead, ref.behind)
print 'runtime: %.3f seconds' % duration
