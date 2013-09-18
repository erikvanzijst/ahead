#!/usr/bin/env python
#
# This module implements a more efficient ahead/behind algorithm than the one
# from ahead.py. On the Bitbucket repo it's about 4x faster:
#
#  (ahead)20:26 ~/work/ahead (master)$ python ahead.py  ../bitbucket/bitbucket/
#  [..]
#  runtime: 0.187 seconds
#
#  (ahead)21:03 ~/work/ahead (master)$ cat fixtures/bb.txt | python ahead2.py
#  [..]
#  runtime: 0.045 seconds
from collections import namedtuple

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

base = None
includes = set()
while True:
    line = f.readline().rstrip()
    if line.startswith('#'):
        continue
    if not line:
        break
    if base is None:
        base = line
    else:
        includes.add(line)

class Ref(object):
    def __init__(self, name, nodes):
        self.name = name
        self.nodes = nodes
        self.based = set()
        self.ahead, self.behind = 0, 0

base = Ref(base, {base})
refs = {Ref(head, {head}) for head in includes}
dead = []
count = 0

start = time.time()
for sha, parents in walk(f, set(list(includes) + [base.name])):
    count += 1
    if not refs:
        break

    on_main = sha in base.nodes
    if on_main:
        base.nodes.remove(sha)
        base.nodes.update(parents)

    for ref in refs:
        if sha in ref.nodes:
            ref.nodes.remove(sha)
            if on_main:
                ref.based.update(parents)
            else:
                ref.ahead += 1
                ref.nodes.update(parents)
            if not ref.nodes and not base.nodes.difference(ref.based):
                dead.append(ref)
        elif sha in ref.based:
            ref.based.remove(sha)
            ref.based.update(parents)
            if not base.nodes.difference(ref.based):
                dead.append(ref)
        elif on_main:
            ref.behind += 1

    while dead:
        ref = dead.pop()
        refs.remove(ref)
        print '%s: %d ahead / %s behind' % (ref.name, ref.ahead,
                                            ref.behind)
duration = time.time() - start

# print refs, count
print 'runtime: %.3f seconds' % duration
