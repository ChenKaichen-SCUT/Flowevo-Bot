"""Response-bound manual mathematical checks, not automatic semantic labels."""
from common import *

def main():
    high={r['task_id']:r for r in jl(HIGH/'baseline_results.jsonl')}
    specifications=[
        ('math_test_number_theory_536','candidate_revision_and_useful_verification','So answer 14',
         'The proposed14 is obtained by incorrectly removing000 from the15 triples summing to4. Later enumeration and the explicit correction recover15. This suffix adds necessary corrective information; candidate appearance was not sufficiency.'),
        ('math_test_counting_probability_192','candidate_revision','Thus answer 1',
         'The text considers1 before later proposing10/19. A dodecahedron has190 vertex pairs;12 pentagonal faces give120 pairs counting30 edges twice, so90 pairs lie in a face and100 pass through the interior. The later10/19 claim has a different, substantive boundary interpretation. Do not call this whole trajectory redundant.'),
        ('math_test_prealgebra_131','redundant_confirmation_span','Let\'s quickly check by writing a mental program',
         'This late span repeats the already-stated count19 and says it was already done, before committing the final response. It adds no new enumerated rectangles in this specific span. This local annotation does not certify that every earlier check was redundant.'),
        ('math_test_counting_probability_126','finalization_without_new_math','The answer is 50.',
         'The late explicit-answer spans discuss the required final wording and ending the response. These formatting statements are not new mathematical evidence. This is a local observation, not a claim that all intervening reasoning is unnecessary.')]
    reviews=[]
    for tid,category,needle,proof in specifications:
        h=high[tid];r=read(HIGH/h['response_path']);text=r['response']['choices'][0]['message']['reasoning_content']
        start=text.rfind(needle) if category=='finalization_without_new_math' else text.find(needle)
        assert start>=0,(tid,needle)
        reviews.append(dict(task_id=tid,category=category,response_hash=r['response_hash'],reasoning_sha256=digest(text),
            span_start=start,span_end=min(len(text),start+600),text=text[start:start+600],assessment=proof,
            scope='Human mathematical/event review, limited to cited span; not a formal certification of the whole trace'))
    lines('evidence/manual_trace_reviews.jsonl',reviews)
    print('Four response-hash-bound event audits saved')
if __name__=='__main__':main()
