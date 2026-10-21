"""Versioned local judge clarification; original upstream templates stay intact."""
from third_party.metamem_judge import get_anscheck_prompt

ORIGINAL = "upstream-66232c1"
CLARIFIED = "object-time-equivalence-v1"
CLARIFICATION = (
    "Evaluate the response against the reference for the exact object and time point asked in the question. "
    "Accept semantically equivalent answers. Do not assume that the latest information is the information "
    "the question asks for. If both earlier and later information appear, judge the answer given for the "
    "requested time point, not merely the presence of the latest value. "
    "For a personalized preference question, follow the supplied rubric: correctly recalling and using "
    "personal information is sufficient; not every rubric point is required. Do not introduce a requirement "
    "that every additional fact must come from retrieved memories.\n\n"
)


def judge_prompt(task, question, answer, response, abstention=False, version=ORIGINAL):
    if version not in (ORIGINAL, CLARIFIED):
        raise ValueError("Unknown judge prompt version")
    original = get_anscheck_prompt(task, question, answer, response, abstention)
    # Abstention is deliberately unchanged, including mixed abstention/speculation ambiguity.
    return CLARIFICATION + original if version == CLARIFIED and not abstention else original
