# Initial Instructions
You are an experienced software engineer specializing in requirement quality.
An Assistant was tasked to evaluate a requirement.
In the evaluation process, the requirement was analyzed based on the following metrics: 
[section/metric]:# (this section can be extended for each given metric)
- {m_name}
[section/metric end]:# (end of section)

For each metric, this was his individual evaluation:
[section/chain_context]:# (when using an evaluation chain to provide context from previous responses)
[var/cc_id]:# (int: refers to ChainElement.step)
[var/cc_req]:# (str: a previously evaluated requirement)
[var/cc_eval]:# (str: the JSON string of a previous evaluation)
[var/cc_metric]:# (str: refers to ChainElement.metric)
**{cc_metric}**
```JSON
{cc_eval}
```
[section/chain_context end]:# (end of section)

## Your Task:
1. **Improvement**: 
  - Use the evaluations above to provide a **single improved requirement** that addresses issues across all metrics.  
  - Ensure the improved requirement is concise and precise, including only essential details that meet the metric definitions. Avoid unnecessary elaboration.

2. **Justification**:
  - Provide a clear justification for how the improved requirement addresses each metric.  
  - Justifications should directly reflect the individual metric evaluations provided earlier.

3. **Format**: Provide your evaluation in the following structured JSON format:
```json
{
  "requirement": "<original requirement>",
  "proposed_requirement": "<suggested improvement>",
  "justification": {
[section/metric]:# (this section can be extended for each given metric)
    "{m_name}":"<explanation>",
[section/metric end]:# (end of section)
  }
}
```

## Example
```json
{
  "requirement": "The system should provide user authentication functionality.",
  "proposed_requirement": "The system shall authenticate users via a secure login process with email and password, adhering to OWASP standards.",
  "justification": {
    "correctness": "The improved requirement defines a genuine system need (user authentication), specifies a feasible implementation (secure login with email and password), and is verifiable by testing compliance with OWASP standards.",
    "unambiguity": "The wording is clear and understandable, with no room for multiple interpretations. Technical terms like 'secure login' and 'OWASP standards' are specific and unambiguous.",
    "completeness": "The improved requirement specifies the authentication method (email and password) and the compliance standard (OWASP), making it comprehensive.",
    "consistency": "The requirement is logically consistent, with no contradictions between components. It aligns with typical security protocols.",
    "precision": "The improved requirement avoids vague terms and specifies exact methods and standards, ensuring precision.",
    "verifiability": "The requirement is verifiable through security audits and functional testing of the login process against OWASP standards.",
    "atomicity": "The improved requirement addresses a single function (user authentication) without conflating multiple features or systems."
  }
}
```
### Key Takeaways from Example:  
From this example, note the following key takeaways for improvement:  
1. **Conciseness**: The improved requirement is brief yet fully addresses issues across all metrics.  
2. **Essential Details Only**: Unnecessary elaboration (e.g., listing every OWASP guideline) is avoided while retaining specificity.  
3. **Alignment with Metrics**: Each justification clearly demonstrates how the improvement meets the metric's criteria.  

When creating your final improved requirement, focus on incorporating essential corrections while ensuring the statement remains as short and direct as possible.