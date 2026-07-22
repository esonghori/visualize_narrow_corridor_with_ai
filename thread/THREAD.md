# X / Twitter thread (draft)

Attach the noted media to each tweet (🎬 = animated GIF). Links: repo
`https://github.com/esonghori/narrow-corridor-llm` · gallery
`https://esonghori.com/narrow-corridor-llm/gallery/`

---

**1/** 🎬 *[attach: `docs/assets/united-states__ensemble-mean.gif`]*

@DAcemogluMIT & James A. Robinson (2024 Economics Nobel laureates) wrote *The Narrow Corridor*, mapping history in a 2D space (state power vs. society power) but never plotted a single country's path through it.

So I had LLMs do it. Here's the United States, 1789→2020, decade by decade. 🧵

📄 Paper: arxiv.org/abs/2607.18319

💻 Code: github.com/esonghori/narrow-corridor-llm

🌐 Gallery: esonghori.com/narrow-corridor-llm/gallery

---

**2/**

Method: for each decade the model first lists the key events & trends, *then* scores state and society power 0–10 on a fixed rubric, feeding prior periods forward so the path stays coherent.

---

**3/** 📈 *[attach: `paper/experiments/results/all-countries__ensemble-mean.png`]*

All 12 countries on one shared scale sort into the book's regions:

🇨🇳🇮🇷 above the corridor → **Despotic** · 🇬🇧🇫🇷🇺🇸🇮🇳🇨🇱 inside → **Shackled** · 🇨🇩🇸🇴🇱🇧 down in the weak-state region below.

One fixed 0–10 rubric is what lets you plot them all together.

---

**4/** 🎬 *[attach 2 GIFs: `docs/assets/united-kingdom__ensemble-mean.gif`, `docs/assets/china__ensemble-mean.gif`]*

The whole thesis in two clips:

🇬🇧 Britain rises *along* the diagonal and stays in the corridor: state & society growing together (the "Red Queen").
🇨🇳 China climbs straight *up* and out: a strong state over a weak society (the Despotic Leviathan).

---

**5/** 🎬 *[attach: `docs/assets/chile__ensemble-mean.gif`]*

Chile is the drama: watch it get thrown out of the corridor at the 1973 coup (society crashing, state spiking), then climb back in after the 1990 return to democracy.

---

**6/** 🎬 *[attach: `docs/assets/india__ensemble-mean.gif`]*

The new cases stress-test the framework:

🇮🇳 India climbs into the corridor: a Shackled Leviathan.
🇱🇧 Lebanon & 🇸🇴 Somalia sink into the weak-state zone, society outrunning a barely-there state.
🇿🇲 Zambia lands *inside* the corridor: one example that may surprise readers unfamiliar with its recent history.

---

**7/**

Does it mean anything? Four LLMs (Gemini 2.5 Pro, Claude Opus 4.8, GPT-5.5, and open-weight Qwen) score independently.

Against V-Dem expert codings, "society power" tracks the civil-society index well (China ρ=.89, France .87), and the models agree with each other (Krippendorff α=.66).

→ a shared, expert-consistent signal, not one model's quirk.

---

**8/**

Two caveats I lead with, not bury:
• These indices are almost certainly in the models' training data, so agreement = *consistency*, not proven accuracy.
• Coverage is thinnest for exactly the non-Western cases (Iran, China, Colombia, DR Congo, Lebanon, Somalia, Zambia): the training data is English-heavy.

---

**9/** 📊 *[attach: `paper/experiments/results_lang/lang-ablation.png`]*

Does prompting in English bias the scores? I re-ran the whole ensemble with every prompt fully translated: 🇫🇷 France in French, 🇨🇳 China in Chinese, 🇮🇷 Iran in Persian, 🇨🇱 Chile in Spanish, 🇱🇧 Lebanon in Arabic.

The paths barely move (first-difference ρ ≈ 0.86–0.99). So prompt language isn't the lever; the trajectory is driven by the history the model encodes, not the surface language.

⚠️ Caveat: the models often still *reason* in English even when prompted in another language. So this shows the prompt language isn't the bias, not that the English/Western-corpus bias is gone.
