"""Seven MATH subjects; unknown categories are deliberately not guessed."""
SUBJECTS = ('prealgebra', 'algebra', 'intermediate_algebra', 'geometry',
            'number_theory', 'counting_probability', 'precalculus')
ALIASES = {s.replace('_', ' '): s for s in SUBJECTS}
ALIASES.update({'counting & probability': 'counting_probability',
                'counting and probability': 'counting_probability'})
INITIAL_PATTERNS = {
    'prealgebra': ['unit_rate', 'ratio_scaling'],
    'algebra': ['expression_grouping', 'factorization_pattern', 'substitution_reduction'],
    'intermediate_algebra': ['symmetric_expression', 'equation_structure_rewrite'],
    'geometry': ['similarity_pattern', 'area_decomposition', 'circle_angle_constraints'],
    'number_theory': ['prime_divisibility', 'modular_reduction', 'gcd_lcm_structure'],
    'counting_probability': ['complement_counting', 'case_partition'],
    'precalculus': ['trigonometric_identity', 'function_composition'],
}


def normalize_subject(value):
    if not value:
        return None
    return ALIASES.get(str(value).strip().lower().replace('_', ' '))


def detect_subject(problem):
    if problem.subject:
        return problem.subject, 'metadata'
    declared = normalize_subject(problem.public_metadata.get('type'))
    if declared:
        return declared, 'metadata'
    text = problem.problem.lower()
    rules = [('geometry', ('triangle', 'circle', 'perimeter')),
             ('number_theory', ('prime', 'divisib', 'remainder', 'modulo', '\\pmod')),
             ('counting_probability', ('probability', 'permutation', 'choose')),
             ('precalculus', ('\\sin', '\\cos', 'trigonometric')),
             ('algebra', ('polynomial', 'quadratic', 'equation'))]
    hits = [s for s, words in rules if any(w in text for w in words)]
    return (hits[0], 'rule') if len(hits) == 1 else (None, 'unknown')
