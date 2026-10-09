"""Generate openly synthetic offline fixtures; no labels are used by the mock client."""
from pathlib import Path
from flowevo_bot.data import write_manifest
from flowevo_bot.schemas import ProblemView,EvaluationRecord,SkillRecord
from flowevo_bot.strategy_bank import StrategyBank
from flowevo_bot.taxonomy import SUBJECTS

ROOT=Path(__file__).resolve().parents[1]


def main():
    specs={
      'train':('train-build',[
        ('algebra','Find the degree of the polynomial 2x^3 + 2x^2 + 5.','3'),
        ('algebra','Identify the degree in this polynomial expression: 4x^5 + 3x^2 + 8.','5'),
        ('algebra','A polynomial is written as 3x^7 + 6x^2 + 9. What is its degree?','7'),
        ('number_theory','Find the remainder of 17 modulo 5.','2'),
        ('number_theory','Determine the residue for 29 modulo 7.','1'),
        ('number_theory','State the least nonnegative remainder of 38 modulo 9.','2'),
      ]),
      'dev':('train-dev',[
        ('algebra','A student collects nonzero monomials to form a polynomial 8x^9 + 4x^2 + 3. Report the degree that controls its leading growth.','9'),
        ('algebra','Consider an algebra notebook describing polynomial 6x^6 + 2x^2 + 1. Which degree remains when its displayed terms are collected?','6'),
        ('number_theory','A cyclic counter asks for the remainder after reducing its position: 44 modulo 6. Provide the canonical residue.','2'),
        ('number_theory','The remainder encodes a cyclic label in this arithmetic exercise: 53 modulo 8. Determine that label.','5'),
      ]),
      'test':('test',[
        ('algebra','An engineer models a signal using polynomial 7x^8 + 4x^2 + 6. Determine the degree of the resulting expression.','8'),
        ('number_theory','For a new cyclic scheduling instance calculate the remainder from 61 modulo 9 and give the least residue.','7'),
        ('prealgebra','Compute (8+4)/3.','4'),
      ]),
    }
    for name,(split,rows) in specs.items():
        ps=[];labels=[]
        for i,(subject,text,answer) in enumerate(rows):
            tid=f'fixture_{name}_{i}'
            ps.append(ProblemView(task_id=tid,problem=text,subject=subject,level='Level 1',public_metadata={'benchmark':'math'}))
            labels.append(EvaluationRecord(task_id=tid,gold_answer=answer,reference_solution='Synthetic fixture evaluation only.'))
        write_manifest(ROOT/'data/manifests',name,split,ps,labels,synthetic=True,source='hand-authored fixture; not MATH benchmark',seed=42)
    bank=StrategyBank(synthetic=True)
    features=['unit_rate','polynomial','equation','triangle','modular','probability','trigonometric']
    steps=[['Identify the quantity per unit.','Scale to the requested number of units.'],
           ['Collect like polynomial terms.','Inspect the largest remaining exponent.'],
           ['Rewrite both sides of the equation under equivalent transformations.','Check any excluded values.'],
           ['Identify corresponding triangle angles and sides.','Use a justified similarity ratio.'],
           ['Reduce terms modulo the stated modulus.','Verify the resulting congruence.'],
           ['Define equally likely elementary events.','Count favorable and total outcomes.'],
           ['Identify a valid trigonometric identity.','Preserve domains while rewriting.']]
    for subject,feature,sequence in zip(SUBJECTS,features,steps):
        bank.add(SkillRecord(skill_id='example_'+subject,subject=subject,strategy_pattern='unvalidated_example',
            name=subject+' schema example',trigger_features=[feature],strategy_steps=sequence,
            verification_rules=['Check assumptions in the original problem.'],
            compact_prompt=' '.join(sequence),status='candidate'))
    bank.save(ROOT/'data/skill_banks/schema_examples.json')
    StrategyBank(synthetic=True).save(ROOT/'data/skill_banks/empty_mock_bank.json')
    print('Synthetic manifests and seven non-active schema examples generated.')


if __name__=='__main__':main()
