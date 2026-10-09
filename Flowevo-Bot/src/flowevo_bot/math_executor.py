"""Optional Route C: only complete, tightly recognized integer-arithmetic tasks."""
import ast
import operator
import re
from fractions import Fraction
from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionResult:
    answer: str
    full_task_verified: bool
    method: str


class MathExecutor:
    OPS = {ast.Add:operator.add, ast.Sub:operator.sub, ast.Mult:operator.mul, ast.Div:operator.truediv}

    def execute(self, task):
        match = re.fullmatch(r'\s*(?:Compute|Calculate|Evaluate)\s+([\d\s()+*/\-]+)\s*\.?\s*', task.problem, re.I)
        if not match or len(match[1]) > 200:
            return None
        def walk(node):
            if isinstance(node, ast.Constant) and type(node.value) is int and abs(node.value)<10**12:
                return Fraction(node.value)
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
                return -walk(node.operand)
            if isinstance(node, ast.BinOp) and type(node.op) in self.OPS:
                return self.OPS[type(node.op)](walk(node.left),walk(node.right))
            raise ValueError('Unsupported arithmetic')
        try:
            tree = ast.parse(match[1].strip(), mode='eval')
            if len(list(ast.walk(tree))) > 80: return None
            value = walk(tree.body)
            return ExecutionResult(str(value),True,'exact rational arithmetic; full anchored grammar')
        except (SyntaxError,ValueError,ZeroDivisionError,RecursionError):
            return None
