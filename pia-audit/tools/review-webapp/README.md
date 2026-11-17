# Review web app (Part A pharmacists, Part B doctors)

A custom review website that runs from **your own Google account** (Google Apps Script). Answers are saved to a Google Sheet you own. Reviewers need no account: each gets a personal link.

## Files
| File | What it is |
|---|---|
| `Code.gs` | Server code (security, saving, blinding, export) |
| `Index.html` | The reviewer page |
| `Admin.html` | Your coordinator dashboard |
| `build_review_data.py` | Builds `dataA.gs` and `dataB.gs` (question text, answer key) from your local MedAraBench file. These files are never committed. |
| `partA_sample.csv`, `partB_items.csv` | Item IDs, option maps, strata and sampling weights |
| `score_review.py` | Scoring after the reviews (`partB_key.csv` is written by the build script) |

## Set up (about 15 minutes)
0. Run `python build_review_data.py --benchmark medarabench-test_split.csv` to create `dataA.gs`, `dataB.gs` and `partB_key.csv`.
1. Go to https://script.google.com → **New project**. Name it `MedQA review web app`.
2. Replace the content of `Code.gs` with the file `Code.gs`.
3. Click **+ → Script**, name it `dataA`, paste `dataA.gs`. Repeat for `dataB`.
4. Click **+ → HTML**, name it `Index` (exactly), paste `Index.html`. Repeat with the name `Admin` for `Admin.html`.
5. **Save**. Choose the function `setup` and click **Run**. Allow the permissions (Advanced → Go to project → Allow).
6. Click **Deploy → New deployment**. Click the gear next to "Select type" → **Web app**. Set:
   - Execute as: **Me**
   - Who has access: **Anyone**
   Click **Deploy** and allow the permissions.
7. Back in the editor, choose the function `showLinks` and click **Run**.
8. Open the spreadsheet **MedQA_Review_Responses** in Google Drive → sheet **access**. It lists:
   - a personal link for P1, P2, D1 and D2 (send each person **only their own** link);
   - the **COORDINATOR** dashboard link (keep it private).

## How it works
- **Pharmacists (P1, P2):** a 3-example training step first, then 150 questions one per screen. Each screen shows order X and order Y side by side, with lines connecting identical options. They choose: same meaning / meaning changed / uncertain.
- **Doctors (D1, D2):** B1 – answer each question blind. After they submit B1, B2 unlocks automatically and shows the benchmark key and the AI model's answer. The server never sends the key before B1 is submitted.
- Every click is saved immediately. Reviewers can close the page and continue later with the same link. Each reviewer sees the questions in their own random order.
- After submitting a part, it can no longer be changed.

## During the review
Open the coordinator dashboard to see each reviewer's progress. When everyone has submitted, click **تصدير CSV** (Export). A CSV file appears in your Google Drive.

## Scoring
Download the exported CSV, then run:
```
python score_review.py partA --long responses_export.csv --register partA_sample.csv
python score_review.py partB --long responses_export.csv --key partB_key.csv
```
Each command writes a `*_disagreements.csv` for the consensus discussion; rerun with `--adjudication <file>` afterwards. Send me the outputs.

## If you change a file after deploying
Deploy → **Manage deployments** → edit (pencil) → Version: **New version** → Deploy. The links stay the same.
