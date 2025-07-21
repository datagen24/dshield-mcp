import pytest
import asyncio
from src.resource_manager import ResourceManager
from src.operation_tracker import OperationTracker

@pytest.mark.asyncio
async def test_resource_manager_cleanup():
    manager = ResourceManager()
    cleaned = []
    async def cleanup():
        cleaned.append(True)
    manager.register_cleanup_handler(cleanup)
    await manager.cleanup_all()
    assert cleaned == [True]

@pytest.mark.asyncio
async def test_operation_tracker():
    tracker = OperationTracker()
    async def dummy():
        await asyncio.sleep(0.01)
    task = asyncio.create_task(dummy())
    tracker.register_operation('op1', task)
    await tracker.wait_for_operations()
    tracker.complete_operation('op1')
    assert tracker.get_active_operations() == [] 