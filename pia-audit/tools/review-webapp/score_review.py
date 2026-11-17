"""Score the Google Forms reviewer surveys.

Download each form's response sheet as CSV (File > Download > Comma-separated values), then run:

  Part A (pharmacists):
    python score_forms.py partA --responses A1.csv A2.csv A3.csv --register sample_register.csv [--adjudication partA_adjudication.csv] [--uncertain-as-changed]

  Part B (doctors):
    python score_forms.py partB --blind B1_1.csv B1_2.csv --unblind B2_1.csv B2_2.csv --key partB_key.csv [--adjudication partB_adjudication.csv]

  Web app export (one CSV from the coordinator dashboard, used instead of the Forms CSVs):
    python score_forms.py partA --long responses_export.csv --register sample_register.csv
    python score_forms.py partB --long responses_export.csv --key partB_key.csv

Without --adjudication the script writes a *_disagreements.csv file. Fill its final_* columns
(third reviewer or recorded discussion), save it, and rerun with --adjudication.
If a rater submitted a form more than once, only their last submission is used.
"""
import argparse, re, sys
import numpy as np, pandas as pd

ID_RE = re.compile(r'^\[([RB]\d{3,4})\]')
TOKEN_RE = re.compile(r'\(([A-Z_]+)\)\s*$')


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    cats = sorted(set(a) | set(b)); po = np.mean(a == b)
    pe = sum(np.mean(a == c) * np.mean(b == c) for c in cats)
    return ((po - pe) / (1 - pe) if pe < 1 else np.nan), po


def read_forms(paths, kind):
    """Return long table: rater, id, field, value (last submission per rater and form)."""
    out = []
    for p in paths:
        df = pd.read_csv(p)
        rcol = [c for c in df.columns if 'Rater code' in c]
        if not rcol:
            sys.exit(f'{p}: no rater-code column found')
        df['_rater'] = df[rcol[0]].astype(str).str.strip().str.upper()
        df = df.drop_duplicates('_rater', keep='last')
        for col in df.columns:
            m = ID_RE.match(str(col))
            if not m:
                continue
            if 'Is the benchmark key correct' in col: field = 'key_validity'
            elif 'How serious' in col: field = 'severity'
            elif 'Reason or source' in col: field = 'reason'
            else: field = 'answer'
            for r, v in zip(df['_rater'], df[col]):
                out.append((r, m.group(1), field, v))
    t = pd.DataFrame(out, columns=['rater', 'id', 'field', 'value'])
    raters = sorted(t.rater.unique())
    if len(raters) != 2:
        sys.exit(f'{kind}: expected exactly two rater codes, found {raters}. Fix the codes in the CSV and rerun.')
    return t, raters


def read_long(path, stages, kind):
    """Read the web-app export (timestamp, rater, stage, item_id, field, value); latest row wins."""
    d = pd.read_csv(path, dtype=str, encoding='utf-8-sig').sort_values('timestamp', kind='stable')
    d = d[d.stage.isin(stages)].drop_duplicates(['rater', 'stage', 'item_id', 'field'], keep='last')
    d['field'] = d.field.replace({'equivalence': 'answer'})
    t = d.rename(columns={'item_id': 'id'})[['rater', 'id', 'field', 'value']]
    raters = sorted(t.rater.unique())
    if len(raters) != 2:
        sys.exit(f'{kind}: expected exactly two raters in the export, found {raters}.')
    return t, raters


def token(v):
    if pd.isna(v): return np.nan
    if re.fullmatch(r'[A-Z_]{2,}|[A-F]', str(v).strip()): return str(v).strip()
    m = TOKEN_RE.search(str(v))
    if m: return m.group(1)
    m = re.match(r'^([A-F])\.', str(v))
    return m.group(1) if m else np.nan


def two_col(t, raters, field):
    s = t[t.field == field].copy(); s['v'] = s.value.map(token) if field != 'reason' else s.value
    w = s.pivot_table(index='id', columns='rater', values='v', aggfunc='last')
    return w.reindex(columns=raters)


