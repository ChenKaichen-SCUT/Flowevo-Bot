from common import *
import requests,tarfile,subprocess

def main():
 dest=OUT/'evidence/official_aflow_data.tar.gz';url='https://drive.google.com/uc?export=download&id=1DNoegtZiUhWtvkd2xoIuElmIi4ah7k8e'
 if not dest.exists():
  r=requests.get(url,timeout=(30,180));r.raise_for_status();assert r.content[:2]==b'\x1f\x8b',(r.headers.get('content-type'),len(r.content),r.text[:180]if len(r.content)<5000 else'not gzip');dest.write_bytes(r.content)
 with tarfile.open(dest,'r:gz')as tf:
  inventory=[{'name':m.name,'size':m.size}for m in tf.getmembers()if m.isfile()];save('evidence/official_archive_inventory.json',inventory)
  selected=[m for m in tf.getmembers()if m.isfile()and ('math' in m.name.lower()or 'split' in m.name.lower())]
  for m in selected:
   p=OUT/'data/official'/m.name
   assert p.resolve().is_relative_to((OUT/'data/official').resolve());p.parent.mkdir(parents=True,exist_ok=True)
   if not p.exists():p.write_bytes(tf.extractfile(m).read())
 save('evidence/official_provenance.json',{'at':now(),'repository':'https://github.com/FoundationAgents/AFlow','commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT/'AFlow',text=True).strip(),'download_url':url,'archive_sha256':sha(dest),'archive_bytes':dest.stat().st_size,'math_files':[m.name for m in selected],'paper':'https://arxiv.org/html/2410.10762v3','paper_split_seed':42,'paper_validation_fraction':.2,'paper_high_variance_filter':'initial template evaluated five times; high-variance validation subset used during optimization','official_code_files':{str(p.relative_to(ROOT/'AFlow')):sha(p)for p in(ROOT/'AFlow').rglob('*')if p.is_file()and '.git'not in p.parts}})
 print({'archive_bytes':dest.stat().st_size,'math_files':[m.name for m in selected]})
if __name__=='__main__':main()
