# X / Twitter thread (draft)

Attach the noted image to each tweet. Links: repo
`https://github.com/esonghori/narrow-corridor-llm` · gallery
`https://esonghori.github.io/narrow-corridor-llm/`

---

**1/** 🎞️ *[attach: `thread/iran.gif`]*

Acemoglu & Robinson's *The Narrow Corridor* maps history in a 2D space — state power vs. society power — but never actually plots a country's path through it.

So I had LLMs do it. Here's Iran, 1880→2010, decade by decade. 🧵

---

**2/**

Method: for each decade the model first lists that period's key events & trends, *then* scores state and society power 0–10 against a fixed rubric, carrying prior periods forward for coherence.

Provider-agnostic — I ran Gemini 2.5 Pro, Claude Opus 4.8, GPT-5.5, and open-weight Qwen.

---

**3/** 📈 *[attach: `thread/ensemble_atlas.png`]*

The six-country atlas (mean of the 4 models) reproduces the book's map:

🇬🇧 stays *in* the corridor · 🇫🇷 enters it · 🇨🇱 exits at the 1973 coup and returns after 1990 · 🇮🇷 & 🇨🇳 exit **upward** into state-dominance — the "Despotic Leviathan."

---

**4/**

Does it mean anything? Checked against V-Dem expert codings:

LLM "society power" tracks V-Dem's civil-society index well (China ρ=.89, France .87). And the 4 models agree with each other (Krippendorff α=.74 on society).

→ a shared, expert-consistent signal, not one model's quirk.

---

**5/** *[attach: US panel — `paper/experiments/results/united-states__ensemble-mean.png`]*

The honest divergence: 🇺🇸.

The LLMs read modern America drifting toward state-dominance. The book (and V-Dem) keep US civil society strong. It's also the country where the 4 models agree *least* — disagreement flags the contested case.

---

**6/**

Two caveats I lead with, not bury:
• These indices are almost certainly in the models' training data, so agreement = *consistency*, not proven accuracy.
• The strongest *open* model (Qwen3-235B) couldn't reliably emit structured scores — a real reproducibility gotcha.

---

**7/**

Everything's open: code, prompts, every run, the paper, and an interactive gallery where you can click any trajectory to play its animation.

Repo: github.com/esonghori/narrow-corridor-llm
Gallery: esonghori.github.io/narrow-corridor-llm