def report_agreement(w, raters, label):
    both = w.dropna()
    k, po = kappa(both[raters[0]], both[raters[1]])
    print(f'\n{label}: {len(both)} items rated by both; raw agreement = {po:.3f}; Cohen kappa = {k:.3f}')
    print(pd.crosstab(both[raters[0]], both[raters[1]], margins=True))


# ------------------------------------------------------------------ Part A
def part_a(a):
    t, raters = read_long(a.long, ['A'], 'Part A') if a.long else read_forms(a.responses, 'Part A')
    w = two_col(t, raters, 'answer')
    reg = pd.read_csv(a.register).rename(columns={'review_id': 'id'})
    print(f'Raters: {raters}; items with any rating: {w.notna().any(axis=1).sum()} of {len(reg)}')
    print('Missing ratings per rater:', w.reindex(reg.id).isna().sum().to_dict())
    report_agreement(w, raters, 'Semantic equivalence (3 categories)')
    d = reg.merge(w, left_on='id', right_index=True, how='left')
    dis = d[(d[raters[0]] != d[raters[1]]) & d[raters].notna().all(axis=1)]
    if a.adjudication:
        adj = pd.read_csv(a.adjudication)[['id', 'final_label']]
        d = d.merge(adj, on='id', how='left')
    else:
        dis[['id', raters[0], raters[1]]].assign(final_label='', adjudicator='', reason='').to_csv('partA_disagreements.csv', index=False)
        print(f'\n{len(dis)} disagreements written to partA_disagreements.csv. Adjudicate them and rerun with --adjudication.')
        d['final_label'] = np.nan
    d['ref'] = np.where(d[raters[0]] == d[raters[1]], d[raters[0]], d['final_label'])
    if a.uncertain_as_changed:
        d['ref'] = d.ref.replace('UNCERTAIN', 'CHANGED')
    print('\nReference labels by stratum:')
    print(pd.crosstab(d.stratum, d.ref.fillna('UNRESOLVED'), margins=True))
    e = d[d.ref.isin(['CHANGED', 'PRESERVED'])].copy(); e['pos'] = e.ref == 'CHANGED'
    print('\nShare judged CHANGED (precision for flagged strata):')
    for s in ['R1', 'R3', 'R2_only', 'Unflagged']:
        g = e[e.stratum == s]; lo, hi = wilson(g.pos.sum(), len(g))
        lab = 'missed among unflagged' if s == 'Unflagged' else s
        print(f'  {lab:24s}: {g.pos.sum()}/{len(g)} = {g.pos.mean():.3f} (95% CI {lo:.3f}-{hi:.3f})')

    def est(x):
        wt = x.weight.values; p = x.pos.values; r1 = (x.stratum == 'R1').values
        tot = np.sum(wt * p)
        return (np.sum(wt * p * r1) / tot if tot > 0 else np.nan), tot
    rec, tot = est(e)
    rng = np.random.default_rng(20260925); bs = []
    for _ in range(5000):
        b = pd.concat([g.sample(len(g), replace=True, random_state=int(rng.integers(1e9))) for _, g in e.groupby('stratum')])
        bs.append(est(b)[0])
    lo, hi = np.nanpercentile(bs, [2.5, 97.5])
    print(f'\nEstimated questions with changed meaning among all 500: {tot:.1f}')
    print(f'Weighted recall of R1 alone: {rec:.3f} (95% bootstrap CI {lo:.3f}-{hi:.3f})')


