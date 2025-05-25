# Visualize Narrow Corridor using Generative Artificial Intelligence (AI).

In **The Narrow Corridor: States, Societies, and the Fate of Liberty, Daron Acemoglu and James A. Robinson** [[1]](#1) propose a framework for analyzing a country's historical trajectory within a two-dimensional space defined by the relative power of the state and society. While the book lays out this conceptual model, it does not include any concrete visualization example.

A major challenge in visualizing such dynamics lies in the difficulty of assigning quantitative values to the state and society's power at different historical moments. Historians and scholars in the humanities are well aware of the inherent biases, subjective interpretations, and the complexity involved in reducing nuanced power dynamics to numerical values.

This project addresses that challenge by employing a **Large Language Model (LLM)** [[4]](#4) to generate visualizations of historical trajectories. Our approach involves prompting the LLM to identify significant historical events and trends for a specific country in a historical period, and then using that information to assign numerical values for state and society power, allowing us to visualize the country's path in the spirit of the Narrow Corridor framework.

We acknowledge the risks of bias in LLMs, especially those inherited from their training data. However, we argue that, with careful prompt engineering and systematic methodology, LLMs can offer a more scalable and potentially less biased alternative to purely expert-driven approaches.

# Methodology

To improve the accuracy and relevance of the numerical values for state and society power, we apply the Chain-of-Thought technique [[3]](#3). For each historical period (e.g., a 5-year span), the LLM is first asked to identify major events and trends. This contextual narrative is then included in the next prompt, which asks the model to assign quantitative values for state and society power during that period.

To ensure consistency across time periods, we also use In-Context Learning [[4]](#4). Beginning from the earliest year, we provide the model with prior period values when predicting the next, thereby anchoring its output and improving temporal coherence.

# How to Use

1.  **Obtain a Google Cloud API key** to access Gemini model APIs.
1.  **Configure the parameters** for the `get_narrow_corridor` function to define the desired historical range. For example:
	```
	country: str = "Iran (Persia)"
	start_year: int = 1870
	end_year: int = 2025
	step_years: int = 5
	```
1. **Visualize the results** using the `plot_path` function, which renders the country's historical trajectory in the state-society power space.


# Example

As an example, we analyzed Iran (Persia) from 1870 to 2025 in 5-year intervals. You can find the corresponding Gemini (gemini-2.0-flash) prompts and responses [here](./example/Iran%20(Persia)%201880-2025%20promot%20and%20response.txt).

![Iran's path from 1880 to 2025](./example/Iran%20(Persia)%201880-2025.png).


# How to cite

If you use this code, please cite this:

```
@misc{CircuitTraining2021,
  title = {Visualize Narrow Corridor using Generative Artificial Intelligence.},
  author = {M. Songhori, Ebrahim},
  howpublished = {\url{https://github.com/esonghori/visualize_narrow_corridor_with_ai}},
  url = "https://github.com/esonghori/visualize_narrow_corridor_with_ai",
  year = 2025,
  note = "[Online; accessed 25-May-2025]"
}
```

# Refrences
- <a id="1">[1]</a> Acemoglu, Daron, and James A. Robinson. The Narrow Corridor: States, Societies, and the Fate of Liberty. Penguin Books, 2019. 
- <a id="2">[2]</a> Kaplan, Jared, Sam McCandlish, Tom Henighan, Tom B. Brown, Benjamin Chess, Rewon Child, Scott Gray, Alec Radford, Jeffrey Wu, and Dario Amodei. "Scaling laws for neural language models." arXiv preprint arXiv:2001.08361 (2020).
- <a id="3">[3]</a> Wei, Jason, Xuezhi Wang, Dale Schuurmans, Maarten Bosma, Fei Xia, Ed Chi, Quoc V. Le, and Denny Zhou. "Chain-of-thought prompting elicits reasoning in large language models." Advances in neural information processing systems 35 (2022): 24824-24837.
- <a id="4">[4]</a> Brown, Tom, Benjamin Mann, Nick Ryder, Melanie Subbiah, Jared D. Kaplan, Prafulla Dhariwal, Arvind Neelakantan et al. "Language models are few-shot learners." Advances in neural information processing systems 33 (2020): 1877-1901.