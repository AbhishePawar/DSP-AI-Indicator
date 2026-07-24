"""Business signal, explanation, and evidence generation.

This subpackage is the Fundamental Engine's own "domain" layer in the
sense Section 5.2 of the architecture document describes: it holds the
metric-specific business rules (:mod:`fundamental.signals.rules`) that
decide what a computed ratio *means*, and the three generators that
shape that meaning into the platform's shared ``contracts`` vocabulary.
"""

from fundamental.signals.evidence_generator import EvidenceGenerator
from fundamental.signals.explanation_generator import ExplanationGenerator
from fundamental.signals.rules import BusinessRuleOutcome, evaluate, register_rule
from fundamental.signals.signal_generator import BusinessSignalGenerator

__all__ = [
    "BusinessRuleOutcome",
    "BusinessSignalGenerator",
    "EvidenceGenerator",
    "ExplanationGenerator",
    "evaluate",
    "register_rule",
]
