from pathlib import Path
import numpy as np,pandas as pd
R=Path(__file__).resolve().parent
p=pd.read_csv(R/'inputs/confirmatory_paired_minimal.csv')
assert len(p)==10000 and not p.duplicated(['model_label','item_id','prompt_id','order_id']).any()
classes=['correct_to_correct','correct_to_incorrect','incorrect_to_correct','same_incorrect','different_incorrect'];out=[];summary=[];itemrows=[]
for model,g in p.groupby('model_label',sort=False):
 good=g.groupby('item_id').valid_output.agg(['sum','size']);ids=good[(good['sum']==4)&(good['size']==4)].index
 assert len(ids)=={'Gemini 3.6 Flash':485,'GPT-5.6 Terra':489}.get(model,500)
 g=g[g.item_id.isin(ids)].copy()
 for kind,held in [('order','P0_original'),('order','P1_probability'),('prompt','O0_original'),('prompt','O1_permuted')]:
  if kind=='order':
   sub=g[g.prompt_id==held];levels=sorted(sub.order_id.unique());a=sub[sub.order_id==levels[0]].set_index('item_id');b=sub[sub.order_id==levels[1]].set_index('item_id')
  else:
   sub=g[g.order_id==held];levels=sorted(sub.prompt_id.unique());a=sub[sub.prompt_id==levels[0]].set_index('item_id');b=sub[sub.prompt_id==levels[1]].set_index('item_id')
  assert len(a)==len(ids),(model,kind,held,g.prompt_id.unique(),g.order_id.unique())
  a=a.sort_index();b=b.loc[a.index];ya=a.correct.to_numpy(int);yb=b.correct.to_numpy(int);pa=a.confidence.to_numpy(float);pb=b.confidence.to_numpy(float);changed=(a.canonical_answer.to_numpy()!=b.canonical_answer.to_numpy());n=len(a)
  cls=np.select([(ya==1)&(yb==1),(ya==1)&(yb==0),(ya==0)&(yb==1),(ya==0)&(yb==0)&(~changed)],[0,1,2,3],default=4)
  assert np.all(changed==(np.isin(cls,[1,2,4])))
  q1=np.clip(pa,1e-6,1-1e-6);q2=np.clip(pb,1e-6,1-1e-6)
  db=(yb-pb)**2-(ya-pa)**2;dl=-(yb*np.log(q2)+(1-yb)*np.log(1-q2))+(ya*np.log(q1)+(1-ya)*np.log(1-q1));dc=pb-pa
  indicators=np.eye(5)[cls];mat=np.c_[indicators,indicators*db[:,None],indicators*dl[:,None]];point=mat.mean(axis=0)
  assert abs(point[5:10].sum()-db.mean())<1e-12 and abs(point[10:].sum()-dl.mean())<1e-12
  assert abs((point[2]-point[1])-(yb-ya).mean())<1e-12
  rng=np.random.default_rng(20260829);draw=np.array([mat[rng.integers(0,n,n)].mean(axis=0) for _ in range(2000)]);lo,hi=np.quantile(draw,[.025,.975],axis=0)
  for k,name in enumerate(classes):
   mask=cls==k
   out.append(dict(model=model,contrast=kind,held_condition=held,n_complete=n,transition=name,count=int(mask.sum()),rate=point[k],rate_ci_low=lo[k],rate_ci_high=hi[k],mean_confidence_change_within_class=dc[mask].mean() if mask.any() else np.nan,brier_contribution=point[5+k],brier_ci_low=lo[5+k],brier_ci_high=hi[5+k],log_loss_contribution=point[10+k],log_loss_ci_low=lo[10+k],log_loss_ci_high=hi[10+k]))
  summary.append(dict(model=model,contrast=kind,held_condition=held,n_complete=n,answer_change=changed.mean(),net_accuracy_change=(yb-ya).mean(),different_incorrect_rate=point[4],brier_delta=db.mean(),log_loss_delta=dl.mean()))
  itemrows.extend(dict(model=model,item_id=i,contrast=kind,held_condition=held,transition=classes[c]) for i,c in zip(a.index,cls))
s=pd.DataFrame(summary)
assert abs(s[(s.model=='GPT-OSS-20B')&(s.contrast=='order')&(s.held_condition=='P0_original')].answer_change.iloc[0]-.41)<1e-12
pd.DataFrame(out).to_csv(R/'supplements/Table_S18_transition_decomposition.csv',index=False);s.to_csv(R/'results/transition_totals.csv',index=False);pd.DataFrame(itemrows).to_csv(R/'results/transition_item_assignments.csv',index=False)
print('Reconstructed 100 transition-class rows; accounting identities passed.')
