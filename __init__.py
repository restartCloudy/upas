"""
UPAS - 通用抽象形态系统
Universal Pattern Abstraction System
"""

from upas.core.upas_system import UPAS
from upas.core.data_preprocessor import DataPreprocessor
from upas.core.pattern_discovery import PatternDiscoveryEngine
from upas.core.pattern_recognition import PatternRecognitionEngine
from upas.core.evaluation_engine import SixDimensionEvaluator

__version__ = '1.0.0'
__all__ = [
    'UPAS',
    'DataPreprocessor',
    'PatternDiscoveryEngine',
    'PatternRecognitionEngine',
    'SixDimensionEvaluator',
]