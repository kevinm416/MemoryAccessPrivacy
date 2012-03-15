#!/usr/bin/env python
from cachem import *
import sys
from cStringIO import StringIO
import unittest

def pad(iterable, length, padding=''):
    for count, i in enumerate(iterable):
        yield i
    while count < length - 1:
        count += 1
        yield padding

### Nehalem Specs
# block size 64 bytes = 0X40
# L1 32 KB Instruction Cache -> 512 entries              O:6
#    32 KB Data Cache        -> 512 entries              O:6
# L2 256 KB Unified Cache    -> 4096 entries   T:19 I:7  O:6
# L3 8192 KB Unified Cache   -> 131072 entries T:14 I:12 O:6

def sequentialAccess(inst, start, count, inc, seq):
    return [inst + ' 0X%08X,%s' % (X*inc + start, seq) for X in xrange(0, count)]

def sequentialMemory(inst, start, count, inc):
    return [inst + ' 0X%08X' % (X*inc + start) for X in xrange(0, count)]

class TestSmallCache(unittest.TestCase):

    def runPattern(self, pattern, cache):
        old_stdout = sys.stdout

        sys.stdout = mystdout = StringIO()
        cache.clear()
        refs = map(parse_reference, pattern)
        for ref in refs:
            cache.access(ref)
        mystdout.flush()

        result = mystdout.getvalue().strip().upper()
        return result

    def runCases(self, cases, cache):
        for (pattern, soln) in cases:
            result = self.runPattern(pattern, cache)
            #sys.stderr.write("result: %s\n" % result)
            soln_formatted = '\n'.join(soln).upper()

            if not (result == soln_formatted):
                resList = result.split('\n')
                length = max(len(soln), len(resList))
                for (r, s) in zip(pad(soln, length), pad(resList, length)):
                    sys.stderr.write(str((r,s)))
                    if not r == s:
                        sys.stderr.write(' <----------------')
                    sys.stderr.write('\n')

            self.assertEquals(result, soln_formatted)

    def test_alignment(self):
        cache = NWayCache(5, 20, 4, 8, LRUPolicy())
        cache.set_parent(RAM())

        cases = [
            (sequentialAccess('L', 0X00000000, 1, 0X101, ''), sequentialMemory('R', 0X00000000, 1, 0X100)),
            (sequentialAccess('L', 0X00000000, 5, 0X101, ''), sequentialMemory('R', 0X00000000, 5, 0X100)),
        ]
        self.runCases(cases, cache)

    def test_associativity(self):
        cache = NWayCache(5, 20, 4, 8, LRUPolicy())
        cache.set_parent(RAM())

        cases = [
            (sequentialAccess('L', 0X00000000, 5, 0X100, ''), sequentialMemory('R', 0X00000000, 5, 0X100)),
            (sequentialAccess('L', 0X00000000, 5, 0X100, '')*3, sequentialMemory('R', 0X00000000, 5, 0X100)),
            (sequentialAccess('L', 0X00000000, 5, 0X100, '')*3 + ['L 0XF0000000,1'], 
                sequentialMemory('R', 0X00000000, 5, 0X100) + ['R 0XF0000000'])
        ]
        self.runCases(cases, cache)
    
    def test_full(self):
        cache = NWayCache(5, 20, 4, 8, LRUPolicy())
        cache.set_parent(RAM())

        totalCacheBlocks = (2**4)*5

        cases = [
            (sequentialAccess('L', 0X00000000, totalCacheBlocks, 0X100, ''), 
                sequentialMemory('R', 0X00000000, totalCacheBlocks, 0X100)),
            (sequentialAccess('L', 0X00000000, totalCacheBlocks, 0X100, '')*3, 
                sequentialMemory('R', 0X00000000, totalCacheBlocks, 0X100)),
            (sequentialAccess('L', 0X00000000, totalCacheBlocks, 0X100, '')*3 + ['L 0XF0000000,1'], 
                sequentialMemory('R', 0X00000000, totalCacheBlocks, 0X100) + ['R 0XF0000000'])
        ]
        self.runCases(cases, cache)

if __name__ == '__main__':
    unittest.main()
