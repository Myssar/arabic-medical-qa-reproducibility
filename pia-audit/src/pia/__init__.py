"""pia-audit: permutation integrity auditing for multiple-choice LLM benchmarks."""
from .rules import Item, ItemAudit, audit, normalize, POSITIONAL_VOCAB
from .permute import free_permutation, safe_permutation, pinned_labels, is_identity
from .decompose import change_rates, transition_decomposition, specificity_ratio

__version__ = "0.1.0"