# ------------------------------------------------------------------ Part B
def part_b(a):
    if a.long:
        tb, rb = read_long(a.long, ['B1'], 'Part B1')
        tu, ru = read_long(a.long, ['B2'], 'Part B2')
    else:
        tb, rb = read_forms(a.blind, 'Part B1')
        tu, ru = read_forms(a.unblind, 'Part B2')
    if rb != ru:
        sys.exit(f'Rater codes differ between B1 {rb} and B2 {ru}')
    raters = rb
    key = pd.read_csv(a.key).rename(columns={'survey_id': 'id'})
    blind = two_col(tb, raters, 'answer')
    kv = two_col(tu, raters, 'key_validity')
    sev = two_col(tu, raters, 'severity')
    print(f'Raters: {raters}; items: {len(key)}')
    print('Missing blind answers:', blind.reindex(key.id).isna().sum().to_dict(),
          '| missing key ratings:', kv.reindex(key.id).isna().sum().to_dict())

    k = key.set_index('id')
    print('\nBlind answers compared with the benchmark key and the model answer:')
    for r in raters:
        b = blind[r].reindex(k.index)
        for src in ['UNANIMOUS_DISAGREEMENT', 'HIGH_CONFIDENCE_ERROR']:
            m = k.source == src; bb = b[m]
            print(f'  {r} {src:24s}: agrees with key {np.mean(bb == k.benchmark_key[m]):.3f}; '
                  f'agrees with model {np.mean(bb == k.model_answer[m]):.3f}; '
                  f'MULTIPLE/NONE/CANNOT_JUDGE {bb.isin(["MULTIPLE", "NONE", "CANNOT_JUDGE"]).mean():.3f}')
    report_agreement(blind, raters, 'Blind answer (option letter or special category)')
    report_agreement(kv, raters, 'Key validity')
    report_agreement(sev, raters, 'Severity of model answer')

    d = key.merge(kv.add_prefix('key_'), left_on='id', right_index=True, how='left') \
           .merge(sev.add_prefix('sev_'), left_on='id', right_index=True, how='left')
    ka, kb, sa, sb = [f'key_{raters[0]}', f'key_{raters[1]}', f'sev_{raters[0]}', f'sev_{raters[1]}']
    if a.adjudication:
        adj = pd.read_csv(a.adjudication)[['id', 'final_key_validity', 'final_severity']]
        d = d.merge(adj, on='id', how='left')
    else:
        dis = d[(d[ka] != d[kb]) | (d[sa] != d[sb])]
        dis[['id', 'source', ka, kb, sa, sb]].assign(final_key_validity='', final_severity='', adjudicator='', reason='') \
            .to_csv('partB_disagreements.csv', index=False)
        print(f'\n{len(dis)} items with any disagreement written to partB_disagreements.csv. Adjudicate and rerun with --adjudication.')
        d['final_key_validity'] = np.nan; d['final_severity'] = np.nan
    d['key_ref'] = np.where(d[ka] == d[kb], d[ka], d.final_key_validity)
    d['sev_ref'] = np.where(d[sa] == d[sb], d[sa], d.final_severity)
    print('\nKey validity (consensus/adjudicated) by source:')
    print(pd.crosstab(d.source, d.key_ref.fillna('UNRESOLVED'), margins=True))
    for src in ['UNANIMOUS_DISAGREEMENT', 'HIGH_CONFIDENCE_ERROR']:
        g = d[(d.source == src) & d.key_ref.notna()]
        bad = g.key_ref.isin(['KEY_INCORRECT', 'MULTIPLE', 'FLAWED']).sum(); lo, hi = wilson(bad, len(g))
        print(f'  {src}: key incorrect, multiple or flawed = {bad}/{len(g)} ({bad / max(len(g), 1):.3f}; 95% CI {lo:.3f}-{hi:.3f})')
    print('\nSeverity of the model answer (consensus/adjudicated) by source:')
    print(pd.crosstab(d.source, d.sev_ref.fillna('UNRESOLVED'), margins=True))
    d.to_csv('partB_item_results.csv', index=False)
    print('\nItem-level results written to partB_item_results.csv')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='part', required=True)
    pa = sp.add_parser('partA'); pa.add_argument('--responses', nargs='+'); pa.add_argument('--long')
    pa.add_argument('--register', required=True); pa.add_argument('--adjudication')
    pa.add_argument('--uncertain-as-changed', action='store_true')
    pb = sp.add_parser('partB'); pb.add_argument('--blind', nargs='+'); pb.add_argument('--long')
    pb.add_argument('--unblind', nargs='+'); pb.add_argument('--key', required=True)
    pb.add_argument('--adjudication')
    a = ap.parse_args()
    part_a(a) if a.part == 'partA' else part_b(a)
