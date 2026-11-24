"""D's dependency-preserving selection over B's shared ranking and F's budget."""
from hybrid_retrieval import reject_annotations, render_selection, validate_parents


def validate_dependencies(units, dependencies):
    """Require an explicit entry for every sentence; dependencies preserve parent order."""
    reject_annotations(dependencies)
    bank = {unit['id']: unit for unit in units}
    sentences = {uid for uid, unit in bank.items() if unit['kind'] == 'synthesis_sentence'}
    if not isinstance(dependencies, dict) or set(dependencies) != sentences:
        raise ValueError('Dependencies must explicitly cover every synthesis sentence')
    for uid, required in dependencies.items():
        if (not isinstance(required, list) or any(not isinstance(x, str) for x in required)
                or len(set(required)) != len(required)):
            raise ValueError('Dependencies must be unique candidate IDs')
        unit = bank[uid]
        for other in required:
            target = bank.get(other)
            if (target is None or target['kind'] != 'synthesis_sentence'
                    or target['parent'] != unit['parent']
                    or target['position'] >= unit['position']):
                raise ValueError('Dependency must be an earlier sentence in the same parent')


def dependency_closure(uid, dependencies):
    selected, stack = set(), [uid]
    while stack:
        current = stack.pop()
        if current not in selected:
            selected.add(current)
            stack.extend(dependencies.get(current, ()))
    return selected


def select_contexts(ranked, parents, dependencies, budget, config):
    units = ranked['units']
    parent_bank = validate_parents(units, parents)
    validate_dependencies(units, dependencies)
    selected, remaining, steps = set(), {u['id'] for u in units}, []
    budget.prepare([])
    while remaining:
        values = {}
        for uid in remaining:
            redundancy = max((ranked['similarity'][uid][other] for other in selected), default=0)
            utility = (config['mmr_relevance'] * ranked['scores'][uid]['relevance']
                       - config['mmr_redundancy'] * redundancy)
            values[uid] = utility, redundancy
        uid = min(remaining, key=lambda key: (-values[key][0], key))
        remaining.remove(uid)
        closure = dependency_closure(uid, dependencies)
        added = closure - selected
        proposed = render_selection(selected | added, units, parent_bank)
        cost = budget.count(proposed)
        accepted = cost <= budget.max_tokens
        steps.append({'id': uid, 'utility': values[uid][0], 'redundancy': values[uid][1],
                      'closure_ids': sorted(closure), 'added_ids': sorted(added),
                      'dependency_ids': sorted(closure - {uid}), 'accepted': accepted,
                      'reason': 'selected' if accepted else 'whole_dependency_package_exceeds_budget',
                      'proposed_tokens': cost})
        if accepted:
            selected.update(added)
            remaining.difference_update(added)
    contexts = render_selection(selected, units, parent_bank)
    return {'contexts': contexts, 'selected_ids': sorted(selected),
            'unselected_ids': sorted({u['id'] for u in units} - selected),
            'steps': steps, 'evidence': budget.prepare(contexts)}


def paired_s1(selection, units, budget):
    """Delete synthesis from A without reranking or filling the freed budget."""
    contexts = [c for c in selection['contexts'] if c['kind'] == 'event']
    kinds = {u['id']: u['kind'] for u in units}
    return {'contexts': contexts,
            'selected_ids': [uid for uid in selection['selected_ids'] if kinds[uid] == 'event'],
            'removed_ids': [uid for uid in selection['selected_ids'] if kinds[uid] != 'event'],
            'pairing': 'delete_synthesis_from_A_without_refill',
            'evidence': budget.prepare(contexts)}
