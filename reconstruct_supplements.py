from pathlib import Path
import itertools,json,shutil
import numpy as np,pandas as pd
from scipy.stats import chi2,binomtest,norm
from sklearn.metrics import roc_auc_score
R=Path(__file__).resolve().parent;S=R/'supplements'
d=pd.read_csv(R/'inputs/primary_item_level_analysis.csv');v=d[d.primary_evaluable].copy();rec=pd.read_csv(R/'inputs/reconstructed_item_results.csv')
assert len(d)==14000 and len(v)==13993 and not d.duplicated(['model','item_id']).any()

def metrics(y,p):
 y=np.asarray(y,float);p=np.asarray(p,float);bins=np.clip(np.searchsorted(np.linspace(0,1,11),p,side='left')-1,0,9);q=np.clip(p,1e-6,1-1e-6)
 return dict(n=len(y),accuracy=y.mean(),mean_confidence=p.mean(),ece=sum(abs(np.sum(y[bins==k]-p[bins==k])) for k in range(10))/len(y),brier=np.mean((y-p)**2),log_loss=np.mean(-(y*np.log(q)+(1-y)*np.log(1-q))),auroc=roc_auc_score(y,p) if len(set(y))==2 else np.nan)
rows=[]
for a,b in itertools.combinations(sorted(v.model.unique()),2):
 x=v[v.model==a].set_index('item_id').primary_correct;y=v[v.model==b].set_index('item_id').primary_correct;i=x.index.intersection(y.index);x=x.loc[i];y=y.loc[i]
 n10=int(((x==1)&(y==0)).sum());n01=int(((x==0)&(y==1)).sum());disc=n10+n01
 if disc<25:stat=min(n10,n01);p=binomtest(n10,disc,.5).pvalue if disc else 1.;test='exact binomial'
 else:stat=(abs(n10-n01)-1)**2/disc;p=chi2.sf(stat,1);test='continuity-corrected chi-square'
 rows.append(dict(model_A=a,model_B=b,n_common=len(i),both_correct=int(((x==1)&(y==1)).sum()),A_only=n10,B_only=n01,both_wrong=int(((x==0)&(y==0)).sum()),statistic=stat,test=test,p_raw=p,p_bonferroni=min(1,p*21)))
pd.DataFrame(rows).to_csv(S/'Table_S1_mcnemar.csv',index=False)
assert sum(x['p_bonferroni']<.05 for x in rows)==19
rows=[]
for model,g in d.groupby('model',sort=False):
 rows.append(dict(model=model,intended_pairs=len(g),evaluable_pairs=int(g.primary_evaluable.sum()),zero_valid_pairs=int((g.n_valid_answers==0).sum()),retained_outputs=int(g.n_model_outputs.sum()),valid_answer_outputs=int(g.n_valid_answers.sum()),invalid_returned_outputs=int(g.n_invalid_returned_outputs.sum()),unfilled_infrastructure_slots=int(g.n_unfilled_infrastructure_slots.sum()),valid_answer_without_confidence=int((g.n_valid_answers-g.n_valid_answer_confidence).sum())))
pd.DataFrame(rows).to_csv(S/'Table_S2_generation_validity.csv',index=False)
for num,columns in [(3,['curriculum_level']),(4,['medical_specialty','umbrella_specialty'])]:
 rows=[]
 for col in columns:
  for (model,level),g in v.groupby(['model',col],dropna=False):rows.append(dict(model=model,grouping=col,stratum=level,**metrics(g.primary_correct,g.primary_verbalized_confidence)))
 pd.DataFrame(rows).to_csv(S/f'Table_S{num}_subgroup_calibration.csv',index=False)
rows=[]
for model,g in v.groupby('model',sort=False):
 y=g.primary_correct.to_numpy();p=g.primary_verbalized_confidence.to_numpy();bins=np.clip(np.searchsorted(np.linspace(0,1,11),p,side='left')-1,0,9)
 for k in range(10):
  mask=bins==k;rows.append(dict(model=model,bin=k,lower=k/10,upper=(k+1)/10,lower_inclusive=k==0,upper_inclusive=True,n=int(mask.sum()),accuracy=y[mask].mean() if mask.any() else np.nan,mean_confidence=p[mask].mean() if mask.any() else np.nan))
