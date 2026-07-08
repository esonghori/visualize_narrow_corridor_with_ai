# X / Twitter thread (draft)

Attach the noted media to each tweet (🎬 = animated GIF). Links: repo
`https://github.com/esonghori/narrow-corridor-llm` · gallery
`https://esonghori.github.io/narrow-corridor-llm/`

---

**1/** 🎬 *[attach: `docs/assets/united-states__ensemble-mean.gif`]*

@DAcemogluMIT & James A. Robinson (2024 Economics Nobel laureates) wrote *The Narrow Corridor*, mapping history in a 2D space — state power vs. society power — but never plotted a single country's path through it.

So I had LLMs do it. Here's the United States, 1789→2020, decade by decade. 🧵

---

**2/**

Method: for each decade the model first lists the key events & trends, *then* scores state and society power 0–10 on a fixed rubric — feeding prior periods forward so the path stays coherent.

---

**3/** 📈 *[attach: `paper/experiments/results/all-countries__ensemble-mean.png`]*

All 12 countries on one shared scale sort into the book's regions:

🇨🇳🇮🇷 above the corridor → **Despotic** · 🇬🇧🇫🇷🇺🇸🇮🇳🇨🇱 inside → **Shackled** · 🇨🇩🇸🇴🇱🇧 down in the weak-state region below.

One fixed 0–10 rubric is what lets you plot them all together.

---

**4/** 🎬 *[attach 2 GIFs: `docs/assets/united-kingdom__ensemble-mean.gif`, `docs/assets/china__ensemble-mean.gif`]*

The whole thesis in two clips:

🇬🇧 Britain rises *along* the diagonal and stays in the corridor — state & society growing together (the "Red Queen").
🇨🇳 China climbs straight *up* and out — a strong state over a weak society (the Despotic Leviathan).

---

**5/** 🎬 *[attach: `docs/assets/chile__ensemble-mean.gif`]*

Chile is the drama: watch it get thrown out of the corridor at the 1973 coup — society crashing, state spiking — then climb back in after the 1990 return to democracy.

---

**6/** 🎬 *[attach: `docs/assets/india__ensemble-mean.gif`]*

The new cases stress-test the framework:

🇮🇳 India climbs into the corridor — a Shackled Leviathan.
🇱🇧 Lebanon & 🇸🇴 Somalia sink into the weak-state zone, society outrunning a barely-there state.
🇿🇲 Zambia I pegged as a "Paper Leviathan" — but the models put it *inside* the corridor. A miss I report, not hide.

---

**7/**

A subtlety the plot can't show: **Paper vs Absent** Leviathan isn't a location — both are weak states low on the state axis. The difference is legal. A *Paper* state exists on paper but can't enforce (🇱🇧 Lebanon); an *Absent* one doesn't exist even on paper (🇸🇴 Somalia).

---

**8/**

Does it mean anything? Four LLMs — Gemini 2.5 Pro, Claude Opus 4.8, GPT-5.5, and open-weight Qwen — score independently.

Against V-Dem expert codings, "society power" tracks the civil-society index well (China ρ=.89, France .87), and the models agree with each other (Krippendorff α=.66).

→ a shared, expert-consistent signal, not one model's quirk.

---

**9/**

Two caveats I lead with, not bury:
• These indices are almost certainly in the models' training data, so agreement = *consistency*, not proven accuracy.
• Coverage is thinnest for exactly the non-Western cases (Iran, China, Colombia, DR Congo, Lebanon, Somalia, Zambia) — the training data is English-heavy.

---

**10/**

Everything's open: code, prompts, every run, the paper, and an interactive gallery where you click any trajectory to play its animation.

Repo: github.com/esonghori/narrow-corridor-llm
Gallery: esonghori.github.io/narrow-corridor-llm
