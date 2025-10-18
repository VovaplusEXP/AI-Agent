#!/usr/bin/env python3
"""
Test improved deduplication in memory systems.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory import VectorMemory
from muse_memory import StrategicMemory, ProceduralMemory, ToolMemory


def test_vector_memory_deduplication():
    """Test that VectorMemory properly handles duplicates with metadata."""
    print("Testing VectorMemory deduplication...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = VectorMemory(str(tmpdir), memory_type="test")
        
        # Add entry without metadata
        memory.add("Test entry 1")
        assert len(memory.storage) == 1
        
        # Try to add same entry - should be skipped
        memory.add("Test entry 1")
        assert len(memory.storage) == 1, "Duplicate should be skipped"
        
        # Add entry with metadata
        memory.add("Test entry 2", metadata={'source': 'test'})
        assert len(memory.storage) == 2
        
        # Try to add same entry with different metadata - should still be skipped
        memory.add("Test entry 2", metadata={'source': 'other'})
        assert len(memory.storage) == 2, "Duplicate with different metadata should be skipped"
        
        # Add different entry
        memory.add("Test entry 3")
        assert len(memory.storage) == 3
        
        print("✅ VectorMemory deduplication works correctly")


def test_strategic_memory_similarity():
    """Test that StrategicMemory detects similar lessons."""
    print("\nTesting StrategicMemory similarity detection...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_path = Path(tmpdir) / "strategic.json"
        strategic = StrategicMemory(str(memory_path))
        
        # Add first lesson
        strategic.add_lesson("Always check memory before using internet search")
        assert len(strategic.lessons) == 1
        
        # Try exact duplicate - should increment usage_count
        strategic.add_lesson("Always check memory before using internet search")
        assert len(strategic.lessons) == 1
        assert strategic.lessons[0]['usage_count'] == 2
        
        # Try very similar lesson (>80% word overlap) - should be detected
        strategic.add_lesson("Always check memory before internet search")
        assert len(strategic.lessons) == 1
        assert strategic.lessons[0]['usage_count'] == 3, "Similar lesson should be detected"
        
        # Try different lesson - should be added
        strategic.add_lesson("Use absolute paths for file operations")
        assert len(strategic.lessons) == 2
        
        # Try similar but not enough overlap (<80%) - should be added
        strategic.add_lesson("Check database before searching")
        assert len(strategic.lessons) == 3
        
        print("✅ StrategicMemory similarity detection works correctly")


def test_procedural_memory_similarity():
    """Test that ProceduralMemory detects similar SOPs."""
    print("\nTesting ProceduralMemory similarity detection...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_path = Path(tmpdir) / "procedural.json"
        procedural = ProceduralMemory(str(memory_path))
        
        # Add first SOP
        steps1 = ["internet_search()", "web_fetch()", "create_file()"]
        procedural.add_sop("Search and save information", steps1, True)
        assert len(procedural.sops) == 1
        
        # Try exact duplicate - should increment usage_count
        procedural.add_sop("Search and save information", steps1, True)
        assert len(procedural.sops) == 1
        assert procedural.sops[0]['usage_count'] == 2
        
        # Try similar task with same steps - should be detected
        steps2 = ["internet_search()", "web_fetch()", "create_file()"]
        procedural.add_sop("Search and save data", steps2, True)
        assert len(procedural.sops) == 1, "Similar SOP with same steps should be detected"
        assert procedural.sops[0]['usage_count'] == 3
        
        # Try different task - should be added
        steps3 = ["read_file()", "analyze_code()"]
        procedural.add_sop("Analyze code file", steps3, True)
        assert len(procedural.sops) == 2
        
        print("✅ ProceduralMemory similarity detection works correctly")


def test_tool_memory_similarity():
    """Test that ToolMemory detects similar hints."""
    print("\nTesting ToolMemory similarity detection...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_path = Path(tmpdir) / "tool_memory.json"
        tool_memory = ToolMemory(str(memory_path))
        
        # Add first hint
        tool_memory.add_hint("web_fetch", "Always use web_search_in_page after web_fetch")
        assert len(tool_memory.tool_hints['web_fetch']) == 1
        
        # Try exact duplicate - should increment usage_count
        tool_memory.add_hint("web_fetch", "Always use web_search_in_page after web_fetch")
        assert len(tool_memory.tool_hints['web_fetch']) == 1
        assert tool_memory.tool_hints['web_fetch'][0]['usage_count'] == 2
        
        # Try very similar hint (>75% word overlap) - should be detected
        tool_memory.add_hint("web_fetch", "Always use web_search_in_page after doing web_fetch")
        assert len(tool_memory.tool_hints['web_fetch']) == 1, "Similar hint should be detected"
        assert tool_memory.tool_hints['web_fetch'][0]['usage_count'] == 3
        
        # Try different hint - should be added
        tool_memory.add_hint("web_fetch", "Set timeout to 30 seconds")
        assert len(tool_memory.tool_hints['web_fetch']) == 2
        
        print("✅ ToolMemory similarity detection works correctly")


def main():
    """Run all deduplication tests."""
    print("=" * 60)
    print("Testing Improved Deduplication")
    print("=" * 60)
    
    try:
        test_vector_memory_deduplication()
        test_strategic_memory_similarity()
        test_procedural_memory_similarity()
        test_tool_memory_similarity()
        
        print("\n" + "=" * 60)
        print("✅ All deduplication tests passed!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
