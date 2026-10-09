"""Small structural protocols leave code/MBPP extension points explicit."""
from typing import Protocol
from .schemas import ProblemView, SkillRecord, RouteDecision

AbstractSkill = SkillRecord
MathStrategySkill = SkillRecord


class AbstractRetriever(Protocol):
    def retrieve(self, task: ProblemView, bank, *, active_only=True) -> list[SkillRecord]: ...


class AbstractRouter(Protocol):
    def route(self, task: ProblemView, bank) -> RouteDecision: ...


class AbstractExecutor(Protocol):
    def execute(self, task: ProblemView): ...
