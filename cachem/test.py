from cachem import *
import sys
from cStringIO import StringIO

### Nehalem Specs
# block size 64 bytes = 0x40
# L1 32 KB Instruction Cache -> 512 entries              O:6
#    32 KB Data Cache        -> 512 entries              O:6
# L2 256 KB Unified Cache    -> 4096 entries   T:19 I:7  O:6
# L3 8192 KB Unified Cache   -> 131072 entries T:14 I:12 O:6

def sequentialAccess(inst, start, count, inc, seq):
    return [inst + ' 0x%08x,%s' % (x*inc + start, seq) for x in xrange(0, count)]

def sequentialMemory(inst, start, count, inc):
    return [inst + ' 0x%08x' % (x*inc + start) for x in xrange(0, count)]

l3Tests = [
    ### Alignment
    (sequentialAccess('L', 0x00000000, 16, 0x41, ''), sequentialMemory('R', 0x00000000, 16, 0x40)),

    ### L3 Size
    # Replace L3 by sequential scan. Need to look at 131072*64=8388608=0x800000 bytes to fill up L3
    (['L 0x00000000,8388608'], ['0x00000000']),
    (['L 0x00000000,8388609'], ['0x00000000', '0x00800000']),
    
    ### L3 16 way associativity
    # Filling up one associative set should only result in 16 memory accesses
    (sequentialAccess('L', 0x00000000, 16, 0x20000, 64), sequentialMemory('R', 0x00000000, 16, 0x20000)),
    # Accessing things in the set multiple times should not result in extra memory accesses
    (sequentialAccess('L', 0x00000000, 16, 0x20000, 64)*2, sequentialMemory('R', 0x00000000, 16, 0x20000)),
    # Accessing a sequence of 17 blocks that all map to different rows in the cache
    # should have to go to disk every time
    (sequentialAccess('L', 0x00000000, 17, 0x20000, 64)*5, sequentialMemory('R', 0x00000000, 17, 0x20000)*5)
    ]

c1 = NWayCache(5, 20, 4, 8, LRUPolicy())
c1.set_parent(RAM())

c1Tests = [
    ### Alignment
    (sequentialAccess('L', 0x00000000, 1, 0x101, ''), sequentialMemory('R', 0x00000000, 1, 0x100)),
    (sequentialAccess('L', 0x00000000, 5, 0x101, ''), sequentialMemory('R', 0x00000000, 5, 0x100)),

    ### Fill up the cache
    (sequentialAccess('L', 0x00000000, (2**4)*5, 0x100, ''), sequentialMemory('R', 0x00000000, (2**4)*5, 0x100)),
    (sequentialAccess('L', 0x00000000, (2**4)*5, 0x100, '')*3, sequentialMemory('R', 0x00000000, (2**4)*5, 0x100)),
    (sequentialAccess('L', 0x00000000, (2**4)*5, 0x100, '')*3 + ['L 0xF0000000,1'], 
        sequentialMemory('R', 0x00000000, (2**4)*5, 0x100) + ['R 0xF0000000'])
]

if __name__ == '__main__':
    old_stdout = sys.stdout

    cache = NehalemCache()
    for (pattern, soln) in c1Tests:
        sys.stdout = mystdout = StringIO()

        refs = map(parse_reference, pattern)
        for ref in refs:
            c1.access(ref)

        mystdout.flush()

        if not mystdout.getvalue().strip() == '\n'.join(soln):
            raise Exception("'" + str(pattern) + "' generated: '" + mystdout.getvalue() + \
                            "' does not equal: '" + '\n'.join(soln) + "'")
    
    sys.stdout = old_stdout