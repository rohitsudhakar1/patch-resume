#!/usr/bin/env python3
"""
Simple test runner for deletion functionality
Run this to verify all deletion scenarios work correctly
"""
import subprocess
import sys
import time

def run_test():
    """Run the comprehensive deletion tests"""
    print("🚀 Starting deletion functionality verification...")
    print("This will test all deletion scenarios to ensure they work correctly.")
    print()
    
    try:
        # Run the comprehensive test
        result = subprocess.run([
            sys.executable, "test_comprehensive_deletions.py"
        ], capture_output=True, text=True)
        
        print("📊 Test Output:")
        print("=" * 60)
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Errors/Warnings:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ All tests completed successfully!")
        else:
            print(f"❌ Tests failed with return code: {result.returncode}")
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running tests: {str(e)}")
        return False

def main():
    """Main function"""
    print("🧪 Deletion Functionality Test Suite")
    print("=" * 50)
    print()
    print("This test suite will verify that deletion works for:")
    print("• First experience entry")
    print("• Second experience entry") 
    print("• Last experience entry")
    print("• Specific company by name")
    print("• First project")
    print("• Second project")
    print("• Education section")
    print()
    print("Make sure your backend server is running on http://localhost:8000")
    print()
    
    input("Press Enter to start testing...")
    
    success = run_test()
    
    if success:
        print("\n🎉 SUCCESS: All deletion scenarios are working correctly!")
        print("You can now confidently use any deletion instruction.")
    else:
        print("\n⚠️ ISSUES DETECTED: Some deletion scenarios may not work properly.")
        print("Check the test output above for details.")
    
    return success

if __name__ == "__main__":
    main()
