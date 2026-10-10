from common import *

def main():
 old=read(OUT/'evidence/protected_previous_snapshot.json');verified=[];allowed=[];bad=[]
 for item in old['files']:
  path=ROOT/item['path']
  if item['path']=='指引.txt':allowed.append({'path':item['path'],'previous_sha256':item['sha256'],'current_sha256':sha(path),'reason':'User supplied this next-stage guide; copied to USER_GUIDE.txt'});continue
  if not path.exists() or sha(path)!=item['sha256']:bad.append(item['path'])
  else:verified.append(item['path'])
 result={'at':now(),'reference_commit':REF,'previous_snapshot_files':old['file_count'],'protected_verified_count':len(verified),'authorized_guide_transition':allowed,'unexpected_changes':bad,'previous_experiments_rerun':False}
 save('evidence/historical_hash_verification.json',result);assert not bad,bad;print(result)
if __name__=='__main__':main()
