#!/usr/bin/env python3
"""
Test script to verify duration functionality
"""
import os
import sys

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import format_duration_simple, validate_audio

def test_duration_functions():
    """Test duration-related functions"""
    try:
        # Test format_duration_simple function
        print("Testing format_duration_simple...")
        result = format_duration_simple(125.5)  # 2 minutes 5 seconds
        print(f"format_duration_simple(125.5) = {result}")
        assert result == "2:05", f"Expected '2:05', got '{result}'"
        
        result = format_duration_simple(65)  # 1 minute 5 seconds
        print(f"format_duration_simple(65) = {result}")
        assert result == "1:05", f"Expected '1:05', got '{result}'"
        
        result = format_duration_simple(30)  # 30 seconds
        print(f"format_duration_simple(30) = {result}")
        assert result == "0:30", f"Expected '0:30', got '{result}'"
        
        print("✅ format_duration_simple tests passed!")
        
        # Test with a small audio file if available
        test_files = ["test.wav", "speech.wav", "sample.mp3"]
        for test_file in test_files:
            if os.path.exists(test_file):
                print(f"Testing validate_audio with {test_file}...")
                is_valid, message, audio_data, duration = validate_audio(test_file)
                print(f"Result: valid={is_valid}, duration={duration}, message='{message}'")
                if is_valid:
                    print("✅ validate_audio test passed!")
                    break
        else:
            print("⚠️  No test audio files found, skipping validate_audio test")
        
        print("\n🎉 All available tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("=== Duration Function Test ===")
    test_duration_functions()