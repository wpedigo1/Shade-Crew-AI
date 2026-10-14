<div align="center">

# ModelMix

### Stop asking one AI and hoping it's right.

**ModelMix gets independent answers from different AI models, then gives them to a Moderator that compares the evidence, handles disagreement, and builds one stronger answer.**

<br>

`Worker A` · `Moderator` · `Worker B`

<br>

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

</div>

---

## One model gives you one perspective.

AI models don't all fail in the same way.

They have different training, reasoning tendencies, strengths, blind spots, and levels of confidence. Asking a second model can expose problems the first one missed — but then **you** have to compare the answers and decide what to trust.

ModelMix does that part too.

```text
                        YOUR PROMPT
                            │
                  ┌─────────┴─────────┐
                  │                   │
                  ▼                   ▼
          ┌───────────────┐   ┌───────────────┐
          │   WORKER A    │   │   WORKER B    │
          │               │   │               │
          │ Independent   │   │ Independent   │
          │ response      │   │ response      │
          └───────┬───────┘   └───────┬───────┘
                  │                   │
                  │   NO CROSS-TALK   │
                  │                   │
                  └─────────┬─────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   MODERATOR   │
                    │               │
                    │ Sees both     │
                    │ responses     │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ FINAL ANSWER  │
                    └───────────────┘
```

> **The side models are independent witnesses.  
> The Moderator is the only one who knows the full picture.**

---

## The idea is simple

**Worker A** gets your request and answers it.

**Worker B** gets the same request and answers it independently.

Neither worker knows the other exists during the run. They don't see each other's response. They don't debate, rank, critique, or converge on a shared answer.

Then the **Moderator** receives both completed responses.

Its job isn't to count votes.

It's to figure out what deserves to survive.

The Moderator can identify agreement, investigate disagreement, weigh supporting evidence, preserve useful minority views, recognize uncertainty, and reject unsupported conclusions before producing the final response.

### Independence first. Synthesis second.

That's ModelMix.

---

## Why?

A polished answer isn't necessarily a correct answer.

And asking the same model to double-check itself still leaves you inside the same model's perspective.

ModelMix is built around a different idea:

> **Get genuinely independent perspectives before asking anyone to reconcile them.**

That gives the Moderator something valuable to work with: **real disagreement**.

If both workers independently reach the same conclusion, that's useful.

If they disagree, that's useful too.

If one catches something the other completely misses, that's exactly the point.

---

## The Cockpit

ModelMix isn't designed as a pile of temporary AI result cards.

It's a three-seat conversation workspace.

```text
┌────────────────────┬──────────────────────────────┬────────────────────┐
│                    │                              │                    │
│      WORKER A      │          MODERATOR           │      WORKER B      │
│                    │                              │                    │
│   Independent AI   │      Wider center seat       │   Independent AI   │
│                    │                              │                    │
│                    │                              │                    │
│                    │                              │                    │
│                    │                              │                    │
├────────────────────┴──────────────────────────────┴────────────────────┤
│                                                                       │
│  Ask ModelMix...                                      [ Send ] [Stop] │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

Each seat is its own persistent conversation surface.

The wider center seat belongs to the Moderator because that's where the final synthesis happens.

The interface stays intentionally simple.

**Three seats. One prompt. Better perspective.**

---

## What makes ModelMix different?

| | ModelMix |
|---|---|
| 🧠 **Independent workers** | Workers form their answers without seeing or influencing each other. |
| ⚖️ **Moderator synthesis** | A separate model evaluates the completed worker responses. |
| 🔀 **Mix models** | Different AI models and providers can occupy different seats. |
| 💬 **Persistent seats** | Worker and Moderator conversations are real conversation surfaces, not disposable cards. |
| 📡 **Live runs** | Responses can stream into their seats while a run is active. |
| 🔄 **Reconnectable** | Run state is designed to survive ordinary frontend disconnects and reconnects. |
| ✋ **Explicit cancellation** | Send and Stop are separate controls with honest run state. |
| 🏠 **Local-first** | ModelMix is designed around local application state and user-controlled provider access. |
| 🔐 **Credential isolation** | Provider credentials stay separate from ordinary prompts and conversation data. |
| 📊 **Honest telemetry** | Reported, calculated, estimated, and unavailable information aren't pretended to be the same thing. |

---

## No fake consensus

ModelMix deliberately does **not** make the workers debate each other before synthesis.

Why?

Because the moment Worker B sees Worker A's answer, Worker B is no longer giving you a fully independent second perspective.

The same problem appears when models rank one another, critique one another, or iteratively converge before the final synthesis.

ModelMix keeps that boundary clean:

```text
Worker A ────────┐
                 │
                 ├────► Moderator
                 │
Worker B ────────┘