pd.DataFrame(rows).to_csv(S/'Table_S5_reliability_bins.csv',index=False)
shutil.copyfile(R/'inputs/corrected_transport_per_stratum.csv',S/'Table_S6_transport_per_stratum.csv')
rows=[]
j=v.merge(rec[['model','item_id','first_valid_answer_confidence_correct','first_valid_answer_confidence_confidence']],on=['model','item_id'],validate='one_to_one')
assert len(j)==13993 and not j.first_valid_answer_confidence_confidence.isna().any()
for model,g in j.groupby('model',sort=False):
 for method,y,p in [('first_valid_answer_and_confidence',g.first_valid_answer_confidence_correct,g.first_valid_answer_confidence_confidence),('ensemble',g.primary_correct,g.primary_verbalized_confidence)]:rows.append(dict(model=model,method=method,**metrics(y,p)))
pd.DataFrame(rows).to_csv(S/'Table_S7_first_generation.csv',index=False)
rows=[]
for mi,(model,g) in enumerate(v.groupby('model',sort=False)):
 tie=g.top_vote_tie.to_numpy(bool);y=g.primary_correct.to_numpy();expect=[];rng=np.random.default_rng(20260824+mi)
 for row in g.itertuples():
  votes=json.loads(row.vote_distribution);choices=[key for key,val in votes.items() if val==max(votes.values())]
  expect.append((1/len(choices)) if row.gold_answer in choices else 0.)
 # Analytical expectation avoids dependence of a finite Monte Carlo mean on row traversal order.
 probability=np.array(expect);sims=np.array([rng.binomial(1,probability).mean() for _ in range(500)])
 rows.append(dict(model=model,n=len(g),ties=int(tie.sum()),tie_rate=tie.mean(),canonical_accuracy=y.mean(),random_tie_expected_accuracy=probability.mean(),random_tie_500_repetition_mean=sims.mean(),random_tie_500_repetition_sd=sims.std(ddof=1),ties_as_errors_accuracy=np.where(tie,0,y).mean(),ties_as_abstention_accuracy=y[~tie].mean(),note='New reconstruction; exact random expectation and explicitly seeded Monte Carlo. Historical finite Monte Carlo mean may differ.'))
pd.DataFrame(rows).to_csv(S/'Table_S8_tie_handling.csv',index=False)

def riskcurve(y,p):
 order=np.argsort(-p,kind='stable');p=p[order];y=y[order];starts=np.r_[0,np.flatnonzero(np.diff(p)!=0)+1];count=np.diff(np.r_[starts,len(y)]);errors=np.add.reduceat(1-y,starts)/count
 rc=np.cumsum(np.repeat(errors,count))/np.arange(1,len(y)+1);oracle=np.cumsum(1-np.sort(y)[::-1])/np.arange(1,len(y)+1)
 return np.r_[rc.mean(),oracle.mean(),rc.mean()-oracle.mean(),[rc[max(1,round(len(y)*c))-1] for c in [.9,.75,.5,.25]]]
rows=[]
for model,g in v.groupby('model',sort=False):
 y=g.primary_correct.to_numpy();p=g.primary_verbalized_confidence.to_numpy();point=riskcurve(y,p);rng=np.random.default_rng(20260814)
 draws=[]
 for b in range(2000):
  ix=rng.integers(0,len(y),len(y));draws.append(riskcurve(y[ix],p[ix]))
 lo,hi=np.quantile(draws,[.025,.975],axis=0)
 for k,name in enumerate(['aurc','oracle_aurc','excess_aurc','risk90','risk75','risk50','risk25']):rows.append(dict(model=model,metric=name,estimate=point[k],ci_low=lo[k],ci_high=hi[k],bootstrap_replicates=2000,seed=20260814,n=len(g),fixed_coverage_rule='round(n*coverage) retained ranks with exchangeable ties'))
pd.DataFrame(rows).to_csv(S/'Table_S9_selective_risk.csv',index=False)
e=pd.read_csv(R/'inputs/confirmatory_factorial_effects.csv');e=e[(e.metric.isin(['accuracy','ece']))].copy();e['bootstrap_se_approx']=(e.ci_high-e.ci_low)/(2*norm.ppf(.975));e['mde80_alpha05']=e.bootstrap_se_approx*(norm.ppf(.975)+norm.ppf(.8));e['mde80_alpha01']=e.bootstrap_se_approx*(norm.ppf(.995)+norm.ppf(.8));e['interpretation']='Retrospective normal approximation from interval width, not prospective power or equivalence evidence';e.to_csv(S/'Table_S17_retrospective_precision.csv',index=False)
print('S1-S9 and S17 reconstructed',flush=True)
