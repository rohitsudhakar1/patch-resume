#!/usr/bin/env python3
"""
Test script to verify deletion functionality works for all scenarios
"""
import json
import requests
import time

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_SCENARIOS = [
    {
        "name": "Delete first experience",
        "instruction": "delete the first experience",
        "expected_removal": "Ardent Capital"
    },
    {
        "name": "Delete second experience", 
        "instruction": "delete the second experience",
        "expected_removal": "Jubilant Capital"
    },
    {
        "name": "Delete third experience",
        "instruction": "delete the third experience", 
        "expected_removal": "Connected"
    },
    {
        "name": "Delete last experience",
        "instruction": "delete the last experience",
        "expected_removal": "Infinity Credit"
    },
    {
        "name": "Delete specific company",
        "instruction": "delete Ardent Capital experience",
        "expected_removal": "Ardent Capital"
    },
    {
        "name": "Delete specific company 2",
        "instruction": "delete Jubilant Capital experience", 
        "expected_removal": "Jubilant Capital"
    }
]

def test_deletion_scenario(scenario):
    """Test a single deletion scenario"""
    print(f"\n🧪 Testing: {scenario['name']}")
    print(f"📝 Instruction: {scenario['instruction']}")
    
    try:
        # Generate patch
        response = requests.post(f"{BASE_URL}/llm/patch", json={
            "instruction": scenario['instruction'],
            "project_id": "test-project"
        })
        
        if response.status_code != 200:
            print(f"❌ Failed to generate patch: {response.status_code}")
            return False
            
        patch_data = response.json()
        changes = patch_data.get('changes', [])
        
        print(f"📊 Generated {len(changes)} changes")
        
        # Analyze changes
        removals = [c for c in changes if c['type'] == 'removal']
        additions = [c for c in changes if c['type'] == 'addition']
        
        print(f"🗑️ Removals: {len(removals)}")
        print(f"➕ Additions: {len(additions)}")
        
        # Check if expected content is being removed
        found_expected = False
        for removal in removals:
            content = removal.get('content', '')
            if scenario['expected_removal'].lower() in content.lower():
                found_expected = True
                print(f"✅ Found expected removal: {content[:100]}...")
                break
        
        if not found_expected:
            print(f"❌ Expected removal '{scenario['expected_removal']}' not found in changes")
            print("📄 Actual removals:")
            for removal in removals:
                print(f"  - {removal.get('content', '')[:100]}...")
            return False
            
        # Check if it's a multi-line removal
        multi_line_removals = [r for r in removals if '\n' in r.get('content', '')]
        if multi_line_removals:
            print(f"✅ Multi-line removal detected: {len(multi_line_removals)} changes")
        else:
            print(f"⚠️ Only single-line removals detected - may not remove entire experience")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing scenario: {str(e)}")
        return False

def run_all_tests():
    """Run all deletion tests"""
    print("🚀 Starting deletion functionality tests...")
    
    # First, we need a project to test with
    print("\n📄 Setting up test project...")
    
    # For now, we'll assume a project exists
    # In a real test, we'd upload a resume first
    
    results = []
    for scenario in TEST_SCENARIOS:
        success = test_deletion_scenario(scenario)
        results.append({
            'scenario': scenario['name'],
            'success': success
        })
        time.sleep(1)  # Rate limiting
    
    # Summary
    print("\n📊 Test Results Summary:")
    print("=" * 50)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{status} {result['scenario']}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All deletion tests passed!")
    else:
        print("⚠️ Some tests failed - deletion functionality needs improvement")
    
    return results

if __name__ == "__main__":
    run_all_tests()
