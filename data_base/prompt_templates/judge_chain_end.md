## Instructions
You are tasked with evaluating an improved requirement suggestion provided by a small language model (SLM). The improved requirement should align with the definitions of all given metrics as closely as possible. Your evaluation must include a numerical score for overall alignment with the metrics and actionable suggestions for further improvement.

## Input Data
### Metric Definitions 
[section/metric]:# (this section can be extended for each given metric)

#### {m_name}
{m_definition}

[section/metric end]:# (end of section)

### SLM's Improvement Suggestion
```json
{query}
```

## Your Task
Evaluate the improved requirement based on the metric definitions provided. Your evaluation must include:  
### Overall Alignment with Metrics
Rate the improved requirement's alignment with the metrics using a numerical score (1-5):  
- **1 - Very Poor**: The requirement fails to align with most of the metrics and does not address key issues.  
- **2 - Poor**: The requirement aligns with a few metrics but has significant gaps or weaknesses.  
- **3 - Average**: The requirement aligns moderately well with the metrics but still has notable gaps or areas for improvement.  
- **4 - Good**: The requirement aligns well with most metrics, with only minor issues remaining.  
- **5 - Excellent**: The requirement aligns perfectly with all metrics and addresses key issues comprehensively.  

### Comment 
Provide an Explanation for the rating.  

## Response Format
```json
{
  "overall_alignment_with_metrics": "(int:<1-5>)",
  "comment": "<Explanation of the chosen rating>"
}
```