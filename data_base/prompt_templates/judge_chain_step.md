## Instructions
You are tasked with evaluating the correctness of an assessment made by a small language model (SLM) for a software requirement. Your evaluation must follow the structured output format below, taking into account the provided metric definition and rating scale.

## Input Data
### Metric Definition
[section/metric]:# (this section can be extended for each given metric)
#### {m_name}
{m_definition}

#### Rating Scale
{m_rating}

[section/metric end]:# (end of section)  

### SLM's Evaluation
```json
{query}
```


## Your Task
Evaluate the SLM's assessment by analyzing the given justification and comparing it with the metric definition and rating scale. Your response must include:  

### Accuracy of Rating 
Rate the accuracy of the SLM's rating using a numerical score (1-5):  
- **1 - Very Poor**: The rating does not align with the metric definition and scale; it is significantly flawed and incorrect.  
- **2 - Poor**: The rating shows minimal alignment with the metric definition and scale, with major discrepancies or misunderstandings.  
- **3 - Average**: The rating aligns moderately with the metric definition and scale but contains some notable issues or lacks consistency.  
- **4 - Good**: The rating aligns well with the metric definition and scale, with only minor discrepancies or areas for improvement.  
- **5 - Excellent**: The rating perfectly aligns with the metric definition and scale, with no discrepancies.


### Quality of Justification
Rate the quality of the justification using a numerical score (1-5):  
- **1 - Very Poor**: The justification does not support the rating and is either irrelevant, incoherent, or lacks any meaningful depth.  
- **2 - Poor**: The justification minimally supports the rating, but it is shallow, unclear, or misses key elements of the metric definition.  
- **3 - Average**: The justification partially supports the rating, addressing some key criteria, but it is incomplete or somewhat unclear.  
- **4 - Good**: The justification mostly supports the rating, addressing most key criteria effectively, with only minor gaps or ambiguities.  
- **5 - Excellent**: The justification fully supports the rating, addressing all key criteria comprehensively and with clarity.


### Comments 
Provide an Explanation for each rating.

## Response Format
Use the following json Format to structure your response:

```json
{
  "accuracy_of_rating": <1-5>,
  "comment_on_accuracy": "<Explanation of the chosen rating>",
  "quality_of_justification": <1-5>,
  "comment_on_quality": "<Explanation of the chosen rating>"
}
```