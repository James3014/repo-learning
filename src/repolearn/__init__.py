"""RepoLearn portable human-learning contracts."""

from .assessment import (
    AssessmentClassification,
    AssessmentResult,
    CueLevel,
    JudgmentEvidence,
    MasteryLevel,
    TransferDistance,
    assess_judgment,
)
from .backends import (
    BackendConflictError,
    LocalFileBackend,
    NexusLedgerBackend,
    ReadOnlyCanonicalBackendError,
    StaleProjectionError,
)
from .client import ClientLearningDecision, prepare_learning_decision
from .state import StateBackend, StateUnavailableError
from .triggers import (
    InteractionMode,
    LearningOpportunity,
    TaskContext,
    TriggerDisposition,
    TriggerResult,
    select_learning_opportunity,
)

__all__ = [
    "AssessmentClassification",
    "AssessmentResult",
    "BackendConflictError",
    "ClientLearningDecision",
    "CueLevel",
    "InteractionMode",
    "JudgmentEvidence",
    "LearningOpportunity",
    "LocalFileBackend",
    "MasteryLevel",
    "NexusLedgerBackend",
    "ReadOnlyCanonicalBackendError",
    "StaleProjectionError",
    "StateBackend",
    "StateUnavailableError",
    "TaskContext",
    "TransferDistance",
    "TriggerDisposition",
    "TriggerResult",
    "assess_judgment",
    "prepare_learning_decision",
    "select_learning_opportunity",
]
