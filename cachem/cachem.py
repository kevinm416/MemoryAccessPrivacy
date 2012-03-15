#!/usr/bin/env python
import collections
import sys



def parse_reference(line):
    """
    Takes in a memory reference line from lackey and splits it into a tuple.
    >>> parse_reference(" L 0421dbe0,8")
    ('L', 69327840, 8)
    """
    line = line.lstrip(" ")
    ref_type = line[0]
    ref_addr, ref_length = line[1:].lstrip().split(",", 2)
    # If there is no number assume 1
    if ref_length:
        ref_int = int(ref_length, 10)
    else:
        ref_int = 1
    return (ref_type, int(ref_addr, 16), ref_int)

def generate_accesses(reference, offset_bits=6, make_repeats=False):
    """
    Takes in a memory reference and generates a list of cache block accesses.

    offset_bits specifies the number of offset bits needed to address
    a byte within a cache block
 
    If make_repeats is true, multiple cache block accesses are made for
    sequential accesses to bytes within the same block to facilitate LRU
    approximation algorithms that depend on access counts
    >>> generate_accesses(('L', 69327840, 8))
    [('R', 69327840)]
    """

    ref_type, ref_addr, ref_length = reference
    if ref_type == "I":
        access_type = "I"
    elif ref_type == "S" or ref_type == "M":
        access_type = "W"
    else:
        access_type = "R"
    
    offset_mask = 0
    for i in xrange(offset_bits):
        offset_mask |= 1 << i
 
    accesses = []
    access_addr = ref_addr
    
    while access_addr < ref_addr + ref_length:
        accesses.append((access_type, access_addr))
        if not make_repeats:
            access_addr |= offset_mask
        access_addr += 1

    return accesses

class NWayCache(object):
    def __init__(self, assoc, tag_bits, index_bits, offset_bits, policy):
        self.index_bits = index_bits
        self.offset_bits = offset_bits
        self.tag_bits = tag_bits 
        self.policy = policy
        self.associativity = assoc

        self.tag_mask = 0
        for i in xrange(tag_bits):
            self.tag_mask |= 1 << i
        self.tag_mask <<= (offset_bits + index_bits)

        self.index_mask = 0
        for i in xrange(index_bits):
            self.index_mask |= 1 << i
        self.index_mask <<= offset_bits

        self.id_mask = self.tag_mask | self.index_mask

        self.sets = collections.defaultdict(set)
        self.dirty = set()

        self.parent = None

    def set_parent(self, parent):
        """
        Set the parent lower level of memory hierarchy that the cache accesses
        when it has a miss or writes a block back.
        """
        self.parent = parent

    def lookup_block(self, address):
        """
        Finds the set that the address indexes into and returns it and whether
        the block corresponding to the address is in the cache
        """
        
        tag = address & self.tag_mask
        index = address & self.index_mask
        cache_set = self.sets[index]
        return (cache_set, tag in cache_set)

    def write(self, address):
        """
        Simulate writing data to a block with the given address and flag it as
        dirty. Since we have a write-allocate policy, if the block isn't in the
        cache, we first read it in and then write to it.
        """
        
        cache_set, present = self.lookup_block(address)
        if not present:
            self.read(address)

        block_id = address & self.id_mask

        self.policy.touch(block_id)
        self.dirty.add(block_id)

    def write_back(self, block_id):
        """
        Simulate writing a block back to a lower level on the memory hierarchy.
        """

        self.parent.write(block_id)

    def read(self, address):
        """
        Simulate reading data from a block with the given address, possibly
        reading it in from another cache level and evicting a block from this
        cache to make room for it.
        """
        index = address & self.index_mask
        block_id = address & self.id_mask
        #sys.stderr.write("----------")
        #sys.stderr.write("%08x,addr" % address)
        #sys.stderr.write("%08x,index" % index)
        #sys.stderr.write("%08x,tag" % (address & self.tag_mask))
        #sys.stderr.write("%08x,block2" % ((address & self.tag_mask) | index))
        ##sys.stderr.write("%08x,block" % block_id)
        cache_set, present = self.lookup_block(address)
        #sys.stderr.write("----------")
        if not present:
            #Should the read happen before any write-backs, or after?
            self.parent.read(block_id)
            if len(cache_set) == self.associativity:
                evicted = self.policy.evict(cache_set)
                cache_set.remove(evicted)
                if evicted in self.dirty:
                    self.dirty.remove(evicted)
                    self.write_back(evicted)
            cache_set.add(block_id)
        self.policy.touch(block_id)
    
    def access(self, ref):
        for (op, addr) in generate_accesses(ref, self.offset_bits, False):
            #sys.stderr.write("%s %08x\n" % (op, addr))
            if op == "I":
                self.read(addr)
            elif op == "R":
                self.read(addr)
            elif op == "W":
                self.write(addr)
            else:
                raise Exception("Invalid operation: %s" % op)

