from cachem import *
import sys
from cStringIO import StringIO
import unittest

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

l3Tests = [
    ### Alignment
    (sequentialAccess('L', 0X00000000, 16, 0X41, ''), sequentialMemory('R', 0X00000000, 16, 0X40)),

    ### L3 Size
    # Replace L3 by sequential scan. Need to look at 131072*64=8388608=0X800000 bytes to fill up L3
    (['L 0X00000000,8388608'], ['0X00000000']),
    (['L 0X00000000,8388609'], ['0X00000000', '0X00800000']),
    
    ### L3 16 way associativity
    # Filling up one associative set should only result in 16 memory accesses
    (sequentialAccess('L', 0X00000000, 16, 0X20000, 64), sequentialMemory('R', 0X00000000, 16, 0X20000)),
    # Accessing things in the set multiple times should not result in eXtra memory accesses
    (sequentialAccess('L', 0X00000000, 16, 0X20000, 64)*2, sequentialMemory('R', 0X00000000, 16, 0X20000)),
    # Accessing a sequence of 17 blocks that all map to different rows in the cache
    # should have to go to disk every time
    (sequentialAccess('L', 0X00000000, 17, 0X20000, 64)*5, sequentialMemory('R', 0X00000000, 17, 0X20000)*5)
    ]

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
                for (r, s) in zip(soln, result.split('\n')):
                    sys.stderr.write(str((r,s)))
                    if not r == s:
                        sys.stderr.write(' <----------------')
                    sys.stderr.write('\n')

            self.assertEquals(result, soln_formatted)
                # "'" + '\n'.join(pattern) + 
                # "' \ngenerated: \n'" + result + 
                # "' \ndoes not equal: \n'" + soln_formatted + 
                # "'\n\n\n")

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
