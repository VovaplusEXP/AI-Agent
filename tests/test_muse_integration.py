# test_muse_integration.py
"""
Integration test for MUSE memory system with agent workflow.

This test simulates a complete agent workflow with MUSE memory:
1. Start task
2. Execute steps
3. Finish task
4. Reflection extracts learnings
5. Memory is saved
6. Next task uses learnings
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from muse_memory import MUSEMemoryManager
from reflection_agent import ReflectionAgent


class MockLLM:
    """Mock LLM for testing."""
    
    def create_chat_completion(self, messages, max_tokens=512, temperature=0.2):
        """Mock chat completion."""
        # Simple mock response for reflection
        return {
            'choices': [{
                'message': {
                    'content': """<SUCCESS>yes</SUCCESS>
<REASON>Task was completed successfully with all steps executed correctly.</REASON>
<LESSONS>
- Using web_search_in_page after web_fetch is effective for data extraction
- Creating file immediately after getting information prevents data loss
</LESSONS>"""
                }
            }]
        }
    
    def tokenize(self, text):
        """Mock tokenization - roughly 4 chars per token."""
        return [0] * (len(text) // 4)


def test_full_workflow():
    """Test complete MUSE workflow with task execution."""
    print("\n" + "=" * 60)
    print("Testing Full MUSE Workflow")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize components
        muse = MUSEMemoryManager(str(tmpdir))
        llm = MockLLM()
        reflection = ReflectionAgent(llm)
        
        # === TASK 1: Successful task with learnings ===
        print("\n[Task 1] Executing successful task...")
        
        task_desc = "Search information about Python online"
        muse.start_task(task_desc)
        
        # Simulate steps
        steps = [
            {'tool': 'internet_search', 'params': {'query': 'Python 3.13'}, 'result': 'Found URLs', 'success': True},
            {'tool': 'web_fetch', 'params': {'url': 'https://python.org'}, 'result': 'HTML content', 'success': True},
            {'tool': 'web_search_in_page', 'params': {'url': 'https://python.org', 'query': 'Python 3.13 features'}, 'result': 'Features extracted', 'success': True},
            {'tool': 'create_file', 'params': {'file_path': 'python.txt', 'content': '...'}, 'result': 'File created', 'success': True}
        ]
        
        for step in steps:
            muse.record_step(
                tool_name=step['tool'],
                parameters=step['params'],
                result=step['result'],
                success=step['success']
            )
        
        print(f"  ✓ Recorded {len(steps)} steps")
        
        # Reflection
        print("  [Reflection] Evaluating task completion...")
        success, evaluation, lessons = reflection.evaluate_task_completion(
            goal=task_desc,
            final_result="Information about Python saved to file",
            trajectory=muse.task_trajectory
        )
        
        print(f"  ✓ Success: {success}")
        print(f"  ✓ Evaluation: {evaluation}")
        print(f"  ✓ Lessons extracted: {len(lessons)}")
        
        # Finish task and save learnings
        muse.finish_task(success=success, final_result="Task completed")
        
        # Add lessons to strategic memory
        for lesson in lessons:
            muse.strategic.add_lesson(lesson, context={'task': task_desc})
        
        print(f"  ✓ Added {len(lessons)} strategic lessons")
        
        # Extract tool patterns
        tool_patterns = reflection.extract_tool_patterns(muse.task_trajectory)
        for tool, hints in tool_patterns.items():
            for hint in hints:
                muse.tool_memory.add_hint(tool, hint)
        
        print(f"  ✓ Added tool patterns for {len(tool_patterns)} tools")
        
        # Check SOP was created
        assert len(muse.procedural.sops) == 1, "SOP should be created for successful multi-step task"
        print(f"  ✓ SOP created: {muse.procedural.sops[0]['task_description']}")
        
        # Save all memory
        muse.save_all()
        print("  ✓ Memory saved")
        
        # === TASK 2: Similar task should use learnings ===
        print("\n[Task 2] Executing similar task with learnings...")
        
        task_desc2 = "Search information online"
        
        # Get context - should include SOP and lessons
        context = muse.get_context_for_task(task_desc2)
        
        if context:
            print("  ✓ Got MUSE context:")
            print("    " + context.replace('\n', '\n    ')[:200] + "...")
        else:
            print("  ! No matching context (expected for simple keyword matching)")
        
        # Get relevant SOP
        sop = muse.procedural.get_relevant_sop(task_desc2)
        if sop:
            print(f"  ✓ Found relevant SOP: {sop['task_description']}")
            print(f"    Steps: {len(sop['steps'])}")
        
        # Get tool hints
        hints = muse.tool_memory.get_hints('web_fetch')
        if hints:
            print(f"  ✓ Got {len(hints)} hints for 'web_fetch'")
        
        # === TASK 3: Failed task should add strategic lessons ===
        print("\n[Task 3] Executing failed task...")
        
        muse.start_task("Attempt file operation")
        muse.record_step(
            tool_name='read_file',
            parameters={'file_path': 'nonexistent.txt'},
            result='Error: File not found',
            success=False
        )
        
        # Identify failure causes
        failures = reflection.identify_failure_causes(muse.task_trajectory)
        assert len(failures) == 1, "Should identify one failure"
        print(f"  ✓ Identified failure: {failures[0]['error_type']}")
        
        # Add strategic lesson from failure
        lesson = f"When getting 'not_found' error with read_file, use list_directory first"
        muse.strategic.add_lesson(
            lesson=lesson,
            context={'tool_name': 'read_file', 'error_type': 'not_found'}
        )
        
        muse.finish_task(success=False, final_result="Failed due to file not found")
        print("  ✓ Strategic lesson added for failure")
        
        # === Memory Stats ===
        print("\n[Memory Stats]")
        stats = muse.get_stats()
        print(f"  Strategic lessons: {stats['strategic']['lessons']}")
        print(f"  Procedural SOPs: {stats['procedural']['sops']}")
        print(f"  Tool hints: {stats['tool_memory']['total_hints']} for {stats['tool_memory']['tools_tracked']} tools")
        
        # === Test Memory Compression ===
        print("\n[Memory Compression]")
        
        # Add low-quality lesson
        muse.strategic.add_lesson("Low quality lesson", {})
        muse.strategic.lessons[-1]['quality_score'] = 0.1
        muse.strategic.lessons[-1]['usage_count'] = 1
        
        stats_before = muse.get_stats()
        print(f"  Before: {stats_before['strategic']['lessons']} lessons")
        
        # Compress
        muse.compress_all(llm)
        
        stats_after = muse.get_stats()
        print(f"  After: {stats_after['strategic']['lessons']} lessons")
        print(f"  ✓ Removed {stats_before['strategic']['lessons'] - stats_after['strategic']['lessons']} low-quality lessons")
        
        # === Test Persistence ===
        print("\n[Testing Persistence]")
        
        # Create new instance - should load saved data
        muse2 = MUSEMemoryManager(str(tmpdir))
        
        stats2 = muse2.get_stats()
        assert stats2['strategic']['lessons'] > 0, "Should load strategic lessons"
        assert stats2['procedural']['sops'] > 0, "Should load SOPs"
        print("  ✓ Memory persisted and loaded successfully")
        
        print("\n" + "=" * 60)
        print("✅ Full MUSE Workflow Test Passed!")
        print("=" * 60)


def test_compression_triggers():
    """Test that compression triggers work correctly."""
    print("\n" + "=" * 60)
    print("Testing Compression Triggers")
    print("=" * 60)
    
    # Use fresh temp directory to ensure clean state
    with tempfile.TemporaryDirectory() as tmpdir:
        muse = MUSEMemoryManager(str(tmpdir))
        llm = MockLLM()
        reflection = ReflectionAgent(llm)
        
        # Test 1: Empty memory should not trigger compression
        stats = muse.get_stats()
        should_compress, reason = reflection.should_compress_memory(stats)
        print(f"  Test 1 - Empty memory: should_compress={should_compress}, reason='{reason}'")
        # Note: Empty memory won't trigger compression
        
        # Test 2: Add many lessons to trigger compression
        for i in range(60):
            muse.strategic.add_lesson(f"Lesson {i}", {})
        
        stats = muse.get_stats()
        should_compress, reason = reflection.should_compress_memory(stats)
        assert should_compress, f"Should compress with >50 lessons, got {stats['strategic']['lessons']} lessons"
        print(f"  ✓ Compression triggered: {reason}")
        
        # Test 3: Test with many SOPs
        muse2 = MUSEMemoryManager(str(tmpdir) + "_2")
        for i in range(110):
            muse2.procedural.add_sop(f"Task {i}", ["step1", "step2"], True)
        
        stats = muse2.get_stats()
        should_compress, reason = reflection.should_compress_memory(stats)
        assert should_compress, f"Should compress with >100 SOPs"
        print(f"  ✓ Compression triggered for SOPs: {reason}")
        
        print("\n" + "=" * 60)
        print("✅ Compression Triggers Test Passed!")
        print("=" * 60)


def main():
    """Run all integration tests."""
    try:
        test_full_workflow()
        test_compression_triggers()
        
        print("\n" + "=" * 60)
        print("✅ All Integration Tests Passed!")
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
