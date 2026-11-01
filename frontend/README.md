# MatchLab 2.0 — frontend

Next.js frontend, isolated from the existing Streamlit application. Forecasts and settlements are fetched from the existing public GitHub repository; no mock predictions are generated.

## Run locally

```bash
cd frontend
npm install
npm run dev
```

## Deploy to Vercel

Import `Bruce-zda/matchlab-ai` into Vercel and set **Root Directory** to `frontend`. Use the Next.js framework preset. Deploy the frontend independently of Streamlit. This repository change does not create a Vercel project or public deployment by itself.

Data is read from `artifacts/forward_ledger.json` and `artifacts/forward_settlements.json` on the main branch with a 120-second revalidation window. The UI shows archived forecast snapshots, not live odds. A result is shown only if the matching provider ID has a recorded settlement.
