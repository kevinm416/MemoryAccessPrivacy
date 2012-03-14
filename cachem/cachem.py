#!/usr/bin/env python
import collections
import sys



def parse_reference(line):
    """
    Takes in a memory reference line from lackey and splits it into a tuple.
    >>> parse_reference(" L 0421dbe0,8")
    ('L', 69327840, 8)
    """
    ref_type, ref_addr, ref_length = line.lstrip(" ").split(",")
    return (ref_type, int(ref_addr, 16), int(ref_length, 10))

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
            self.tag_mask |= 1
        self.tag_mask << (offset_bits + index_bits)

        self.index_mask = 0
        for i in xrange(index_bits):
            self.index_mask |= 1 << i
        self.index_mask << offset_bits

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
        cache_set, present = self.lookup_block(address)
        if not present:
            if len(cache_set) == self.associativity:
                evicted = self.policy.evict(cache_set)
                cache_set.remove(evicted)
                if evicted in self.dirty:
                    self.dirty.remove(evicted)
                    self.write_back(evicted)
            cache_set.add(block_id)
        self.policy.touch(block_id)
