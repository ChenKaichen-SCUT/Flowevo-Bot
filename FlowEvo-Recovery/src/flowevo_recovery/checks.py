"""Bounded public checks, never hidden-test or gold-based diagnosis."""
import ast,re,subprocess,tempfile,os,sys,json,resource
from pathlib import Path
from flowevo_bot.v2.evaluator import extract
from flowevo_bot.rmmd.macros import fragments
from flowevo_bot.compositional_v4.expression import parse_expression,exact_eval,ScopeError

def extract_code(text):
 blocks=re.findall(r'```(?:python|py)?\s*\n(.*?)```',text,re.S|re.I)
 # Match the native first-code-block policy; parser failures are reported.
 return blocks[0].strip() if blocks else text.strip()

def run_tests(code,tests,setup=''):
 try:ast.parse(code)
 except SyntaxError as e:return {'compile_ok':False,'passed':False,'evidence':[{'kind':'syntax','line':e.lineno,'message':e.msg}]}
 if len(code)>50000:return {'compile_ok':True,'passed':False,'environment_issue':True,'evidence':[{'kind':'code_size_limit'}]}
 forbidden={'os','sys','subprocess','socket','pathlib','ctypes','multiprocessing','resource','importlib','inspect','builtins'}
 for n in ast.walk(ast.parse(code)):
  if isinstance(n,(ast.Import,ast.ImportFrom)):
   names=[a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else [(n.module or '').split('.')[0]]
   if set(names)&forbidden:return {'compile_ok':True,'passed':False,'environment_issue':True,'evidence':[{'kind':'unsupported_import','modules':names}]}
 harness='''import math,cmath,itertools,functools,collections,re,heapq,bisect,statistics,decimal,fractions,operator,string,random,datetime,array,typing,copy,json,sys,resource,ctypes,errno,os
resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456))
resource.setrlimit(resource.RLIMIT_CPU,(2,2))
resource.setrlimit(resource.RLIMIT_FSIZE,(1048576,1048576))
payload=json.loads(sys.stdin.read())
# Deny filesystem opens, networking, process creation after common stdlib preload.
lib=ctypes.CDLL('libseccomp.so.2')
lib.seccomp_init.restype=ctypes.c_void_p
lib.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint]
lib.seccomp_load.argtypes=[ctypes.c_void_p]
lib.seccomp_release.argtypes=[ctypes.c_void_p]
ctx=lib.seccomp_init(0x7fff0000)
assert ctx
for name in [b'open',b'openat',b'openat2',b'socket',b'connect',b'fork',b'vfork',b'clone',b'clone3',b'execve',b'execveat']:
 num=lib.seccomp_syscall_resolve_name(name)
 if num>=0: assert lib.seccomp_rule_add(ctx,0x50000|errno.EPERM,num,0)==0
assert lib.seccomp_load(ctx)==0
lib.seccomp_release(ctx)
scope={'__name__':'candidate'}
results=[]
try:
 exec(payload['setup'],scope,scope)
 exec(payload['code'],scope,scope)
 for i,test in enumerate(payload['tests']):
  try:
   exec(test,scope,scope);results.append({'index':i,'passed':True})
  except Exception as e:results.append({'index':i,'passed':False,'kind':type(e).__name__,'message':str(e)[:300],'test':test})
 print('__RECOVERY__'+json.dumps({'passed':all(r['passed'] for r in results) and bool(results),'evidence':results}))
except Exception as e:
 print('__RECOVERY__'+json.dumps({'passed':False,'evidence':[{'kind':type(e).__name__,'message':str(e)[:300]}]}))
'''
 def limits():
  os.setsid()
  if os.geteuid()==0:os.setgroups([]);os.setgid(65534);os.setuid(65534)
 with tempfile.TemporaryDirectory(prefix='recovery_') as temp:
  os.chmod(temp,0o755)
  try:
   r=subprocess.run(['/usr/bin/python3','-I','-c',harness],input=json.dumps({'code':code,'tests':tests,'setup':setup}),capture_output=True,text=True,cwd=temp,env={'PATH':'/usr/bin:/bin','OMP_NUM_THREADS':'1'},timeout=4,preexec_fn=limits)
   markers=[l[12:] for l in r.stdout.splitlines() if l.startswith('__RECOVERY__')]
   if not markers:return {'compile_ok':True,'passed':False,'evidence':[{'kind':'runtime_or_sandbox','returncode':r.returncode,'stderr':r.stderr[-500:]}]}
   return {'compile_ok':True,**json.loads(markers[-1])}
  except subprocess.TimeoutExpired:return {'compile_ok':True,'passed':False,'evidence':[{'kind':'timeout','limit_seconds':4}]}

def features(state):
 f={'domain':state.task.domain,'truncated':state.truncated,'missing_final':False,'local_contradiction':False,
    'compile_failed':False,'public_failed':False,'environment_issue':False,'evidence':[]}
 if state.task.domain=='code':
  check=run_tests(extract_code(state.solution),state.task.public_tests,state.task.setup)
  f.update(compile_failed=not check['compile_ok'],public_failed=not check['passed'],environment_issue=check.get('environment_issue',False),evidence=check['evidence'])
 else:
  ans,status=extract(state.solution);f['missing_final']=not bool(ans);f['final_status']=status
  for fragment in fragments(state.solution)[:64]:
   text=fragment['text']
   if text.count('=')!=1:continue
   try:
    a,b=(parse_expression(t) for t in text.split('='));x,y=exact_eval(a),exact_eval(b)
    if x!=y:f['evidence'].append({'kind':'exact_integer_contradiction','step_id':fragment['step_id'],'text':text,'left':x,'right':y})
   except (ScopeError,ValueError,OverflowError):pass
  f['local_contradiction']=bool(f['evidence'])
 return f

def feature_key(f):
 return '|'.join([f['domain']]+[k for k in ('truncated','missing_final','local_contradiction','compile_failed','public_failed','environment_issue') if f[k]])
