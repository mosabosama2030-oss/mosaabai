"""MosaabAI Minimal Demo — end-to-end task execution.
Task: "2 + 3 * 4"  →  Expected: 14
"""
from __future__ import annotations
import asyncio
from core.cognitive_loop import LoopStage, Task
from core.errors import ErrorCode, err, ok
from tools.built_in.calculator import Calculator
from tools.tool_environment import create_root


async def demo() -> None:
    print("═" * 60)
    print("  MOSAABAI MINIMAL DEMO")
    print("═" * 60)
    print()

    task = Task(description="What is 2 + 3 * 4?", goal="Compute arithmetic")
    print(f"[TASK] {task.description}")
    print()

    print(f"[{LoopStage.UNDERSTAND.value.upper()}] Analyzing...")
    expression = "2 + 3 * 4"
    print(f"     Extracted: {expression}")
    print()

    print(f"[{LoopStage.PLAN.value.upper()}] Planning...")
    print("     Step 1: Calculator tool")
    print(f"     Step 2: Evaluate {expression}")
    print("     Step 3: Verify")
    print()

    print(f"[{LoopStage.EXECUTE.value.upper()}] Setting up environment...")
    calc = Calculator()
    env = create_root("demo-env", [calc], {"compute"})
    print(f"     Environment: {env.environment_id}")
    print(f"     Tools: {env.list_tools()}")
    print()

    print(f"[{LoopStage.EXECUTE.value.upper()}] Executing calculator...")
    tool = env.get_tool("calculator")
    result = await tool.execute(expression=expression)
    print(f"     Result: success={result.success}, output={result.output}")
    print()

    print(f"[{LoopStage.OBSERVE.value.upper()}] Observation: {result.output}")
    print()

    print(f"[{LoopStage.EVALUATE.value.upper()}] Evaluating...")
    expected = 14
    if result.output == expected:
        print(f"     ✓ Matches expected: {expected}")
        evaluation = ok(result.output)
    else:
        print(f"     ✗ Expected {expected}, got {result.output}")
        evaluation = err(ErrorCode.verification_failure, f"got {result.output}")
    print()

    print(f"[{LoopStage.VERIFY.value.upper()}] Verifying...")
    if evaluation.is_ok():
        print(f"     ✓ PASSED — value: {evaluation.unwrap()}")
    else:
        print(f"     ✗ FAILED — {evaluation.unwrap_err().code.value}")
    print()

    print(f"[{LoopStage.LEARN.value.upper()}] Recording experience...")
    print(f"     Task: {task.description}")
    print(f"     Tool: calculator")
    print(f"     Success: {result.success}")
    print()

    print(f"[{LoopStage.ANSWER.value.upper()}] Final answer:")
    print()
    if evaluation.is_ok():
        print(f"     >>> {expression} = {evaluation.unwrap()}")
    else:
        print(f"     >>> FAILED")
    print()
    print("═" * 60)
    print("  DEMO COMPLETE")
    print("═" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
