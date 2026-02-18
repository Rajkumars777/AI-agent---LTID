"""
Test script for the autonomous agentic system.
Tests multi-step tasks, conditional logic, and cross-site comparisons.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from execution.agentic_orchestrator import orchestrator
from execution.task_memory import get_task_memory
from capabilities.browser_agent import browser_agent


async def test_basic_search():
    """Test Level 1: Basic navigation and search"""
    print("\n" + "="*80)
    print("TEST 1: Basic Search - Amazon iPhone 15")
    print("="*80)
    
    result = await orchestrator.execute_task(
        goal="Go to amazon.in and search for 'iPhone 15'",
        starting_url="https://www.amazon.in",
        task_id="test_basic_search"
    )
    
    print(f"\n✅ Success: {result.success}")
    print(f"\n📋 Summary:\n{result.summary}")
    print(f"\n📝 Logs:")
    for log in result.logs[-10:]:  # Last 10 logs
        print(f"  {log}")
    
    return result.success


async def test_filter_and_extract():
    """Test Level 3: Multi-step with filtering and extraction"""
    print("\n" + "="*80)
    print("TEST 2: Filter and Extract - Amazon iPhone under 50k")
    print("="*80)
    
    result = await orchestrator.execute_task(
        goal="Go to amazon.in, search for 'iPhone 15', filter price under 50000, and extract the price of the first product",
        starting_url="https://www.amazon.in",
        task_id="test_filter_extract"
    )
    
    print(f"\n✅ Success: {result.success}")
    print(f"\n📋 Summary:\n{result.summary}")
    print(f"\n📊 Extracted Data: {result.extracted}")
    
    return result.success


async def test_click_and_extract():
    """Test Level 3: Open product and extract details"""
    print("\n" + "="*80)
    print("TEST 3: Click and Extract - Open product page")
    print("="*80)
    
    result = await orchestrator.execute_task(
        goal="Go to amazon.in, search for 'iPhone 15', open the first product, and extract the price and rating",
        starting_url="https://www.amazon.in",
        task_id="test_click_extract"
    )
    
    print(f"\n✅ Success: {result.success}")
    print(f"\n📋 Summary:\n{result.summary}")
    print(f"\n📊 Extracted Data: {result.extracted}")
    
    return result.success


async def test_cross_site_comparison():
    """Test Bonus Level: Cross-site price comparison"""
    print("\n" + "="*80)
    print("TEST 4: Cross-Site Comparison - Amazon vs Flipkart")
    print("="*80)
    
    result = await orchestrator.execute_task(
        goal="Compare iPhone 15 price between Amazon.in and Flipkart.com",
        starting_url=None,  # Let it figure out the sites
        task_id="test_comparison"
    )
    
    print(f"\n✅ Success: {result.success}")
    print(f"\n📋 Summary:\n{result.summary}")
    print(f"\n📊 Extracted Data: {result.extracted}")
    
    memory = get_task_memory("test_comparison")
    comparison = memory.compare_data("price")
    print(f"\n💰 Price Comparison: {comparison}")
    
    return result.success


async def test_conditional_logic():
    """Test Level 6: Conditional execution"""
    print("\n" + "="*80)
    print("TEST 5: Conditional Logic - If price < 50000, open product")
    print("="*80)
    
    result = await orchestrator.execute_task(
        goal="Go to amazon.in, search for 'iPhone 15', if price is below 50000, open the product page and extract full details",
        starting_url="https://www.amazon.in",
        task_id="test_conditional"
    )
    
    print(f"\n✅ Success: {result.success}")
    print(f"\n📋 Summary:\n{result.summary}")
    print(f"\n📊 Extracted Data: {result.extracted}")
    
    return result.success


async def run_all_tests():
    """Run all tests sequentially"""
    print("\n🚀 STARTING AGENTIC SYSTEM TESTS")
    print("="*80)
    
    # Start browser once
    browser_agent.start()
    
    results = {}
    
    try:
        # Level 1: Basic
        results["basic_search"] = await test_basic_search()
        await asyncio.sleep(2)
        
        # Level 3: Multi-step
        results["filter_extract"] = await test_filter_and_extract()
        await asyncio.sleep(2)
        
        results["click_extract"] = await test_click_and_extract()
        await asyncio.sleep(2)
        
        # Bonus: Cross-site
        results["comparison"] = await test_cross_site_comparison()
        await asyncio.sleep(2)
        
        # Level 6: Conditional
        results["conditional"] = await test_conditional_logic()
        
    finally:
        browser_agent.stop()
    
    # Summary
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n✅ Passed: {passed}/{total}")
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    print("\n" + "="*80)
    print(f"{'🎉 ALL TESTS PASSED!' if passed == total else '⚠️  SOME TESTS FAILED'}")
    print("="*80)


if __name__ == "__main__":
    # Run tests
    asyncio.run(run_all_tests())
