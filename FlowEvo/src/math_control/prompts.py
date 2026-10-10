"""Gold-free interventions appended to the same native base prompt."""
import json
GENERIC='Recheck what the original problem asks, including its constraints. If the draft answers the right question, keep its answer. Otherwise correct it. End with: The answer is [your answer].'

def intervention_prompt(base_prompt,kind,visible,reasoning,decision):
    if kind=='generic':
        context=visible[-10000:] if visible.strip() else reasoning[-8000:]
        return base_prompt+'\n\nPrevious draft (unverified):\n'+context+'\n\n'+GENERIC
    if kind=='a1':
        c=decision['candidate'];excerpt=reasoning[max(0,c['start']-2000):min(len(reasoning),c['end']+2500)]
        return base_prompt+'\n\nA previous request ended without a complete final response. This is a NEW request; no hidden reasoning state is retained. Exposed draft excerpt (unverified):\n'+excerpt+'\n\nCandidate expression: '+c['text']+'\nCheck that the candidate answers the original target and respects its constraints. It may be wrong; do not accept it merely because it appears in the draft. Finish the mathematical answer. End with: The answer is [your answer].'
    if kind=='a2':
        return base_prompt+'\n\nPrevious final draft (unverified):\n'+visible[-10000:]+'\n\nPublic-question goal specification:\n'+json.dumps(decision['goal_spec'],ensure_ascii=False)+'\nObserved possible target mismatch:\n'+json.dumps(decision['evidence'],ensure_ascii=False)+'\nCheck this specific mismatch against the original question. Preserve valid work; correct the requested object or constraints only if necessary. End with: The answer is [your answer].'
    raise ValueError('unknown intervention')
