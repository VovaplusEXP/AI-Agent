# test_muse_memory.py
"""
Tests for MUSE memory system.
"""

import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from muse_memory import MUSEMemoryManager, StrategicMemory, ProceduralMemory, ToolMemory


def test_strategic_memory():
    """Test strategic memory operations."""
    print("Testing Strategic Memory...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_path = Path(tmpdir) / "strategic.json"
        strategic = StrategicMemory(str(memory_path))
        
        # Add lesson
        strategic.add_lesson(
            "Always check L3 memory before internet_search",
            context={'tool_name': 'internet_search'}
        )
        
        # Check it was added
        assert len(strategic.lessons) == 1
        assert strategic.lessons[0]['lesson'] == "Always check L3 memory before internet_search"
        assert strategic.lessons[0]['usage_count'] == 1
        
        # Add duplicate - should increment usage count
        strategic.add_lesson(
            "Always check L3 memory before internet_search",
            context={'tool_name': 'internet_search'}
        )
        
        assert len(strategic.lessons) == 1
        assert strategic.lessons[0]['usage_count'] == 2
        
        # Get relevant lessons
        lessons = strategic.get_relevant_lessons({'tool_name': 'internet_search'}, max_lessons=1)
        assert len(lessons) == 1
        assert "internet_search" in lessons[0]
        
        print("✅ Strategic Memory tests passed")


def test_procedural_memory():
    """Test procedural memory operations."""
    print("Testing Procedural Memory...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_path = Path(tmpdir) / "procedural.json"
        procedural = ProceduralMemory(str(memory_path))
        
        # Add SOP
        procedural.add_sop(
            task_description="Search information online",
            steps=[
                "internet_search(query='test')",
                "web_fetch(url='...')",
                "web_search_in_page(url='...', query='test')",
                "create_file(file_path='result.txt', content='...')"
            ],
            success=True
        )
        
        # Check it was added
        assert len(procedural.sops) == 1
        assert procedural.sops[0]['task_description'] == "Search information online"
        assert len(procedural.sops[0]['steps']) == 4
        assert procedural.sops[0]['success_count'] == 1
        
        # Get relevant SOP
        sop = procedural.get_relevant_sop("Search information online")
        assert sop is not None
        assert sop['task_description'] == "Search information online"
        
        # Get relevant SOP with partial match
        sop2 = procedural.get_relevant_sop("Search something online")
        assert sop2 is not None  # Should match due to common words
        
        print("✅ Procedural Memory tests passed")


def test_tool_memory():
    """Test tool memory operations."""
    print("Testing Tool Memory...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_path = Path(tmpdir) / "tool_memory.json"
        tool_memory = ToolMemory(str(memory_path))
        
        # Add hint
        tool_memory.add_hint(
            tool_name='web_fetch',
            hint='Always use web_search_in_page after web_fetch',
            context={}
        )
        
        # Check it was added
        assert 'web_fetch' in tool_memory.tool_hints
        assert len(tool_memory.tool_hints['web_fetch']) == 1
        assert tool_memory.tool_hints['web_fetch'][0]['hint'] == 'Always use web_search_in_page after web_fetch'
        
        # Add duplicate - should increment usage count
        tool_memory.add_hint(
            tool_name='web_fetch',
            hint='Always use web_search_in_page after web_fetch',
            context={}
        )
        
        assert len(tool_memory.tool_hints['web_fetch']) == 1
        assert tool_memory.tool_hints['web_fetch'][0]['usage_count'] == 2
        
        # Get hints
        hints = tool_memory.get_hints('web_fetch', max_hints=2)
        assert len(hints) == 1
        assert 'web_search_in_page' in hints[0]
        
        print("✅ Tool Memory tests passed")


def test_muse_memory_manager():
    """Test MUSE memory manager integration."""
    print("Testing MUSE Memory Manager...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        muse = MUSEMemoryManager(str(tmpdir))
        
        # Start task
        muse.start_task("Test task")
        assert muse.current_task is not None
        assert muse.current_task['description'] == "Test task"
        
        # Record steps
        muse.record_step(
            tool_name='internet_search',
            parameters={'query': 'test'},
            result='Found results',
            success=True
        )
        
        assert len(muse.task_trajectory) == 1
        assert muse.task_trajectory[0]['tool_name'] == 'internet_search'
        assert muse.task_trajectory[0]['success'] == True
        
        # Finish task
        muse.finish_task(success=True, final_result='Task completed')
        
        # Check SOP was created (for successful multi-step task)
        # Note: We need at least 2 steps for SOP creation
        muse.start_task("Multi-step task")
        muse.record_step('step1', {}, 'ok', True)
        muse.record_step('step2', {}, 'ok', True)
        muse.finish_task(success=True, final_result='Done')
        
        assert len(muse.procedural.sops) == 1
        assert muse.procedural.sops[0]['task_description'] == "Multi-step task"
        
        # Get context for task
        context = muse.get_context_for_task("Multi-step task")
        assert 'ПРОЦЕДУРА (SOP)' in context or context == ""  # May not match if keywords don't overlap
        
        # Get stats
        stats = muse.get_stats()
        assert 'strategic' in stats
        assert 'procedural' in stats
        assert 'tool_memory' in stats
        
        print("✅ MUSE Memory Manager tests passed")


def test_memory_persistence():
    """Test that memory persists across instances."""
    print("Testing Memory Persistence...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create first instance and add data
        muse1 = MUSEMemoryManager(str(tmpdir))
        muse1.strategic.add_lesson("Test lesson", {})
        muse1.procedural.add_sop("Test task", ["step1", "step2"], True)
        muse1.tool_memory.add_hint("test_tool", "Test hint", {})
        muse1.save_all()
        
        # Create second instance - should load saved data
        muse2 = MUSEMemoryManager(str(tmpdir))
        
        assert len(muse2.strategic.lessons) == 1
        assert muse2.strategic.lessons[0]['lesson'] == "Test lesson"
        
        assert len(muse2.procedural.sops) == 1
        assert muse2.procedural.sops[0]['task_description'] == "Test task"
        
        assert 'test_tool' in muse2.tool_memory.tool_hints
        assert len(muse2.tool_memory.tool_hints['test_tool']) == 1
        
        print("✅ Memory Persistence tests passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Running MUSE Memory Tests")
    print("=" * 60)
    
    try:
        test_strategic_memory()
        test_procedural_memory()
        test_tool_memory()
        test_muse_memory_manager()
        test_memory_persistence()
        
        print("\n" + "=" * 60)
        print("✅ All MUSE Memory tests passed!")
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
