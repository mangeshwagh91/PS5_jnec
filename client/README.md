# Client App

React + Vite frontend for the surveillance command center.

## Local Run

```powershell
npm install
npm run dev
```

Default local URL: `http://localhost:8000`

## Environment Variables

Use `.env` (copy from `.env.example`):

- `VITE_API_BASE_URL` default `http://localhost:8001/api/v1`
- `VITE_ALERTS_WS_URL` default `ws://localhost:8001/ws/alerts`
- `VITE_SURVEILLANCE_ROLE` default `admin`

## Build

```powershell
npm run build
npm run preview
```

## Tests

```powershell
npm run test
```
