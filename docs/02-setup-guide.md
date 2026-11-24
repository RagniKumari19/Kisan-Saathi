# Phase 2 — Your Setup Guide

Only a few steps need you personally: installing one Python version, starting Docker, and creating five accounts. Everything else is code I write in Phase 3.

Work top to bottom. Each step has a **verify** command with expected output. If a verify fails, stop there — do not continue to the next step.

Run all commands in **Git Bash** (not cmd, not PowerShell), from `/c/Users/Public/farm`.

---

## Step 1 — Verify Python 3.12 (already installed ✅)

Python **3.12.10** is already on this machine and is reachable as `py -3.12`. Nothing to install — but the default `python` on PATH is 3.14.7, which is too new for PyTorch wheels, so **every command and Docker build must use 3.12**. That's a rule I enforce in Phase 3, not something you need to remember.

Just confirm it:

```bash
py -3.12 --version
```

**Expected:** `Python 3.12.10`

> Do not run `python --version` to check this — it resolves to 3.14 and tells you nothing about whether 3.12 is usable.

---

## Step 2 — Make sure Docker Desktop actually runs (5 min)

Docker is installed (29.7.2) but the engine only runs when Docker Desktop is started.

```bash
docker info --format '{{.ServerVersion}}'
```

- **Prints a version** → good, you're done with this step.
- **`error during connect` / `cannot connect to the Docker daemon`** → start Docker Desktop from the Start menu, wait for "Engine running", retry.
- **No output at all** → the engine is stopped or WSL is unhealthy. Open Docker Desktop → *Settings → Troubleshoot → Restart*.

Then confirm Compose is available:

```bash
docker compose version
```

**Expected:** `Docker Compose version v2.x` (note: `docker compose`, with a space, not `docker-compose`).

> If Docker Desktop asks you to enable WSL 2 and you accept, Windows may need a reboot. Do that before continuing.

---

## Step 3 — Get the free API keys (20 min of clicking, one 1–2 day wait)

You can start the project without most of these — Phase 3–6 need **none** of them. But two have real-world latency, so request them now.

### 3a. data.gov.in API key — instant, needed in Phase 9

1. Go to `https://www.data.gov.in` → **Register** (email + OTP).
2. Sign in → click your profile/name → **My Account** → **API key**.
3. Copy the long alphanumeric string.

Verify it works (replace the key):

```bash
curl -s "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key=YOUR_KEY&format=json&limit=1" | head -c 600
```

**Expected:** JSON containing `"status":"ok"` and a `records` array with fields like `state`, `district`, `market`, `commodity`, `arrival_date`, `modal_price`.
**If it returns `"status":"error"` with an invalid-key message:** the key can take a few minutes to activate; retry later.

### 3b. OpenWeatherMap API key — instant to 2 hours, needed in Phase 7

1. `https://openweathermap.org/api` → **Sign Up** (free).
2. **My API keys** tab → copy the default key.
3. Stay on the **free "Current & Forecast"** plan. Do **not** subscribe to *One Call 3.0* — it has its own per-call billing and we deliberately don't use it.

Verify (new keys can take up to ~2 h to activate; a `401` right after signup is normal):

```bash
curl -s "https://api.openweathermap.org/data/2.5/weather?q=Pune&appid=YOUR_KEY&units=metric" | head -c 300
```

**Expected:** JSON with `"name":"Pune"` and a `main.temp` value in °C.

### 3c. Bhashini — 1–2 business days, needed in Phase 10

1. `https://dashboard.bhashini.co.in/user/register` → register with email + phone.
2. Complete the profile; submit for approval (DIBD reviews it).
3. After approval, go to **My Profile / API keys** and copy the inference API key.

Nothing to verify yet — I'll wire it in Phase 10. Registering now means it isn't blocking you in three weeks.

### 3d. Cloudflare R2 — ~10 min, needed in Phase 8

1. `https://dash.cloudflare.com` → sign up (free) → **R2 Object Storage** → enable.
   *Note: R2 requires a payment method on file even for the free tier (10 GB storage, 1M writes, 10M reads, zero egress).*
2. Create a bucket named `farm-images`.
3. **Manage R2 API Tokens** → create a token with *Object Read & Write* on that bucket → copy **Access Key ID**, **Secret Access Key**, and your **Account ID** (shown in the R2 overview).

