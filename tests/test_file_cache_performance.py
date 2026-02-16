"""
Performance Benchmark Test for File Search Cache
Tests the A1 hybrid search strategy and measures performance improvements.
"""

import sys
import os
import time
sys.path.append(os.path.join(os.getcwd(), "backend"))

from capabilities.desktop import find_file_paths, clear_file_cache, refresh_file_cache
from capabilities.file_search_cache import FileSearchIndex

print("="*80)
print("FILE SEARCH CACHE - PERFORMANCE BENCHMARK")
print("="*80)

# Test file - you can change this to any file that exists on your system
TEST_FILE = "sample.xlsx"

print(f"\n🎯 Testing with: '{TEST_FILE}'")
print("-"*80)

# ===================================================================
# TEST 1: First Run (Cold Cache - Building Index)
# ===================================================================
print("\n📊 TEST 1: First Run (Cold Cache)")
print("Expected: 3-5 seconds (building index)")
print("-"*80)

# Clear cache to simulate first run
clear_file_cache()

start_time = time.time()
results_cold = find_file_paths(TEST_FILE)
cold_time = time.time() - start_time

print(f"\n⏱️  Time: {cold_time:.2f} seconds")
print(f"📂 Found: {len(results_cold)} file(s)")
if results_cold:
    for path in results_cold[:3]:  # Show first 3
        print(f"   - {path}")

# ===================================================================
# TEST 2: Second Run (Warm Cache)
# ===================================================================
print("\n\n📊 TEST 2: Second Run (Warm Cache)")
print("Expected: <100ms (cache lookup)")
print("-"*80)

start_time = time.time()
results_warm = find_file_paths(TEST_FILE)
warm_time = time.time() - start_time

print(f"\n⏱️  Time: {warm_time*1000:.1f} milliseconds ({warm_time:.3f} seconds)")
print(f"📂 Found: {len(results_warm)} file(s)")

# ===================================================================
# TEST 3: Non-existent File (Smart Fallback)
# ===================================================================
print("\n\n📊 TEST 3: Non-existent File (Smart Fallback)")
print("Expected: ~500ms (checks Downloads/Desktop/Documents)")
print("-"*80)

start_time = time.time()
results_missing = find_file_paths("this_file_definitely_does_not_exist_12345.xyz")
fallback_time = time.time() - start_time

print(f"\n⏱️  Time: {fallback_time*1000:.1f} milliseconds ({fallback_time:.3f} seconds)")
print(f"📂 Found: {len(results_missing)} file(s)")

# ===================================================================
# TEST 4: Fuzzy Match Performance
# ===================================================================
print("\n\n📊 TEST 4: Fuzzy Match (Partial Name)")
print("Expected: <200ms (fuzzy search in cache)")
print("-"*80)

# Extract just the filename without extension for fuzzy test
test_base = os.path.splitext(TEST_FILE)[0] if '.' in TEST_FILE else TEST_FILE[:4]

start_time = time.time()
results_fuzzy = find_file_paths(test_base)
fuzzy_time = time.time() - start_time

print(f"\n⏱️  Time: {fuzzy_time*1000:.1f} milliseconds ({fuzzy_time:.3f} seconds)")
print(f"📂 Found: {len(results_fuzzy)} file(s)")
if results_fuzzy:
    for path in results_fuzzy[:3]:
        print(f"   - {os.path.basename(path)}")

# ===================================================================
# PERFORMANCE SUMMARY
# ===================================================================
print("\n\n" + "="*80)
print("PERFORMANCE SUMMARY")
print("="*80)

# Calculate speedup
speedup = cold_time / warm_time if warm_time > 0 else 0

print(f"\n📈 Performance Metrics:")
print(f"   Cold Cache (First Run):     {cold_time:.2f}s")
print(f"   Warm Cache (Cached Lookup): {warm_time*1000:.1f}ms")
print(f"   Smart Fallback (Miss):      {fallback_time*1000:.1f}ms")
print(f"   Fuzzy Match:                {fuzzy_time*1000:.1f}ms")
print(f"\n⚡ Speedup: {speedup:.1f}x faster with cache")

# Pass/Fail Criteria
print(f"\n🎯 A1 Performance Targets:")
print(f"   ✓ Warm cache < 100ms:     {'✅ PASS' if warm_time < 0.1 else '❌ FAIL'} ({warm_time*1000:.1f}ms)")
print(f"   ✓ Smart fallback < 1s:    {'✅ PASS' if fallback_time < 1.0 else '❌ FAIL'} ({fallback_time*1000:.1f}ms)")
print(f"   ✓ Fuzzy match < 200ms:    {'✅ PASS' if fuzzy_time < 0.2 else '❌ FAIL'} ({fuzzy_time*1000:.1f}ms)")
print(f"   ✓ Speedup > 20x:          {'✅ PASS' if speedup > 20 else '❌ FAIL'} ({speedup:.1f}x)")

# ===================================================================
# CACHE STATISTICS
# ===================================================================
print(f"\n\n" + "="*80)
print("CACHE STATISTICS")
print("="*80)

cache = FileSearchIndex()
cache.load_from_disk()
stats = cache.get_stats()

print(f"\n📊 Index Stats:")
print(f"   Total Files:       {stats['total_files']:,}")
print(f"   Unique Filenames:  {stats['unique_filenames']:,}")
print(f"   Last Updated:      {stats['last_updated']}")
print(f"   Cache Age:         {stats['age_hours']:.1f} hours")
print(f"   Cache File:        {stats['cache_file']}")

print("\n" + "="*80)
if all([warm_time < 0.1, fallback_time < 1.0, fuzzy_time < 0.2, speedup > 20]):
    print("✅ ALL TESTS PASSED - A1 Performance Achieved!")
else:
    print("⚠️  Some targets not met - Review results above")
print("="*80)
