"""
Unit test for KisanSetu reasoning & Gnani voice integration
"""

import sys
import os

# Add backend to sys.path
sys.path.append(os.path.dirname(__file__))

from indic_reasoner import IndicReasoner
from gnani_client import GnaniClient

def test_pipeline():
    print("=== Testing Indic Agri Reasoner ===")
    reasoner = IndicReasoner()

    # Test 1: Mandi Price Query
    res1 = reasoner.process_query("नासिक मंडी में प्याज का क्या भाव है?", "hi-IN")
    print("\n[Test 1: Mandi Price Query]")
    print("Intent:", res1["intent"])
    print("Title:", res1["title"])
    print("Voice Text:", res1["voice_response"])
    assert res1["intent"] == "mandi"

    # Test 2: Crop Disease Query
    res2 = reasoner.process_query("टमाटर के पत्ते पीले पड़ रहे हैं और मुड़ रहे हैं", "hi-IN")
    print("\n[Test 2: Crop Disease Query]")
    print("Intent:", res2["intent"])
    print("Title:", res2["title"])
    print("Voice Text:", res2["voice_response"][:100] + "...")
    assert res2["intent"] == "crop_health"

    # Test 3: Scheme Query
    res3 = reasoner.process_query("पीएम किसान सम्मान निधि की अगली किस्त कब आएगी?", "hi-IN")
    print("\n[Test 3: Scheme Query]")
    print("Intent:", res3["intent"])
    print("Title:", res3["title"])
    print("Voice Text:", res3["voice_response"][:100] + "...")
    assert res3["intent"] == "scheme"

    # Test 4: Marathi Language Support
    res4 = reasoner.process_query("नाशिक मार्केटमध्ये कांद्याचा भाव काय आहे?", "mr-IN")
    print("\n[Test 4: Marathi Language Query]")
    print("Intent:", res4["intent"])
    print("Voice Text:", res4["voice_response"])
    assert res4["intent"] == "mandi"

    print("\n=== Testing Gnani Timbre TTS on Reasoner Output ===")
    gnani = GnaniClient()
    audio_bytes, latency_ms = gnani.synthesize_speech(
        text=res1["voice_response"],
        language="hi-IN",
        voice="Nalini"
    )
    print(f"TTS Audio Generated: {len(audio_bytes)} bytes in {latency_ms} ms!")
    assert len(audio_bytes) > 1000

    print("\nALL BACKEND REASONING & VOICE TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_pipeline()
