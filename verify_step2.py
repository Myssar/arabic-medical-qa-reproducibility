from pathlib import Path
import json
import numpy as np,pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from refit_analysis import fit
R=Path(__file__).resolve().parent
d=pd.read_csv(R/'inputs/cell19_isotonic_cv_predictions.csv');r=pd.read_csv(R/'results/refit_loss_and_ece_comparisons.csv');checks=[]
assert len(r)==105 and (r.bootstrap_replicates==2000).all()
for mi,(model,g) in enumerate(d.groupby('model',sort=False)):
 y=g.correct.to_numpy();p=g.original_confidence.to_numpy();f=g.cv_fold.to_numpy();rng=np.random.default_rng(20260916+mi)
 ix=np.concatenate([rng.choice(np.flatnonzero(f==k),sum(f==k),replace=True) for k in np.unique(f)])
 w=np.bincount(ix,minlength=len(g));pred=fit(y,p,f,w);x=np.log(np.clip(p,1e-6,1-1e-6)/(1-np.clip(p,1e-6,1-1e-6)))[:,None]
 err=0
 for k in np.unique(f):
  tr=ix[f[ix]!=k];te=f==k;assert not set(tr)&set(np.flatnonzero(te))
  ip=IsotonicRegression(out_of_bounds='clip').fit(p[tr],y[tr]).predict(p[te]);lp=LogisticRegression(C=1e6,solver='lbfgs',max_iter=2000).fit(x[tr],y[tr]).predict_proba(x[te])[:,1]
  assert np.allclose(ip,pred['Isotonic'][te],atol=1e-12)
  err=max(err,float(np.max(abs(lp-pred['Logistic'][te]))));assert err<1e-6
  assert abs(y[tr].mean()-pred['Base_rate'][te][0])<1e-12
 draws=pd.read_csv(R/'results'/f'refit_draws_{mi}.csv');assert len(draws)==8000 and not draws.duplicated(['replicate','method']).any()
 for row in r[r.model==model].itertuples():
  a=draws[draws.method==row.method].set_index('replicate')[row.metric];b=draws[draws.method==row.reference].set_index('replicate')[row.metric]
  assert np.allclose(np.quantile(a-b,[.025,.975]),[row.ci_low,row.ci_high],atol=1e-12)
 checks.append(dict(model=model,duplicate_vs_weighted_max_logistic_difference=err,interval_rows_verified=15,fold_identity_leakage=False))
s=pd.read_csv(R/'supplements/Table_S2_generation_validity.csv');assert s.retained_outputs.sum()==69703 and s.invalid_returned_outputs.sum()==315 and s.valid_answer_without_confidence.sum()==469
b=pd.read_csv(R/'supplements/Table_S5_reliability_bins.csv');assert b.n.sum()==13993
c=pd.read_csv(R/'supplements/Table_S18_transition_decomposition.csv');assert len(c)==100
for _,g in c.groupby(['model','contrast','held_condition']):assert g['count'].sum()==g.n_complete.iloc[0] and abs(g.rate.sum()-1)<1e-12
(R/'verification.json').write_text(json.dumps({'passed':True,'models':checks,'supplement_count_checks':'passed','interval_rows_verified':len(r)},indent=2));print('PASS',len(r),'intervals, 7 duplicate-versus-weighted refit comparisons; supplement accounting')