Worker A  ✕  Worker B
```

Workers produce evidence.

The Moderator sees the whole picture.

---

## Mix the models you trust

ModelMix is being built to sit above individual AI providers rather than belong to one of them.

That means the interesting question becomes:

**Which models do you want in the seats?**

A Mix might use models from different companies.

It might combine cloud and local models.

It might deliberately pair models with different strengths.

And the model occupying a seat can change without changing what that seat means.

**Seats are resources. Roles are assignments.**

ModelMix preserves which provider and model actually produced a response rather than silently swapping one for another.

---

## Honest by design

ModelMix shouldn't tell you something it doesn't know.

That applies to AI answers — and to the application itself.

If a provider reports usage, ModelMix can identify it as provider-reported.

If ModelMix calculates something locally, it can identify it as ModelMix-tracked.

If something is estimated, it should say so.

If the information isn't available:

**Unknown means unknown.**

No invented quota percentages.

No fake provider status.

No imaginary precision.

No silent model substitutions.

---

## Runs that behave like real work

AI requests aren't always instant.

Connections drop. Providers fail. Users hit Stop. One worker may finish while another doesn't.

ModelMix treats those as real states instead of pretending every request ends neatly.

The run architecture is designed around:

- ordered streaming events;
- persistent run identity;
- reconnect and replay;
- duplicate protection;
- explicit cancellation;
- preserved partial output;
- visible failures;
- honest terminal states.

If useful work was already produced, ModelMix shouldn't casually throw it away.

---

## Local-first

ModelMix is designed as software **you run**, connected to AI providers **you choose**.

Conversation and application state remain under a ModelMix-owned persistence layer rather than requiring ModelMix to operate a paid AI backend for you.

Provider credentials are handled separately from ordinary conversation content and should never be committed to the repository.

---

# Quick Start

## Requirements

- Python **3.10+**
- Node.js **18+**
- [`uv`](https://docs.astral.sh/uv/)

## 1. Clone ModelMix

```bash
git clone https://github.com/wpedigo1/ModelMix.git
cd ModelMix
```

## 2. Install dependencies

```bash
uv sync
npm install --prefix frontend
```

## 3. Start ModelMix

```bash
./start.sh
```

Open:

```text
http://localhost:5173
```

<details>
<summary><strong>Run the backend and frontend separately</strong></summary>

<br>

Backend:

```bash
uv run python -m backend.main
```

Frontend:

```bash
cd frontend
npm run dev
```

Then open:

```text
http://localhost:5173
```

</details>

<details>
<summary><strong>Docker</strong></summary>

<br>

The inherited application includes Docker-based startup:

```bash
docker compose up -d --build
```

Docker and deployment behavior may continue to change while inherited infrastructure is converted to ModelMix.

</details>

---

## Under the hood

ModelMix currently builds on:

| Layer | Technology |
|---|---|
| Frontend | React 19 |
| Backend | FastAPI |
| Language | Python 3.10+ |
| Package management | uv / npm |
| Streaming | Server-Sent Events |
| Alpha persistence | Versioned atomic JSON |
| Browser development | Local web application |

The browser experience is the primary alpha surface.

The architecture intentionally keeps important boundaries — providers, persistence, run state, credentials, and UI — replaceable enough to evolve without rewriting the core ModelMix product model.

---

## Built from a strong foundation

ModelMix began as a fork/evolution of **The AI Counsel**, an open-source multi-model AI project.

AI Counsel provided substantial working infrastructure around providers, conversations, model access, streaming, and other capabilities.

ModelMix takes the product in a different direction.

Instead of Council peer review, Chairman ranking, Advisor personas, and multi-round debate, ModelMix centers the experience on:

```text
Independent Worker
        +
Independent Worker
        +
     Moderator
```

Some inherited AI Counsel code, documentation, terminology, assets, and configuration may remain in the repository while that transition is underway.

Their presence does not automatically mean they describe current ModelMix behavior.

**Credit to the original AI Counsel project and its contributors for the foundation ModelMix started from.**

---

## For developers

Before changing ModelMix, coding agents should read:

```text
AGENTS.md
```

That file defines the permanent ModelMix engineering contract, including:

- worker independence;
- Moderator boundaries;
- run/event integrity;
- persistence;
- provider behavior;
- security;
- telemetry;
- UI constraints;
- testing and validation;
- scope discipline.

Task prompts should describe the individual change.

`AGENTS.md` describes ModelMix.

---

## Where ModelMix is going

The default experience stays intentionally small:

### Worker A · Moderator · Worker B

More power can grow around that foundation without turning the main interface into an AI control room.

Future directions can include richer research, additional Mix configurations, deeper evidence inspection, expanded provider capabilities, desktop packaging, mobile experiences, and other advanced tools.

But the core idea doesn't need to get complicated:

```text
Ask once.

Get independent perspectives.

Let the Moderator make sense of them.
```

---

## Development Status

> 🚧 **ModelMix is under active development.**

The repository is currently transitioning from its AI Counsel foundation to the ModelMix architecture.

Some inherited functionality may still exist while replacement work continues.

Expect things to move.

---

## License

ModelMix retains the repository's existing licensing and applicable upstream attribution requirements.

See the repository's license files for authoritative terms.

---

<div align="center">

# ModelMix

### Don't trust one perspective when you can compare two.

**Independent models · Independent perspectives · One Moderator**

<br>

⭐ If the idea interests you, star the repo and follow the build.

</div>