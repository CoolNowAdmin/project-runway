# Runway

**How much lease you have left, and what it buys you.**

Capstone project for the AI Champions Bootcamp 2026 (Project Type 2), by Team Runway: Lynn Koh, Leong Soon Poh,
Danish Syafiq and Max How.

Runway helps HDB resale buyers understand one rule that keeps catching people out. Since May 2019, how much CPF you
can put towards a flat depends on whether its lease will last until the youngest buyer turns 95. If it won't, CPF use
and the HDB loan are both scaled down. Runway works this out for your own ages and flat, shows what a shorter lease
costs in each town you're considering, and explains the result in plain English with the official rule quoted.

## What's in the app

The interface in `runway_game/index.html` is the approved design hand-off, running full-window inside Streamlit. One left navigation (Home, Map, Shortlist, Trends, Ask, More, Log in) is on every screen: a fixed sidebar on wide screens, a drawer behind the menu button on phones. Every screen has its own address (`/`, `/map`, `/shortlist`, `/trends`, `/ask`, `/more`, and `/details`, `/text-size`, `/about`, `/how-it-works`, `/sources`, `/faq`, `/timeline`, `/case-study`, `/privacy`, `/terms` under More), so reloads, shared links and Back/Forward work; addresses carry page names only, never anything you type. Every inner page has a breadcrumb back to Home, the navigation has a site search (pages, FAQ questions and towns, in the browser only), and an unknown address opens Home with a "Page not found" notice.

| Screen | What it does |
|---|---|
| **Home page** | Landing page, Ask Runway first: a question box (**Ask Runway** asks it on the Ask page) beside one worked example that quotes the official document, the age-95 rule calculator, what a shorter lease costs by town, and the required notice. Green and beige palette, the device's system font (Anton only for the RUNWAY wordmark), as set out in `DESIGN.md`. **Log in** in the navigation opens the reviewer login over the page. |
| **Setup** | Youngest buyer's age, rough CPF, first town. No names or NRIC. |
| **Map** (use case 1) | Town Safari: every HDB block, MRT lines and the flats sold in Jul–Sep 2026. Tap a diamond for the verdict, runway bar, CPF you can use and cash you need. Keep, Why?, Next flat. **Find by budget** ranks towns and flat types by how many recent sales your cash and CPF cover; **Filters** narrow the diamonds by flat type, price, cash and CPF verdict. |
| **Flat result** | Opened from a diamond. A price check against similar recent sales (same town and flat type, lease within 5 years, last 12 months, from `runway/price_check.py`); Buyer's Stamp Duty, HDB fees and the grants you may get once you add income and household details; an HDB loan beside a bank loan at a rate you type, with the 30% income cap; and what the lease means for whoever buys from you in 5 to 20 years. Every figure names its document in `data/corpus/`. |
| **Shortlist** | Kept flats recalculated for your details, two or three of them side by side in a table, a printable summary, CSV download, and 26 town stamps with Wikimedia Commons photos. |
| **Trends** | Public price charts, no login or setup needed. Compare median resale price or price per sqm by town since 1990 (up to 5 places, by flat type and period), and what remaining lease does to price. Numbers are built from `data/resale.parquet` by `runway/trends.py`; each chart has a table view. |
| **Ask** (use case 2) | Answers from 32 official documents with sources, "Why?" for a flat, chat summary, read-aloud, and document upload that suggests towns. Answers, read-aloud and voice input in English, Chinese, Malay or Tamil (official quotes and figures stay in English; the rest of the interface is English). Helpful / Not helpful under each AI answer: a vote writes one line to the server log and to `data/feedback.jsonl` where the disk is writable, with the question kept only if it has no personal details. |
| **More** | Your details (with a reset), text size, About Us (with the required notice), How it works (flowcharts), Sources and credits, an FAQ whose answers each cite one document in `data/corpus/`, a buying timeline (`/timeline`) from the HFE letter to completion with a source for every step, a case study worked out live from the Trends data, the Privacy Policy and the Terms. Visitors browse as guests and see short versions; logging in as `reviewer` shows the full About Us and How it works. |

