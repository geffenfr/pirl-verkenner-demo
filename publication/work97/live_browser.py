from pathlib import Path
import json,hashlib,traceback
from playwright.sync_api import sync_playwright
def probe(url,out,expected_sha):
 out.mkdir(parents=True,exist_ok=True);checks=[];views=[];errors=[];requests=[];hosted_requests=[];report={'status':'FAIL','candidateSha256':expected_sha,'physicalIphoneSessions':0}
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':390,'height':844},accept_downloads=True,service_workers='block',extra_http_headers={'Cache-Control':'no-cache','Pragma':'no-cache'});page=ctx.new_page();page.set_default_timeout(35000);page.on('pageerror',lambda e:errors.append(str(e)));page.route('**/*',lambda route:route.continue_());page.on('request',lambda r:(hosted_requests.append({'url':r.url,'resourceType':r.resource_type}),requests.append(r.url) if not (r.url.split('?')[0]==url or r.url=='https://geffenfr.github.io/favicon.ico') else None) if r.url.startswith(('http:','https:')) else None)
  page.add_init_script('''(()=>{window.__fileReads=[];for(const k of ['text','arrayBuffer','slice','stream']){const old=File.prototype[k];if(typeof old==='function')File.prototype[k]=function(...a){if(this.name?.startsWith('SENTINEL'))window.__fileReads.push(k);return old.apply(this,a);};}for(const k of ['readAsText','readAsArrayBuffer','readAsBinaryString','readAsDataURL']){const old=FileReader.prototype[k];if(old)FileReader.prototype[k]=function(f,...a){if(f?.name?.startsWith('SENTINEL'))window.__fileReads.push(k);return old.call(this,f,...a);};}})()''')
  try:
   def boot(target):
    response=page.goto(target);assert response.status==200 and not response.from_service_worker
    body=response.body();assert hashlib.sha256(body).hexdigest()==expected_sha
    page.wait_for_function("window.__PIRL_CLEAN_APP__?.version==='PRO-004-v2.8.0'",timeout=60000)
   def go(route):
    page.locator('#v18MenuBtn').click()
    for d in page.locator('#v18Drawer details').all():
     if d.get_attribute('open') is None and d.locator(':scope>summary').is_visible():d.locator(':scope>summary').click()
    page.locator('[data-v19-node="'+route+'"]').click();page.wait_for_function('(r)=>window.__PIRL_CLEAN_APP__.router.getCurrentRoute()===r',arg=route)
   def absent():
    assert page.locator('input[type=file]').count()==0
    state=page.evaluate("(()=>{const a=window.__PIRL_CLEAN_APP__;return {runtime:['activateRaw','activateSource','restoreExternal'].filter(k=>typeof a.runtimeStore[k]==='function'),load:['importFile','importSourceProfile','importMeasurementContract'].filter(k=>typeof a.loadExplorerController[k]==='function'),story:typeof a.storybookController.importStory,large:!!window.__PIRL_LS002__,probe:!!window.__PIRL_SOURCE_PROBE__}})()")
    assert not state['runtime'] and not state['load'] and state['story']=='undefined' and not state['large'] and not state['probe'],state
   def negative_files(route):
    go(route);absent();before=page.evaluate("window.__PIRL_CLEAN_APP__.runtimeStore.snapshot().generation")
    # Synthetic retired markup is a test probe for surviving delegated/capture handlers, not a shipped UI route.
    page.evaluate('''()=>{const root=document.querySelector('#main-content'),f=new File(['{"SENTINEL":"DO_NOT_READ"}'],'SENTINEL.json',{type:'application/json'}),dt=new DataTransfer();dt.items.add(f);for(const attr of ['data-load-file','data-measurement-profile-file','data-measurement-contract-file','data-story-import','id']){const i=document.createElement('input');i.type='file';i.setAttribute(attr,attr==='id'?'evidence-readback':'');i.files=dt.files;root.append(i);i.dispatchEvent(new Event('change',{bubbles:true}));i.remove();}root.dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:dt}));root.dispatchEvent(new ClipboardEvent('paste',{bubbles:true,cancelable:true,clipboardData:dt}));}''')
    page.wait_for_timeout(100);assert page.evaluate('window.__fileReads')==[];assert page.evaluate("window.__PIRL_CLEAN_APP__.runtimeStore.snapshot().generation")==before;absent()
   boot(url+'?profile=research&import=https://example.invalid/SENTINEL.json&source=external');absent();assert page.evaluate('window.__PIRL_CLEAN_APP__.runtimeStore.snapshot().model') is None
   for route in ['explore.load','storybooks','validation.export']:negative_files(route)
   checks.append({'name':'No supported file APIs, parser/large-loader globals or real file inputs; retired-handler/drop/paste probes do not read synthetic sentinel bytes; query flags do not enable research import','sentinelReads':page.evaluate('window.__fileReads')})
   for width in [320,390]:
    page.set_viewport_size({'width':width,'height':844})
    for lang in ['nl','en']:
     page.locator('#languageSwitch').select_option(lang)
     assert ('Research edition' not in page.title() and 'Onderzoeksversie' not in page.title()) and '2.8.0' in page.title() and ('30 October 2026' if lang=='en' else '30 oktober 2026') in page.title()
     for route in ['explore.load','storybooks','releases']:
      go(route);absent();body=page.locator('#main-content').inner_text();assert ('Public demo' if lang=='en' else 'Publieke demoversie') in (body if route!='storybooks' else page.locator('body').inner_text()) if route!='storybooks' else True
      if route=='explore.load':assert ('Opening your own files is not available' if lang=='en' else 'Het openen van eigen bestanden is niet beschikbaar') in body
      if route=='releases':assert ('file read-back have been removed' if lang=='en' else 'bestandsherlezing zijn verwijderd') in body
      scan=page.locator('#main-content').evaluate('''root=>{let w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT),n,count=0,bad=[];while(n=w.nextNode()){const e=n.parentElement;if(!n.textContent.trim()||!e.checkVisibility({checkVisibilityCSS:true}))continue;let h=e.closest('details:not([open])');if(h&&!h.querySelector(':scope>summary')?.contains(e))continue;const r=document.createRange();r.selectNodeContents(n);for(const b of r.getClientRects()){if(!b.width||!b.height)continue;count++;if(b.left< -2||b.right>innerWidth+2)bad.push(n.textContent.slice(0,70));let a=e;while(a&&a!==document.body){const st=getComputedStyle(a),q=a.getBoundingClientRect();if(/hidden|clip/.test(st.overflowX)&&(b.left<q.left-2||b.right>q.right+2))bad.push('ancestor '+n.textContent.slice(0,60));if(/hidden|clip/.test(st.overflowY)&&(b.top<q.top-2||b.bottom>q.bottom+2))bad.push('vertical '+n.textContent.slice(0,60));a=a.parentElement;}}}return {textRects:count,clipped:bad}}''')
      assert scan['textRects'] and not scan['clipped'],(route,lang,width,scan);views.append({'route':route,'language':lang,'width':width,'text':body,**scan})
   checks.append({'name':'Bilingual public scope, correct title/date, privacy/no-import copy, release history and mobile changed screens','combinations':len(views)})
   go('explore.load');page.locator('[data-load-builtin="novaserve"]').click();page.wait_for_function("window.__PIRL_CLEAN_APP__.runtimeStore.snapshot().source?.id==='novaserve' && window.__PIRL_CLEAN_APP__.runtimeStore.snapshot().model?.cases?.length>0",timeout=120000);checks.append({'name':'Normal hosted NovaServe built-in activation','snapshot':page.evaluate("(()=>{const s=window.__PIRL_CLEAN_APP__.runtimeStore.snapshot();return {id:s.source.id,kind:s.source.kind,cases:s.model.cases.length,events:s.model.events.length}})()")})
   go('explore.load');page.locator('[data-load-builtin="bank"]').click();page.wait_for_function("window.__PIRL_CLEAN_APP__.runtimeStore.snapshot().model?.manifest?.case_scenario?.version==='D04-C04-REGIE99-2'",timeout=120000);go('analysis.ip.overview');page.locator('[data-content-action="anchor"]').click();page.locator('[data-content-action="open"]').click();page.locator('[data-content-story]').wait_for();assert page.locator('[data-content-document]').count()==4
   for did,count in [('R4-DEC-ASSESS01',9),('DEC-001894-D18-02',10),('DEC-001893-D18-02',4)]:
    page.locator('[data-content-position]').select_option(did);page.wait_for_function('(d)=>window.__PIRL_CLEAN_APP__.contextStore.getState().decision?.id===d',arg=did);assert page.locator('[data-content-document]').count()==count
   go('validation.export');page.locator('#evidence-export').click()
   with page.expect_download() as d:page.locator('#evidence-download').click()
   f=out/d.value.suggested_filename;d.value.save_as(f);data=json.loads(f.read_text());assert data['generator']['runtime']=='PRO-004-v2.8.0' and data['caseScenario']['version']=='D04-C04-REGIE99-2';absent();checks.append({'name':'Actual public results download verified in external test tool; no app read-back claim','bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'runtime':data['generator']['runtime']})
   go('storybooks');form=page.locator('[data-story-form="create"]');form.locator('xpath=ancestor::details[1]').locator(':scope>summary').click();form.locator('[name="title"]').fill('Synthetic public test');form.locator('button[type="submit"]').click();form=page.locator('[data-story-form="chapter"]');form.locator('[name="title"]').fill('Chapter');form.locator('button[type="submit"]').click();go('analysis.ip.reconstruct');page.locator('[data-story-action="capture"]').click();form=page.locator('[data-story-form="bookmark"]');form.wait_for();form.locator('[name="title"]').fill('Case bookmark');form.locator('button[type="submit"]').click();page.locator('[data-story-action="open"]').first.click();page.wait_for_function("window.__PIRL_CLEAN_APP__.router.getCurrentRoute()==='analysis.ip.reconstruct'");assert page.evaluate("window.__PIRL_CLEAN_APP__.contextStore.getState().decision.id")=='DEC-001893-D18-02';go('storybooks')
   with page.expect_download() as d:page.locator('[data-story-action="export"]').click()
   f=out/d.value.suggested_filename;d.value.save_as(f);book=json.loads(f.read_text());assert book['chapters'][0]['bookmarks'][0]['source']['kind']=='builtin';checks.append({'name':'Normal local story creation/bookmark capture/internal open and actual story JSON export','bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
   # Seed only this new isolated browser's own synthetic storage to simulate a legacy external reference.
   book['chapters'][0]['bookmarks'][0]['source']['kind']='external';book['chapters'][0]['bookmarks'][0]['source']['id']='SYNTHETIC-OLD-EXTERNAL';raw=json.dumps([book],separators=(',',':'));page.evaluate('(s)=>localStorage.setItem("pirl.pro004.storybooks.v1",s)',raw);boot(url);go('storybooks');page.locator('[data-story-action="open"]').first.click();page.wait_for_function("window.__PIRL_CLEAN_APP__.storybookController.getViewModel().error==='STORY_SOURCE_UNAVAILABLE'");assert page.evaluate('localStorage.getItem("pirl.pro004.storybooks.v1")')==raw;assert page.evaluate('window.__PIRL_CLEAN_APP__.runtimeStore.snapshot().model') is None
   for lang in ['nl','en']:
    page.locator('#languageSwitch').select_option(lang);body=page.locator('#main-content').inner_text();assert ('unavailable in the public demo' if lang=='en' else 'niet beschikbaar in de publieke demo') in body
   checks.append({'name':'Persisted synthetic external source rejected in NL/EN without source substitution, file read or story deletion'})
   assert not errors and not requests,(errors,requests);report.update(status='PASS',checks=checks,views=views,browserVersion=browser.version,pageErrors=errors,networkRequests=requests,sentinelFileReads=page.evaluate('window.__fileReads'),physicalIphoneSessions=0,hostedRequests=hosted_requests,freshBrowserContext=True,httpCacheDisabledByRouting=True,serviceWorkersBlocked=True,siteUrl=url)
  except Exception as e:report.update(error=str(e),traceback=traceback.format_exc(),checks=checks,views=views,pageErrors=errors,networkRequests=requests);(out/'FAILURE_VISIBLE_TEXT.txt').write_text(page.locator('body').inner_text());raise
  finally:(out/'PUBLIC_BROWSER.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');browser.close()
 return report
