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
    ProjectionConflictError,
    ReadOnlyCanonicalBackendError,
    StaleProjectionError,
)
from .client import (
    ClientLearningDecision,
    LearningResponseDisposition,
    LearningResponseResult,
    classify_learning_response,
    prepare_learning_decision,
)
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
    "LearningResponseDisposition",
    "LearningResponseResult",
    "LocalFileBackend",
    "MasteryLevel",
    "NexusLedgerBackend",
    "ProjectionConflictError",
    "ReadOnlyCanonicalBackendError",
    "StaleProjectionError",
    "StateBackend",
    "StateUnavailableError",
    "TaskContext",
    "TransferDistance",
    "TriggerDisposition",
    "TriggerResult",
    "assess_judgment",
    "classify_learning_response",
    "prepare_learning_decision",
    "select_learning_opportunity",
]
