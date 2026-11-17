/**
 * Arabic Medical QA – reviewer web app (Google Apps Script)
 * Generated 25 September 2026.
 *
 * Part A  – pharmacists P1, P2: do option orders X and Y keep the same meaning? (150 items)
 * Part B1 – doctors D1, D2: blind answer to each question (101 items)
 * Part B2 – doctors D1, D2: key validity and severity of the model answer (unlocked only after B1 is submitted)
 *
 * SETUP: run setup() once, deploy as a web app (Execute as: Me; Who has access: Anyone),
 * then run showLinks() to get the personal links and the coordinator dashboard link.
 * Requires dataA.gs and dataB.gs in the same project. dataB.gs contains the answer key and is never sent
 * to a browser before that reviewer's B1 is submitted.
 */

const PROPS = PropertiesService.getScriptProperties();
const RATERS = { P1: 'A', P2: 'A', D1: 'B', D2: 'B' };
const VALID = {
  A:  { equivalence: ['PRESERVED', 'CHANGED', 'UNCERTAIN'], reason: 'text' },
  B1: { answer: 'letter_or_special', comment: 'text' },
  B2: { key_validity: ['KEY_CORRECT', 'KEY_INCORRECT', 'MULTIPLE', 'FLAWED', 'CANNOT_JUDGE'],
        severity: ['ACCEPTABLE', 'MINOR', 'MODERATE', 'HARMFUL', 'NA'], reason: 'text' }
};
const REQUIRED = { A: ['equivalence'], B1: ['answer'], B2: ['key_validity', 'severity'] };
const B1_SPECIAL = ['MULTIPLE', 'NONE', 'CANNOT_JUDGE'];

// ------------------------------------------------------------------ setup
function setup() {
  let ss;
  const id = PROPS.getProperty('SS_ID');
  if (id) {
    ss = SpreadsheetApp.openById(id);
  } else {
    ss = SpreadsheetApp.create('MedQA_Review_Responses');
    ss.getSheets()[0].setName('responses').appendRow(['timestamp', 'rater', 'stage', 'item_id', 'field', 'value']);
    ss.insertSheet('status').appendRow(['timestamp', 'rater', 'stage', 'event']);
    ss.insertSheet('access').appendRow(['rater', 'role', 'access_code', 'personal_link']);
    PROPS.setProperty('SS_ID', ss.getId());
  }
  if (!PROPS.getProperty('CODES')) {
    const codes = {};
    Object.keys(RATERS).forEach(function (r) { codes[r + '-' + randomString_(6)] = r; });
    PROPS.setProperty('CODES', JSON.stringify(codes));
    PROPS.setProperty('ADMIN', randomString_(24));
  }
  Logger.log('Setup complete. Responses spreadsheet: ' + ss.getUrl());
  Logger.log('Now deploy the web app (Deploy → New deployment → Web app), then run showLinks().');
}

function showLinks() {
  const url = ScriptApp.getService().getUrl();
  if (!url) throw new Error('Deploy the web app first (Deploy → New deployment → Web app), then run showLinks() again.');
  const codes = JSON.parse(PROPS.getProperty('CODES'));
  const sh = ss_().getSheetByName('access');
  sh.getRange(2, 1, Math.max(sh.getLastRow() - 1, 1), 4).clearContent();
  Object.keys(codes).forEach(function (c) {
    const r = codes[c];
    const link = url + '?c=' + encodeURIComponent(c);
    sh.appendRow([r, RATERS[r] === 'A' ? 'Pharmacist (Part A)' : 'Doctor (Part B)', c, link]);
    Logger.log(r + '  ' + link);
  });
  const admin = url + '?admin=' + PROPS.getProperty('ADMIN');
  sh.appendRow(['COORDINATOR', 'Dashboard – do not share', '', admin]);
  Logger.log('Coordinator dashboard (keep private): ' + admin);
}

