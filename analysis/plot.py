#!/usr/bin/env python
import sys
import Image
from collections import defaultdict
access_mapping = {"ir": "INST_READ",
                  "dr": "DATA_READ",
                  "dw": "DATA_WRITE"}

BLOCK_BITS = 6
PAGE_BITS  = 12

BLOCK_SIZE = 2**BLOCK_BITS
PAGE_SIZE  = 2**PAGE_BITS

def get_block(addr):
    return (addr >> BLOCK_BITS) << BLOCK_BITS

def get_page(addr):
    return (addr >> PAGE_BITS) << PAGE_BITS

def memory_access_blocks(it):
    for i,line in enumerate(it):
        if line.startswith('==') or line.startswith('--'):
            continue
        try:
            access_type, addr_str = [x.strip().lower() for x in line.strip().split(":")]
        except ValueError:
            sys.stderr.write("Error parsing line %d\n" % (i+1))
            continue

        if access_type not in access_mapping:
            sys.stderr.write("Unknown memory access type '%s' on line %d\n" % (access_type, i+1))
            continue
        try:
            address = int(addr_str, 16)
        except ValueError:
            sys.stderr.write("Unable to parse memory address '%s' on line %d\n" % (addr_str, i+1))
            continue

        yield (access_mapping[access_type], get_block(address))

def find_segments(it):
    accessed = set(addr for (access_type, addr) in it)
    x = list(accessed)
    x.sort()

    if not x:
        return []


    segments = []
    prev = get_block(x[0])
    segment_start = prev
    thresh = 2**20
    for addr in x:
        addr = get_block(addr)
        if (addr - prev) > thresh:
            segments.append((segment_start, prev, prev - segment_start))
            segment_start = addr
        prev = addr

    segments.append((segment_start, addr, addr - segment_start))

    return segments

def find_pages(it):
    return 

def find_boundaries(it):
    accessed = set(addr for (access_type, addr) in it)
    x = list(accessed)
    x.sort()

    if not x:
        raise ValueError
    prev = (x[0] >> 6) << 6
    gap_width = 0
    gap_pair = None
    for addr in x:
        addr = (addr >> 6) << 6
        if (addr - prev) > gap_width:
            gap_width = addr - prev
            gap_pair = (prev, addr)
        elif 2e6 <= (addr - prev) < 10e6:
            print "%08x-%08x looks like a segment" % (addr, prev)
        prev = addr
    
    heap_low = min(x)
    heap_high, stack_low = gap_pair
    stack_high = max(x)

    return (heap_low, heap_high, heap_high-heap_low), (stack_low, stack_high, stack_high-stack_low)

def mark_region_accesses(it):
    regions = defaultdict(int)
    for (access_type, addr) in it:
        page = get_page(addr)
        regions[(page, access_type)] += 1
    return regions

def human_friendly(b):
    GB, b = divmod(b, 2**30)
    MB, b = divmod(b, 2**20)
    KB, b = divmod(b, 2**10)
    if GB:
        return "%.2fGiB" % (GB + (MB + KB/1024.0)/1024.0)
    if MB:
        return "%.2fMiB" % (MB + KB/1024.0)
    else:
        return "%.2fKiB" % (KB + b/1024.0)

def chunk_process(iterable, chunk_size):
    it = iter(iterable)
    while True:
        i = 0
        chunk = []
        while i < chunk_size:
            try:
                chunk.append(it.next())
            except StopIteration:
                yield chunk
                raise StopIteration
            i += 1
        else:
            yield chunk

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print "Usage: ./plot.py timestep output_filename < trace_file"
        sys.exit(1)

    chunk_size = int(sys.argv[1])
    output_filename = sys.argv[2]


    block_accesses = list(memory_access_blocks(sys.stdin))
    #pages = mark_region_accesses(block_accesses)

    #x = pages.items()
    #x.sort(key=lambda (key, value): key)
    
    #print len(x)

    pages = mark_region_accesses(block_accesses)
    unique_pages = sorted(list(set(addr for (addr, access_type) in pages)))


    row_count = 0
    row_map = {}

    prev = unique_pages[-1]
    for page in reversed(unique_pages):
        row_map[page] = row_count
        if (prev - page) >> 12 > 256:
            #print hex(prev), hex(page), (page - prev) >> 12
            row_count += 10
        row_count += 1
        prev = page


    num_chunks = len(block_accesses)/chunk_size + 1

    im = Image.new("RGB", (num_chunks, row_count), "white")
    for i,accesses in enumerate(chunk_process(block_accesses, chunk_size)):
        accessed_pages = mark_region_accesses(accesses)
        for page in unique_pages:
            dr = accessed_pages[(page, "DATA_READ")]
            dw = accessed_pages[(page, "DATA_WRITE")]
            ir = accessed_pages[(page, "INST_READ")]
            total = dr + dw + ir
            if total:
                im.putpixel((i, row_map[page]), (255.0*dr/total, 255.0*dw/total, 255.0*ir/total))
    im.save(output_filename)

    #Red is data reads, Green is data writes, Blue is Instruction reads

    #for (key, value) in reversed(x):
    #    print "%09x : %s" % (key, value)
    
    #heap, stack = find_boundaries(memory_access_blocks(sys.stdin))
    #print "heap: %08x-%08x (%d)" % heap
    #print "stack:%08x-%08x (%d)" % stack
    
    #print "Segments"
    #total = 0
    #for seg in find_segments(memory_access_blocks(sys.stdin)):
    #    total += seg[2]
    #    print "%09x-%09x (%s)" % (seg[0], seg[1], human_friendly(seg[2]))
    #print "Total memory usage: %s" % human_friendly(total)
