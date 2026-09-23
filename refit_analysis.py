from pathlib import Path
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import json,hashlib,time
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from concurrent.futures import ProcessPoolExecutor
R=Path(__file__).resolve().parent;B=2000;SEED=20260916

def fit(y,p,f,w):
 s={'Native':p.copy(),'Base_rate':np.empty(len(y)),'Logistic':np.empty(len(y)),'Isotonic':np.empty(len(y))}
 q=np.clip(p,1e-6,1-1e-6);x=np.log(q/(1-q))[:,None]
 for k in np.unique(f):
  tr=(f!=k)&(w>0);te=f==k
  assert len(np.unique(y[tr]))==2
  s['Base_rate'][te]=np.average(y[tr],weights=w[tr])
  s['Isotonic'][te]=IsotonicRegression(out_of_bounds='clip').fit(p[tr],y[tr],sample_weight=w[tr]).predict(p[te])
  s['Logistic'][te]=LogisticRegression(C=1e6,solver='lbfgs',max_iter=2000).fit(x[tr],y[tr],sample_weight=w[tr]).predict_proba(x[te])[:,1]
 return s

def metrics(y,p,w):
 q=np.clip(p,1e-6,1-1e-6);bins=np.clip(np.searchsorted(np.linspace(0,1,11),p,side='left')-1,0,9)
 return {'brier':np.average((y-p)**2,weights=w),'log_loss':np.average(-(y*np.log(q)+(1-y)*np.log(1-q)),weights=w),'ece':sum(abs(np.sum(w[bins==k]*(y[bins==k]-p[bins==k]))) for k in range(10))/w.sum()}

def worker(task):
 mi,model,g=task;g=g.reset_index(drop=True);y=g.correct.to_numpy();p=g.original_confidence.to_numpy();f=g.cv_fold.to_numpy();n=len(g)
 groups=[np.flatnonzero(f==k) for k in np.unique(f)];rng=np.random.default_rng(SEED+mi)
 point=fit(y,p,f,np.ones(n))
 assert np.max(abs(point['Isotonic']-g.recalibrated_confidence.to_numpy()))<1e-12
 pointm={method:metrics(y,s,np.ones(n)) for method,s in point.items()}
 records=[]
 for b in range(B):
  ix=np.concatenate([rng.choice(ix,len(ix),replace=True) for ix in groups]);w=np.bincount(ix,minlength=n)
  fitted=fit(y,p,f,w)
  ms={method:metrics(y,s,w) for method,s in fitted.items()}
  for method in ['Native','Base_rate','Logistic','Isotonic']:
   records.append({'model':model,'replicate':b,'method':method,**ms[method]})
  if (b+1)%250==0:print(model,b+1,flush=True)
 df=pd.DataFrame(records);df.to_csv(R/'results'/f'refit_draws_{mi}.csv',index=False)
 out=[]
 for method in ['Native','Logistic','Isotonic']:
  for reference in ['Base_rate','Native']:
   if method==reference:continue
   for metric in ['brier','log_loss','ece']:
    v=df[df.method==method][metric].to_numpy()-df[df.method==reference][metric].to_numpy();lo,hi=np.quantile(v,[.025,.975])
    out.append({'model':model,'method':method,'reference':reference,'metric':metric,'estimate':pointm[method][metric]-pointm[reference][metric],'ci_low':lo,'ci_high':hi,'bootstrap_replicates':B,'folds_fixed':True})
 return out
if __name__=='__main__':
 d=pd.read_csv(R/'inputs/cell19_isotonic_cv_predictions.csv');assert len(d)==13993 and not d.duplicated(['model','item_id']).any()
 plan={'analysis':'post hoc fixed-fold refitting bootstrap','replicates':B,'seed':SEED,'procedure':'Resample question identities within each original fold. Carry one multiplicity weight per identity into every fold-specific training fit and held-out evaluation. All copies of a question remain in its original fold. Refit base rate, isotonic and logistic in every replicate. No test item appears in its calibration training folds.','scope':'Accounts for empirical sampling and calibrator refitting, conditional on frozen fold allocation, retained outputs and serving configurations. Does not model source-cluster dependence or new model generation. No multiplicity adjustment.'}
 (R/'analysis_plan.json').write_text(json.dumps(plan,indent=2))
 tasks=[(i,model,g) for i,(model,g) in enumerate(d.groupby('model',sort=False))]
 with ProcessPoolExecutor(max_workers=3) as pool:results=list(pool.map(worker,tasks))
 pd.DataFrame([r for result in results for r in result]).to_csv(R/'results/refit_loss_and_ece_comparisons.csv',index=False)
 print('COMPLETE',flush=True)
