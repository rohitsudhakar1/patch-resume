#!/usr/bin/env python3
"""
Comprehensive test for deletion functionality across all scenarios
"""
import json
import requests
import time
import re

# Test configuration
BASE_URL = "http://localhost:8000"

def test_patch_generation(instruction, expected_keywords):
    """Test patch generation for a specific instruction"""
    print(f"\n🧪 Testing: '{instruction}'")
    
    try:
        response = requests.post(f"{BASE_URL}/llm/patch", json={
            "instruction": instruction,
            "project_id": "test-project"
        })
        
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
        data = response.json()
        changes = data.get('changes', [])
        
        print(f"📊 Generated {len(changes)} changes")
        
        # Analyze changes
        removals = [c for c in changes if c.get('type') == 'removal']
        additions = [c for c in changes if c.get('type') == 'addition']
        
        print(f"🗑️ Removals: {len(removals)}")
        print(f"➕ Additions: {len(additions)}")
        
        # Check if any removal contains expected keywords
        found_keywords = []
        for removal in removals:
            content = removal.get('content', '')
            for keyword in expected_keywords:
                if keyword.lower() in content.lower():
                    found_keywords.append(keyword)
                    print(f"✅ Found keyword '{keyword}' in removal")
        
        if not found_keywords:
            print(f"❌ No expected keywords found in removals")
            print("📄 Actual removals:")
            for i, removal in enumerate(removals):
                print(f"  {i+1}. {removal.get('content', '')[:100]}...")
            return False
        
        # Check if it's multi-line
        multi_line_removals = [r for r in removals if '\n' in r.get('content', '')]
        if multi_line_removals:
            print(f"✅ Multi-line removal detected: {len(multi_line_removals)} changes")
            for removal in multi_line_removals:
                lines = removal.get('content', '').split('\n')
                print(f"   📏 Multi-line content: {len(lines)} lines")
        else:
            print(f"⚠️ Only single-line removals detected")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def run_comprehensive_tests():
    """Run comprehensive deletion tests"""
    print("🚀 Starting comprehensive deletion tests...")
    
    test_cases = [
        {
            "instruction": "delete the first experience",
            "expected_keywords": ["Ardent Capital", "AI Intern"],
            "description": "Delete first experience entry"
        },
        {
            "instruction": "delete the second experience", 
            "expected_keywords": ["Jubilant Capital", "Software Engineering"],
            "description": "Delete second experience entry"
        },
        {
            "instruction": "delete the third experience",
            "expected_keywords": ["Connected", "Transportation", "Lab"],
            "description": "Delete third experience entry"
        },
        {
            "instruction": "delete the last experience",
            "expected_keywords": ["Infinity Credit", "Solutions"],
            "description": "Delete last experience entry"
        },
        {
            "instruction": "delete Ardent Capital experience",
            "expected_keywords": ["Ardent Capital", "AI Intern"],
            "description": "Delete specific company by name"
        },
        {
            "instruction": "delete Jubilant Capital experience",
            "expected_keywords": ["Jubilant Capital", "Software Engineering"],
            "description": "Delete specific company by name"
        },
        {
            "instruction": "remove the first project",
            "expected_keywords": ["Blackjack", "FreeRTOS"],
            "description": "Delete first project"
        },
        {
            "instruction": "remove the second project",
            "expected_keywords": ["Client Database", "Management"],
            "description": "Delete second project"
        },
        {
            "instruction": "delete the education section",
            "expected_keywords": ["University", "Wisconsin", "Madison"],
            "description": "Delete education section"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(test_cases)}: {test_case['description']}")
        print(f"{'='*60}")
        
        success = test_patch_generation(
            test_case['instruction'], 
            test_case['expected_keywords']
        )
        
        results.append({
            'test': test_case['description'],
            'instruction': test_case['instruction'],
            'success': success
        })
        
        time.sleep(1)  # Rate limiting
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 COMPREHENSIVE TEST RESULTS")
    print(f"{'='*60}")
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{status} {result['test']}")
        if not result['success']:
            print(f"     Instruction: '{result['instruction']}'")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Deletion functionality is working correctly.")
    elif passed >= total * 0.8:
        print("⚠️ Most tests passed, but some issues remain.")
    else:
        print("❌ Many tests failed. Deletion functionality needs significant improvement.")
    
    return results

if __name__ == "__main__":
    run_comprehensive_tests()
