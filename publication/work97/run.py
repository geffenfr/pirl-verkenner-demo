"""Exact-byte Work97 publication preparation and HTTPS verification. No product build."""
from pathlib import Path
import base64,hashlib,importlib.util,json,os,subprocess,sys,traceback,urllib.request,uuid,zlib
ROOT=Path(__file__).resolve().parents[2];TASK=ROOT/'publication/work97';OUT=ROOT/'work97-evidence'
API='https://api.github.com/repos/geffenfr/pirl-verkenner-demo'
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def github(path,method='GET',body=None):
 headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
 data=None if body is None else json.dumps(body).encode()
 if data is not None:headers['Content-Type']='application/json'
 request=urllib.request.Request(API+path,data=data,headers=headers,method=method)
 with urllib.request.urlopen(request,timeout=180) as response:
  data=response.read();return json.loads(data) if data else {'httpStatus':response.status}
def offered(url):
 request=urllib.request.Request(url,headers={'Cache-Control':'no-cache, no-store, max-age=0','Pragma':'no-cache','Accept-Encoding':'identity'})
 with urllib.request.urlopen(request,timeout=90) as response:
  b=response.read();return b,{'requestedUrl':url,'responseUrl':response.geturl(),'status':response.status,'bytes':len(b),'sha256':sha(b),'headers':dict(response.headers),'cache':'fresh urllib request; identity encoding; no local response cache'}
def main():
 OUT.mkdir(exist_ok=False);cfg=json.loads((TASK/'config.json').read_bytes())
 receipt={'status':'FAIL','work':'97','regie':'109','baselineId':cfg['baselineId'],'phase':cfg['phase'],
          'preparationCommit':os.environ.get('GITHUB_SHA'),'runId':os.environ.get('GITHUB_RUN_ID'),'attempt':os.environ.get('GITHUB_RUN_ATTEMPT'),
          'mainWrittenByThisJob':False,'productBytesModified':False,'physicalIphoneSessions':0,'independentRegieClosure':'PENDING'}
 try:
  assert os.environ['GITHUB_REPOSITORY']==cfg['publicRepository'] and os.environ['GITHUB_REF']=='refs/heads/'+cfg['preparationBranch']
  expected_commit=cfg['previousCommit'] if cfg['phase']=='pre' else cfg['publicCommit']
  head=github('/git/ref/heads/main')['object']['sha'];assert head==expected_commit,'PUBLIC_MAIN_CONFLICT_STOP'
  receipt['publicCommitObserved']=head
  expected_sha=cfg['previousHtmlSha256'] if cfg['phase']=='pre' else cfg['targetHtmlSha256']
  expected_bytes=cfg['previousHtmlBytes'] if cfg['phase']=='pre' else cfg['targetHtmlBytes']
  responses=[]
  for url in [cfg['siteUrl'],cfg['siteUrl']+'?work97_verify='+uuid.uuid4().hex]:
   b,r=offered(url);responses.append(r);save(OUT/'HTTP_RESPONSES.json',responses)
   assert r['status']==200 and r['responseUrl'].split('?')[0]==cfg['siteUrl'] and sha(b)==expected_sha and len(b)==expected_bytes,'ACTUAL_SITE_BYTES_DIFFER_STOP'
  (OUT/('BEFORE_SERVED_index.html' if cfg['phase']=='pre' else 'AFTER_SERVED_index.html')).write_bytes(b)
  receipt['httpResponses']=responses
  if cfg['phase']=='pre':
   old=(ROOT/'index.html').read_bytes();assert sha(old)==cfg['previousHtmlSha256'] and len(old)==cfg['previousHtmlBytes']
   transport=(TASK/'exact-html-transport.zlib.base64').read_bytes();assert sha(transport)==cfg['transportSha256']
   delta=json.loads(zlib.decompress(base64.b64decode(transport)));assert delta['baseSha256']==sha(old) and delta['targetSha256']==cfg['targetHtmlSha256']
   target=b''.join(old[o['copy'][0]:o['copy'][0]+o['copy'][1]] if 'copy' in o else base64.b64decode(o['insert']) for o in delta['ops'])
   assert sha(target)==cfg['targetHtmlSha256'] and len(target)==cfg['targetHtmlBytes'],'FROZEN_TARGET_IDENTITY_STOP'
   git_sha=hashlib.sha1(b'blob '+str(len(target)).encode()+b'\0'+target).hexdigest();assert git_sha==cfg['targetGitBlobSha']
   assert github('/git/ref/heads/main')['object']['sha']==cfg['previousCommit'],'PARALLEL_MAIN_CHANGE_STOP'
   blob=github('/git/blobs','POST',{'content':base64.b64encode(target).decode(),'encoding':'base64'})
   assert blob['sha']==git_sha,'UPLOADED_BLOB_IDENTITY_STOP'
   assert github('/git/ref/heads/main')['object']['sha']==cfg['previousCommit'],'PARALLEL_MAIN_CHANGE_STOP'
   receipt.update(status='PREFLIGHT_PASS_MAIN_UNCHANGED',targetBlobSha=git_sha,targetSha256=sha(target),targetBytes=len(target),transport='Lossless byte transport only; target verified against frozen baseline; no product edits')
  else:
   sums,response=offered(cfg['siteUrl']+'SHA256SUMS?work97_verify='+uuid.uuid4().hex)
   assert sums.decode()==cfg['targetHtmlSha256']+'  index.html\n','SERVED_CHECKSUM_METADATA_MISMATCH_STOP'
   receipt['checksumHttpResponse']=response
   spec=importlib.util.spec_from_file_location('hosted',TASK/'live_browser.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
   receipt['hostedBrowser']=module.probe(cfg['siteUrl'],OUT/'browser',cfg['targetHtmlSha256'])
   assert github('/git/ref/heads/main')['object']['sha']==cfg['publicCommit'],'POSTCHECK_MAIN_CHANGED_STOP'
   # Remove only this isolated preparation branch, after checking its exact HEAD.
   assert github('/git/ref/heads/'+cfg['preparationBranch'])['object']['sha']==os.environ['GITHUB_SHA'],'PREPARATION_BRANCH_CHANGED_NO_DELETE'
   deleted=github('/git/refs/heads/'+cfg['preparationBranch'],'DELETE');assert deleted['httpStatus']==204
   receipt.update(status='WORK97_EXACT_BASELINE_HOSTED_VERIFICATION_PASS',publicationObserved=True,preparationBranchDeleted=True)
 except Exception as e:receipt.update(blocker=str(e),traceback=traceback.format_exc())
 save(OUT/'EXECUTION_RECEIPT.json',receipt);print(json.dumps(receipt),flush=True)
 return 0 if receipt['status'] in ['PREFLIGHT_PASS_MAIN_UNCHANGED','WORK97_EXACT_BASELINE_HOSTED_VERIFICATION_PASS'] else 1
if __name__=='__main__':sys.exit(main())