class RAM(object):
    def read(self, address):
        sys.stdout.write("R 0x%08x\n" % address)

    def write(self, address):
        sys.stdout.write("W 0x%08x\n" % address)

class LRUPolicy(object):
    def __init__(self):
        self.access_list = []

    def touch(self, item):
        if item in self.access_list:
            index = self.access_list.index(item)
            self.access_list.append(self.access_list.pop(index))
        else:
            self.access_list.append(item)

    def evict(self, choices):
        for item in self.access_list:
            if item in choices:
                self.access_list.remove(item)
                return item
        else:
            return list(choices)[0]

#class ClockPolicy(object):
#    def __init__(self, n):
#        self.n = n
#        self.

class NehalemCache(object):
    """ Nehalem Specs
    block size 64 bytes = 0x40
    L1 32 KB Instruction Cache -> 512 entries              O:6
       32 KB Data Cache        -> 512 entries              O:6
    L2 256 KB Unified Cache    -> 4096 entries   T:19 I:7  O:6
    L3 8192 KB Unified Cache   -> 131072 entries T:14 I:12 O:6 
    """
    def __init__(self):
        self.total_bits = 32
        self.offset_bits = 6
        self.L1I_cache = NWayCache(4, self.total_bits - 7 - self.offset_bits, 7, self.offset_bits,
                              LRUPolicy())
        self.L1D_cache = NWayCache(8, self.total_bits - 6 - self.offset_bits, 6, self.offset_bits,
                              LRUPolicy())

        self.L2_cache = NWayCache(8, self.total_bits - 12 - self.offset_bits, 12, self.offset_bits,
                             LRUPolicy())

        #The replacement policy for L3 is not disclosed in the textbook...
        self.L3_cache = NWayCache(16, self.total_bits - 17 - self.offset_bits, 17, self.offset_bits,
                             LRUPolicy())

        self.ram = RAM()
        
        self.L1I_cache.set_parent(self.L2_cache)
        self.L1D_cache.set_parent(self.L2_cache)
        self.L2_cache.set_parent(self.L3_cache)
        self.L3_cache.set_parent(self.ram)
    
    def access(self, ref):
        for (op, addr) in generate_accesses(ref, self.offset_bits, False):
            #sys.stderr.write("%s %08x\n" % (op, addr))
            if op == "I":
                self.L1I_cache.read(addr)
            elif op == "R":
                self.L1D_cache.read(addr)
            elif op == "W":
                self.L1D_cache.write(addr)
            else:
                raise Exception("Invalid operation: %s" % op)

if __name__ == "__main__":
    total_bits = 32
    offset_bits = 6

    L1I_cache = NWayCache(4, total_bits - 7 - offset_bits, 7, offset_bits,
                          LRUPolicy())
    L1D_cache = NWayCache(8, total_bits - 6 - offset_bits, 6, offset_bits,
                          LRUPolicy())

    L2_cache = NWayCache(8, total_bits - 12 - offset_bits, 12, offset_bits,
                         LRUPolicy())

    #The replacement policy for L3 is not disclosed in the textbook...
    L3_cache = NWayCache(16, total_bits - 17 - offset_bits, 17, offset_bits,
                         LRUPolicy())

    ram = RAM()
    
    
    L1I_cache.set_parent(L2_cache)
    L1D_cache.set_parent(L2_cache)
    L2_cache.set_parent(L3_cache)
    L3_cache.set_parent(ram)

    for line in sys.stdin:
        if line.startswith("=="):
            continue
        ref = parse_reference(line)
        for (op, addr) in generate_accesses(ref, offset_bits, False):
            #print op, "%08x" % addr
            if op == "I":
                L1I_cache.read(addr)
            elif op == "R":
                L1D_cache.read(addr)
            else:
                L1D_cache.write(addr)