// ------------------------------------------------------------------ web entry
function doGet(e) {
  const p = (e && e.parameter) || {};
  const isAdmin = !!p.admin;
  const t = HtmlService.createTemplateFromFile(isAdmin ? 'Admin' : 'Index');
  t.code = p.c || '';
  t.admin = p.admin || '';
  return t.evaluate()
    .setTitle(isAdmin ? 'لوحة المنسّق — Coordinator' : 'مراجعة الأسئلة الطبية — Question review')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

// ------------------------------------------------------------------ reviewer API
function api_start(code) {
  const rater = raterFor_(code);
  const role = RATERS[rater];
  const ev = events_(rater);
  const stages = role === 'A' ? ['A'] : ['B1', 'B2'];
  const info = {};
  stages.forEach(function (s) {
    const ans = answers_(rater, s);
    info[s] = {
      total: items_(s).length,
      answered: countComplete_(ans, s),
      submitted: !!ev[s + ':submitted'],
      locked: s === 'B2' && !ev['B1:submitted']
    };
  });
  return { rater: rater, role: role, trained: !!ev['training:done'], stages: info };
}

function api_items(code, stage) {
  const rater = raterFor_(code);
  checkStage_(rater, stage);
  const ev = events_(rater);
  if (stage === 'B2' && !ev['B1:submitted']) throw new Error('B2_LOCKED');
  const list = shuffle_(items_(stage).slice(), rater + ':' + (stage === 'B2' ? 'B1' : stage));
  let out;
  if (stage === 'A') {
    out = list.map(function (it) { return { id: it.id, q: it.q, x: it.x, y: it.y }; });
  } else if (stage === 'B1') {
    out = list.map(function (it) { return { id: it.id, q: it.q, opts: it.opts }; });   // no key, no model answer
  } else {
    const blind = answers_(rater, 'B1');
    out = list.map(function (it) {
      return { id: it.id, q: it.q, opts: it.opts, key: it.key, model: it.model,
               blind: (blind[it.id] || {}).answer || '' };
    });
  }
  return { items: out, answers: answers_(rater, stage), submitted: !!ev[stage + ':submitted'] };
}

function api_save(code, stage, itemId, field, value) {
  const rater = raterFor_(code);
  checkStage_(rater, stage);
  const ev = events_(rater);
  if (ev[stage + ':submitted']) throw new Error('ALREADY_SUBMITTED');
  if (stage === 'B2' && !ev['B1:submitted']) throw new Error('B2_LOCKED');
  const item = items_(stage).filter(function (it) { return it.id === itemId; })[0];
  if (!item) throw new Error('UNKNOWN_ITEM');
  const rule = VALID[stage][field];
  if (!rule) throw new Error('UNKNOWN_FIELD');
  value = String(value == null ? '' : value);
  if (rule === 'text') {
    value = value.slice(0, 1500);
  } else if (rule === 'letter_or_special') {
    const letters = item.opts.map(function (o) { return o[0]; });
    if (letters.indexOf(value) < 0 && B1_SPECIAL.indexOf(value) < 0) throw new Error('INVALID_VALUE');
  } else if (rule.indexOf(value) < 0) {
    throw new Error('INVALID_VALUE');
  }
  withLock_(function () {
    ss_().getSheetByName('responses').appendRow([new Date(), rater, stage, itemId, field, value]);
  });
  return { ok: true, savedAt: new Date().toISOString() };
}

function api_training(code) {
  const rater = raterFor_(code);
  logEvent_(rater, 'training', 'done');
  return true;
}

function api_submit(code, stage) {
  const rater = raterFor_(code);
  checkStage_(rater, stage);
  const ev = events_(rater);
  if (ev[stage + ':submitted']) return { ok: true, already: true };
  const ans = answers_(rater, stage);
  const missing = items_(stage).filter(function (it) {
    return REQUIRED[stage].some(function (f) { return !(ans[it.id] && ans[it.id][f]); });
  }).map(function (it) { return it.id; });
  if (missing.length) return { ok: false, missing: missing };
  logEvent_(rater, stage, 'submitted');
  return { ok: true };
}

// ------------------------------------------------------------------ coordinator API
function api_admin_status(token) {
  checkAdmin_(token);
  const codes = JSON.parse(PROPS.getProperty('CODES'));
  const rows = [];
  Object.keys(RATERS).forEach(function (r) {
    const ev = events_(r);
    const stages = RATERS[r] === 'A' ? ['A'] : ['B1', 'B2'];
    stages.forEach(function (s) {
      const ans = answers_(r, s);
      rows.push({ rater: r, stage: s, answered: countComplete_(ans, s), total: items_(s).length,
                  trained: !!ev['training:done'], submitted: ev[s + ':submitted'] || '',
                  last: lastActivity_(r, s) });
    });
  });
  return { rows: rows, sheet: ss_().getUrl(), codes: Object.keys(codes).length };
}

function api_admin_export(token) {
  checkAdmin_(token);
  const data = ss_().getSheetByName('responses').getDataRange().getValues().slice(1);
  const latest = {};
  data.forEach(function (row) {
    const k = [row[1], row[2], row[3], row[4]].join('|');
    latest[k] = row;   // rows are appended in time order, so the last one wins
  });
  const lines = ['timestamp,rater,stage,item_id,field,value'];
  Object.keys(latest).sort().forEach(function (k) {
    const r = latest[k];
    lines.push([new Date(r[0]).toISOString(), r[1], r[2], r[3], r[4], r[5]].map(csv_).join(','));
  });
  const name = 'responses_export_' + Utilities.formatDate(new Date(), 'UTC', 'yyyyMMdd_HHmm') + '.csv';
  const file = DriveApp.createFile(name, '\ufeff' + lines.join('\n'), MimeType.CSV);
  return { url: file.getUrl(), name: name, rows: lines.length - 1 };
}

// ------------------------------------------------------------------ helpers
function ss_() {
  const id = PROPS.getProperty('SS_ID');
  if (!id) throw new Error('Run setup() first.');
  return SpreadsheetApp.openById(id);
}
function raterFor_(code) {
  const codes = JSON.parse(PROPS.getProperty('CODES') || '{}');
  const r = codes[String(code || '').trim().toUpperCase()] || codes[String(code || '').trim()];
  if (!r) throw new Error('BAD_CODE');
  return r;
}
function checkAdmin_(token) {
  if (!token || token !== PROPS.getProperty('ADMIN')) throw new Error('NOT_AUTHORIZED');
}
function checkStage_(rater, stage) {
  const ok = (RATERS[rater] === 'A' && stage === 'A') || (RATERS[rater] === 'B' && (stage === 'B1' || stage === 'B2'));
  if (!ok) throw new Error('WRONG_STAGE');
}
function items_(stage) { return stage === 'A' ? PART_A : PART_B; }
function answers_(rater, stage) {
  const data = ss_().getSheetByName('responses').getDataRange().getValues();
  const out = {};
  for (let i = 1; i < data.length; i++) {
    const r = data[i];
    if (r[1] !== rater || r[2] !== stage) continue;
    out[r[3]] = out[r[3]] || {};
    out[r[3]][r[4]] = String(r[5]);
  }
  return out;
}
function countComplete_(ans, stage) {
  return Object.keys(ans).filter(function (id) {
    return REQUIRED[stage].every(function (f) { return ans[id][f]; });
  }).length;
}
function events_(rater) {
  const data = ss_().getSheetByName('status').getDataRange().getValues();
  const ev = {};
  for (let i = 1; i < data.length; i++) {
    if (data[i][1] === rater) ev[data[i][2] + ':' + data[i][3]] = new Date(data[i][0]).toISOString();
  }
  return ev;
}
function lastActivity_(rater, stage) {
  const data = ss_().getSheetByName('responses').getDataRange().getValues();
  let last = '';
  for (let i = 1; i < data.length; i++) if (data[i][1] === rater && data[i][2] === stage) last = new Date(data[i][0]).toISOString();
  return last;
}
function logEvent_(rater, stage, event) {
  withLock_(function () { ss_().getSheetByName('status').appendRow([new Date(), rater, stage, event]); });
}
function withLock_(fn) {
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try { return fn(); } finally { lock.releaseLock(); }
}
function shuffle_(arr, seedText) {
  let h = 2166136261;
  for (let i = 0; i < seedText.length; i++) { h ^= seedText.charCodeAt(i); h = Math.imul(h, 16777619); }
  let s = h >>> 0;
  const rnd = function () { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  for (let i = arr.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); const t = arr[i]; arr[i] = arr[j]; arr[j] = t; }
  return arr;
}
function randomString_(n) {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let s = '';
  for (let i = 0; i < n; i++) s += chars.charAt(Math.floor(Math.random() * chars.length));
  return s;
}
function csv_(v) {
  const s = String(v == null ? '' : v);
  return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}
