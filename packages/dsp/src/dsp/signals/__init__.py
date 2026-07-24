"""Signal, Explanation, and Evidence generation for the Indicator Engine.

This subpackage is the Indicator Engine's own "domain" layer in the sense
Section 5.2 of the architecture document describes: it holds the
indicator-specific business rules (:mod:`dsp.signals.rules`) that decide
what a computed reading *means*, and the three generators that shape that
meaning into the platform's shared ``contracts`` vocabulary.
"""

from dsp.signals.evidence_generator import EvidenceGenerator
from dsp.signals.explanation_generator import ExplanationGenerator
from dsp.signals.rules import RuleOutcome, evaluate, register_rule
from dsp.signals.signal_generator import SignalGenerator

__all__ = [
    "EvidenceGenerator",
    "ExplanationGenerator",
    "RuleOutcome",
    "SignalGenerator",
    "evaluate",
    "register_rule",
]
