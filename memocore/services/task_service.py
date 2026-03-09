import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from memocore.models.task import Task
from memocore.schemas.task import TaskCreate, TaskUpdate

logger = logging.getLogger(__name__)


async def create_task(db: AsyncSession, data: TaskCreate) -> Task:
    task = Task(
        title=data.title,
        description=data.description,
        due_date=data.due_date,
        priority=data.priority,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    logger.info("Created task id=%s title=%r", task.id, task.title)
    return task


async def get_tasks(
    db: AsyncSession, include_completed: bool = False
) -> list[Task]:
    stmt = select(Task)
    if not include_completed:
        stmt = stmt.where(Task.is_completed.is_(False))
    stmt = stmt.order_by(Task.due_date.nulls_last(), Task.priority)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_task_by_title(
    db: AsyncSession, title: str, include_completed: bool = True
) -> Task | None:
    stmt = select(Task).where(Task.title.ilike(title))
    if not include_completed:
        stmt = stmt.where(Task.is_completed.is_(False))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_task(
    db: AsyncSession, task_id: str, data: TaskUpdate
) -> Task | None:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.flush()
    await db.refresh(task)
    return task


async def update_task_by_title(
    db: AsyncSession, title: str, data: TaskUpdate
) -> Task | None:
    stmt = select(Task).where(Task.title.ilike(title))
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if task is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.flush()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task_id: str) -> bool:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        return False
    await db.delete(task)
    return True


async def delete_task_by_title(db: AsyncSession, title: str) -> bool:
    stmt = select(Task).where(Task.title.ilike(title))
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if task is None:
        return False
    await db.delete(task)
    return True


async def delete_all_tasks(db: AsyncSession) -> int:
    result = await db.execute(delete(Task))
    return result.rowcount or 0
