"""Atomic sealed task records with config/bank/split/manifest binding."""
from pathlib import Path
from .common import digest, read_json, write_json
from .schemas import Submission


class Checkpoint:
    def __init__(self,directory,*,config,bank_hash,split,mode,manifest_hash,simulated,resume=False):
        self.directory=Path(directory); self.path=self.directory/'checkpoint.json'
        self.identity={'config_hash':digest(config.model_dump()),'bank_hash':bank_hash,'split':split,
                       'mode':mode,'manifest_hash':manifest_hash,'simulated':simulated}
        self.records={}
        if self.path.exists():
            if not resume: raise FileExistsError('Run exists; use --resume or a new output directory')
            data=read_json(self.path)
            if data['identity']!=self.identity: raise ValueError('Checkpoint config/bank/split/manifest mismatch')
            for row in data['submissions']:
                s=Submission.model_validate(row);s.assert_frozen()
                if s.bank_hash!=bank_hash or s.split!=split: raise ValueError('Submission bank/split mismatch')
                self.records[s.task_id]=s
        elif self.directory.exists() and any(self.directory.iterdir()):
            raise FileExistsError('Nonempty output directory lacks matching checkpoint')
        else:
            self.directory.mkdir(parents=True,exist_ok=True)
            self.save()

    def save(self):
        write_json(self.path,{'identity':self.identity,'submissions':[s.model_dump(mode='json') for s in self.records.values()]})

    def commit(self,submission):
        submission.assert_frozen()
        if submission.bank_hash!=self.identity['bank_hash'] or submission.split!=self.identity['split']:
            raise ValueError('Cannot commit another bank/split')
        old=self.records.get(submission.task_id)
        if old and old.seal!=submission.seal: raise ValueError('Cannot overwrite a frozen answer')
        self.records[submission.task_id]=submission;self.save()