Python (`runway/bridge.py`) checks the reviewer login, sends the map data after the home page loads, and answers questions
(`runway/rag.py` + `runway/llm.py`). The map's calculator runs in the browser and is tested against
`runway/cpf_rules.py` so both give the same numbers. The AI never calculates; an explanation with a number
the calculator didn't produce is replaced by a plain template.

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then add your ANTHROPIC_API_KEY
python scripts/seed_users.py                                  # creates demo logins (see below)
streamlit run app.py
```

Without an `ANTHROPIC_API_KEY` the app still works: calculations, charts and keyword search run as normal, and Ask
Runway shows the matching official passages instead of an AI answer.

Ask Runway uses Claude through the Anthropic API: `claude-opus-5-5` by default, or the model named in
`ANTHROPIC_MODEL` (for example `claude-haiku-5-5`, which costs far less per answer). The key comes from
[console.anthropic.com](https://console.anthropic.com); a Claude subscription does not include one. Documents are found by
keyword search, and a question in Chinese, Malay or Tamil is put into English by the model first.

## Logins

Anyone can use Runway without an account. One `reviewer` login unlocks the full About Us and How it works.
No passwords are stored in this repository. `scripts/seed_users.py` creates the account from, in order:

1. the `RUNWAY_DEMO_USERS` environment variable (`name:password`), or
2. `demo_accounts.local.toml` (gitignored), or
3. a generated `reviewer` account with a random password, saved to `demo_accounts.local.toml`.

It writes only a salted PBKDF2 hash to `.streamlit/secrets.toml` (also gitignored). For a deployed app, paste that
file's contents into **Streamlit Community Cloud > App settings > Secrets**. Use `--rotate` for a new password.

## Deploy (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. At [share.streamlit.io](https://share.streamlit.io), create an app from the repo, branch `main`, main file
   `app.py`, Python 3.12, and set the custom subdomain `runway-hdb` (app URL: https://runway-hdb.streamlit.app).
3. Paste the contents of your local `.streamlit/secrets.toml` (the `ANTHROPIC_API_KEY` line first, then the `[auth.users]` hashes: a key placed below `[auth.users]` is read as a
   username and the AI stays off) into the app's
   Secrets.

## Project layout

```
app.py                 Streamlit host: full-window interface + message loop
runway_game/index.html the interface (from design/runway-mockup.html in the hand-off)
runway_game/assets/    home page photos (Wikimedia Commons, credited on the page)
DESIGN.md              colours, type, spacing and copy rules for the interface
runway/bridge.py       sign-in, ask, why, summary, trends, towns, town_photo and nav (page URL) messages
runway/cpf_rules.py    age-95 rule, CPF share, HDB loan limit, loan tenure (Python reference)
runway/costs.py        stamp duty, HDB fees, grants, HDB and bank loan under the income cap
runway/price_check.py  one flat's price per sqm against similar recent sales
runway/rag.py          chunking and BM25 keyword search
runway/llm.py          prompts, question screening, number guard, Claude calls (Anthropic API)
runway/auth.py         password hashing and checks
runway/game_data.py    map data and town photos; town list and one photo at a time for the home page
data/game/             towns, Jul-Sep 2026 sales, blocks, roads, MRT, amenities
data/photos/           26 town photos + credits (scripts/fetch_town_photos.py)
data/corpus/           32 official documents with source URLs
data/resale.parquet    986,090 HDB resale transactions (offline analysis)
eval/, tests/          evaluation questions and the pytest suite
```

## Checks

```bash
pytest                 # includes a check that the map's calculator matches cpf_rules.py (needs Node.js)
python eval/run_eval.py   # retrieval, calculator, decline checks (+ LLM answers if a key is set)
```

The CPF formula reproduces every official worked example: MND's May 2019 Annex B (age 25 with 55 / 65 / 75 years
left gives 70% / 90% / 100%) and CPF Board's FAQ. The lease premium reproduces the proposal's Table 1 from the data.

## Data and licences

- HDB resale flat prices, [data.gov.sg](https://data.gov.sg/collections/189/view), Singapore Open Data Licence.
  Rebuild `data/resale.parquet` with `python scripts/build_dataset.py <folder with the 5 CSVs>`, or run
  `python scripts/refresh_data.py` to download the five files and rebuild in one step.
- **Monthly refresh.** The "Data refresh" GitHub workflow runs `refresh_data.py` on the 3rd of each month, runs the
  tests and opens a pull request with the new `data/resale.parquet` and `data/dataset_meta.json`. It never pushes to
  `main`, so nothing deploys until the pull request is merged. It needs the repository setting "Allow GitHub Actions
  to create and approve pull requests". Trends and the home page figures follow the new data; the map's Jul–Sep 2026
  sales and each town's lease effect stay as they are, because `data/game/` came from the design hand-off and has no
  build script. The transaction count in this file is as at Sep 2026.
- Rules documents: public pages from CPF Board, HDB, MND, MOM, IRAS and CEA, retrieved 16 Oct 2026. Each file in
  `data/corpus/` records its source URL.
