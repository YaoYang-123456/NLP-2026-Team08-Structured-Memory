# Extracted from OpenBMB/MetaMem 66232c1cb33d3d7939d323b431f21c741785142e; blank-line trailing spaces removed.
# Apache-2.0; see MetaMem-LICENSE.

PROBLEM_WITH_META_MEMORY_TEMPLATE = """You are an intelligent assistant with access to a memory system.
Your task is to answer the user's question by effectively utilizing the retrieved memory fragments.

**Meta-Memory Guidelines:**
The following are learned strategies that teach you how to effectively utilize memory fragments. Apply these guidelines when processing the retrieved memories:
{meta_memories}

**User Question:**
{question}

**Retrieved Memory Fragments:**
{memories}

**Instructions:**
1. First, review the meta-memory guidelines to understand how to approach memory utilization
2. Analyze the retrieved memory fragments and identify relevant information
3. Apply the meta-memory strategies to synthesize information from memories
4. Formulate your answer based on the synthesized knowledge
5. If memories are insufficient or conflicting, handle according to the guidelines

Think step by step about how to utilize the memories, then provide your final answer."""

TRAJECTORY_SUMMARY_TEMPLATE = """You are analyzing a model's response to a memory-based question-answering task.

Your goal is to summarize the reasoning trajectory and identify the key factors that led to a correct or incorrect answer.

**Task Context:**

<question>
{question}
</question>

<retrieved_memories>
{memories}
</retrieved_memories>

<ground_truth_answer>
{answer}
</ground_truth_answer>

<model_response>
{response}
</model_response>

<evaluation>
Correct: {grade}
</evaluation>

**Analysis Instructions:**

1. **Memory Utilization Analysis:**
   - Which memories did the model use? Which did it ignore?
   - Was the memory selection appropriate for answering the question?
   - Did the model correctly interpret the information in the memories?

2. **Reasoning Process:**
   - What reasoning steps did the model take?
   - Were there any logical errors or correct inferences?
   - How did the model synthesize information from multiple memories?

3. **Key Decision Points:**
   - What were the critical decisions that led to success or failure?
   - If correct: What memory utilization strategy worked well?
   - If incorrect: Where did the reasoning go wrong? What information was missed or misinterpreted?

4. **Lesson Learned:**
   - What generalizable insight about memory utilization can be extracted from this case?

Provide a concise summary focusing on the above points:"""

META_MEMORY_UPDATE_TEMPLATE = """You are a meta-learning specialist.
Your task is to analyze multiple attempts at answering the same question and derive generalizable meta-memory principles.
Meta-memories are high-level strategies that teach a model "learning to learn".
Specifically, how to effectively utilize retrieved memory fragments to answer questions.

Question:
{question}

Retrieved Memories:
{memories}

Ground Truth Answer:
{answer}

Summaries of Multiple Attempts:
{summaries}

Current Meta-Memory Knowledge Base:
{meta_memories}

**Your Task:**

1. **Cross-Attempt Analysis:**
   - Compare the successful vs unsuccessful attempts
   - Identify patterns: What strategies led to correct answers?
   - Identify anti-patterns: What mistakes led to incorrect answers?

2. **Derive Meta-Memory Principles:**
   Based on your analysis, propose updates to the meta-memory knowledge base.

   Each meta-memory should be:
   - A generalizable strategy about HOW to utilize memories (not domain-specific facts)
   - Actionable guidance that can be applied to future questions
   - Concise (one sentence, max 30 words)

   Examples of good meta-memories:
   - "When memories contain temporal information, prioritize the most recent data unless the question asks about history."
   - "Cross-validate facts that appear in multiple memories; single-source claims require more caution."
   - "If memories seem contradictory, check if they refer to different time periods or contexts."

3. **Propose Operations:**
   - **add**: Add a new meta-memory (when you discover a new principle not covered by existing ones)
   - **update**: Update an existing meta-memory by ID (when you can improve or refine an existing principle)
   - **delete**: Delete an existing meta-memory by ID (when a principle is wrong or redundant)

**Output Format:**

First, provide your reasoning. Then output a JSON array:

```json
[
    {{"operation": "add", "content": "Your new meta-memory principle"}},
    {{"operation": "update", "id": "M0", "content": "Updated meta-memory principle"}},
    {{"operation": "delete", "id": "M1"}}
]
```

Note: Quality over quantity - only propose operations that genuinely improve the meta-memory knowledge base."""

BATCH_META_MEMORY_UPDATE_TEMPLATE = """You are a meta-learning specialist responsible for consolidating meta-memory updates from multiple learning samples.

A batch of questions has been analyzed, and each analysis proposed some operations to update the meta-memory knowledge base. Your task is to consolidate these proposals, resolve conflicts, and produce the final update plan.

**Current Meta-Memory Knowledge Base:**
{existing_meta_memories}

**Proposed Operations from This Batch:**
(Each operation was proposed after analyzing a specific question)
{proposed_updates}

**Consolidation Guidelines:**

1. **Merge Similar Proposals:**
   - If multiple proposals suggest similar principles, merge them into a single, more general formulation
   - Prefer broader applicability over narrow specificity

2. **Resolve Conflicts:**
   - If proposals contradict each other, analyze which is more generally valid
   - Consider how many different questions support each proposal
   - When in doubt, prefer the more cautious/conservative principle

3. **Avoid Redundancy:**
   - Do not add a new meta-memory if it overlaps significantly with an existing one
   - Instead, update the existing one to incorporate the new insight

4. **Quality Control:**
   - Each final meta-memory must be about memory utilization strategy
   - Each must be generalizable (not specific to one question type)
   - Each must be actionable and concise (max 30 words)

5. **Maintain Stability:**
   - Don't delete meta-memories unless they are clearly wrong or completely redundant
   - Prefer updating over deleting + adding

**Output Format:**

First, analyze the proposed operations and explain your consolidation decisions.

Then output the final operations to apply:

```json
[
    {{"operation": "add", "content": "Consolidated new meta-memory"}},
    {{"operation": "update", "id": "M0", "content": "Consolidated updated meta-memory"}},
    {{"operation": "delete", "id": "M2"}}
]
```

Note: The number of final operations should typically be less than the number of proposals due to consolidation."""