Nothing to verify yet — local disk storage is used until Phase 8.

### 3e. SMS / DLT — start now if SMS matters to you, weeks-end to weeks-long

This is paperwork, not code, and it is the single slowest dependency:

1. Pick an Indian provider with DLT support: **MSG91**, **Fast2SMS**, or **Exotel**. Create an account and note the API key.
2. On the operator DLT portal your provider points you to (Jio/Airtel/Vi/Idea portals, or a provider-hosted flow):
   - register as a **Principal Entity** (needs GST/PAN + business details; an individual can register as "Sole Proprietor" with PAN),
   - get a **Header/Sender ID** (6 characters, alphanumeric),
   - submit **Content Templates** — you need at least: OTP, weather alert, price alert, expert reply. Approval is usually 1–3 days per template after entity approval.
3. Send me the entity ID, header, and approved template IDs when you have them.

**Decision point:** if SMS is not needed for your demo, skip 3e entirely. Phase 11 ships in-app notifications; SMS stays behind a flag until the paperwork exists. Nothing else is blocked.

---

## Step 4 — (Optional) Colab for model training

Phase 8 trains an image classifier. On CPU it takes hours; on a free Colab GPU, ~30–60 minutes.

1. `https://colab.research.google.com` → sign in with a Google account.
2. Create a notebook, then **Runtime → Change runtime type → T4 GPU**.
3. Verify GPU availability:

```python
import torch
print(torch.cuda.is_available(), torch.cuda.get_device_name(0))
```

**Expected:** `True Tesla T4`. If it prints `False`, you have no GPU quota left for the day — the free tier is not guaranteed. In that case Phase 8 uses Kaggle Notebooks (30 GPU-hours/week) instead, or a reduced training run on CPU with a smaller model. I'll adapt the plan to whichever you have.

---

## Step 5 — First commit (2 min)

I already ran `git init`, and your git identity is already set (`ragnikumari1907@gmail.com`), so there is nothing to configure.

Commit the Phase 1 + Phase 2 documents, so there is a checkpoint to return to:

```bash
cd /c/Users/Public/farm
git add -A
git commit -m "Add phase 1 architecture and phase 2 design documents"
git log --oneline
```

**Expected:** one commit, one line of output.

---

## Step 6 — Where the keys go (30 seconds, later)

Do **not** create `.env` yet — Phase 3 generates `.env.example` with every variable documented, and I'll ask you to copy it:

```bash
cp .env.example .env     # Phase 3
```

Then you paste keys into `.env`. `.env` is already gitignored, and it must never be committed or pasted into chat. When you're ready, tell me *"keys are in .env"* rather than sending me the values — I only need to know they're set, and I can verify by calling the API.

---

## Step 7 — The one command that tells you if you're ready

After Steps 1–2, run the preflight check I've added:

```bash
cd /c/Users/Public/farm && bash infra/scripts/preflight.sh
```

It checks Python 3.12, Node, Docker engine, Compose, Git, disk space and free memory, and prints a `PASS`/`FAIL` line for each with the exact fix. Everything relevant to Phase 3 must be `PASS`; API keys are checked separately and may be `PENDING`.

---

## Summary — what you do, in order

| # | Task | Time | Blocks |
|---|---|---|---|
| 1 | Verify Python 3.12 (already installed) | 10 s | Phase 5 |
| 2 | Start Docker Desktop + verify | 5 min | **Phase 3 (next)** |
| 3a | data.gov.in key | 10 min | Phase 9 |
| 3b | OpenWeatherMap key | 10 min | Phase 7 |
| 3c | Bhashini registration (approval 1–2 days) | 15 min | Phase 10 |
| 3d | Cloudflare R2 bucket + token | 10 min | Phase 8 |
| 3e | SMS/DLT (optional, slow) | 1 h + wait | Phase 11 |
| 4 | Colab GPU check (optional) | 5 min | Phase 8 |
| 5 | First commit (identity already set) | 2 min | — |
| 7 | Run preflight | 1 min | Phase 3 |

**Minimum to start Phase 3: just Steps 1, 2 and 7.** Everything else can happen while I build.

When preflight is green, say **"preflight passed"** and I'll build the Docker stack.
