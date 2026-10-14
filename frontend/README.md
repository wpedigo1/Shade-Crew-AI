# Shade Crew AI browser console

React/Vite frontend using the existing three-seat ModelMix runtime.

Run the backend from the repository root with `uv run python -m backend.main`,
then run `npm ci` and `npm run dev -- --host 127.0.0.1` here.

`npm test`, `npm run lint`, and `npm run build` validate the frontend.
`npm run preview -- --host 127.0.0.1 --port 5173` serves the production build.
The root and `/modelmix` URLs both show the cockpit. No Council route is exposed.
See the root README for local server configuration and compatibility boundaries.
