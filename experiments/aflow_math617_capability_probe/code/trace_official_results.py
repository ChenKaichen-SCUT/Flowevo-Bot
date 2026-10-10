from common import *
import requests,tarfile,html.parser
class Form(html.parser.HTMLParser):
 def __init__(self):super().__init__();self.params={};self.action=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='form' and a.get('id')=='download-form':self.action=a['action']
  if tag=='input' and a.get('type')=='hidden':self.params[a['name']]=a['value']
def main():
 p=OUT/'evidence/official_aflow_results.tar.gz'
 if p.read_bytes()[:2]!=b'\x1f\x8b':
  form=Form();form.feed(p.read_text());assert form.action.startswith('https://drive.usercontent.google.com/')
  save('evidence/result_download_confirmation.json',{'action':form.action,'file_id':form.params['id'],'archive_advertised_size':'49M','automatically_download_public_author_archive':True})
  r=requests.get(form.action,params=form.params,stream=True,timeout=(30,180));r.raise_for_status();tmp=p.with_suffix('.download');n=0
  with tmp.open('wb')as f:
   for block in r.iter_content(1024*1024):
    n+=len(block);assert n<300*1024**2;f.write(block)
  assert tmp.read_bytes()[:2]==b'\x1f\x8b';tmp.replace(p)
 with tarfile.open(p,'r:gz')as tf:
  inv=[{'name':m.name,'size':m.size}for m in tf.getmembers()if m.isfile()];save('evidence/official_results_inventory.json',inv)
  selected=[m for m in tf.getmembers()if m.isfile()and '/math/'in m.name.lower()]
  for m in selected:
   dest=OUT/'evidence/official_results'/m.name;assert dest.resolve().is_relative_to((OUT/'evidence/official_results').resolve());dest.parent.mkdir(parents=True,exist_ok=True)
   if not dest.exists():dest.write_bytes(tf.extractfile(m).read())
 save('evidence/official_results_provenance.json',{'at':now(),'sha256':sha(p),'bytes':p.stat().st_size,'math_files':len(selected),'math_bytes':sum(m.size for m in selected)})
 print({'all_files':len(inv),'math_files':len(selected),'math_bytes':sum(m.size for m in selected)})
if __name__=='__main__':main()
