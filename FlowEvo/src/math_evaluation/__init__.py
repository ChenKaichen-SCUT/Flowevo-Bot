"""Opt-in, post-submission mathematical evaluation. Never import into inference."""
__version__ = '3.0.0'
from .engine import MathEvaluatorV3
from .models import AnswerSpec, EvaluatorConfig
__all__ = ['MathEvaluatorV3', 'AnswerSpec', 'EvaluatorConfig']
