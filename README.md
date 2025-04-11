# Visualize Narrow Corridor with AI

Daron Acemoğlu and James A. Robinson's book, The Narrow Corridor: States, Societies, and the Fate of Liberty, proposes a framework for tracing a country's historical trajectory within a two-dimensional space defined by state and societal power. However, the authors did not offer concrete visualizations in the book, acknowledging the difficulty of assigning quantitative values to the relative power of state and society at different historical junctures for any given nation. Historians and humanities researchers are acutely aware of the inherent biases and subjective interpretations involved in historical analysis, as well as the complexities of reducing nuanced state-society power dynamics to numerical values.

This work attempts to address this challenge by employing a Large Language Model (LLM). Our approach involves using the LLM to extract significant historical events and trends for a specific country and subsequently leveraging this information to assign values representing state and societal power, enabling a visualization of the country's path in the style of the Narrow Corridor framework.

While we recognize the potential for biases stemming from the LLM's training data, and the tendency of such models to perpetuate these biases, particularly with limited or similarly biased training data, we posit that careful application of LLMs can offer a less biased quantitative assessment of historical power dynamics than any individual expert.

# How to Use

1.  Obtain your Google Cloud API key to access the Gemini model APIs.
1.  Set the arguments of the get_narrow_corridor function to define your desired historical path. For example:
	```
	country: str = "Iran (Persia)"
	start_year: int = 1870
	end_year: int = 2025
	step_years: int = 5
	```
1. Utilize the plot_path function to visualize the generated historical trajectory of the specified country.

