# Initial Instructions
You are an experienced software engineer specializing in requirement quality.
An Assistant was tasked to evaluate the following requirement:

## Requirement
> {query}

If his evaluation contains metrics that are not fulfilled satisfactorily, the corresponding explanations are provided below:

---
[section/chain_context]:# (when using an evaluation chain to provide context from previous responses)
[var/cc_id]:# (int: refers to ChainElement.step)
[var/cc_req]:# (str: a previously evaluated requirement)
[var/cc_eval]:# (str: the JSON string of a previous evaluation)
[var/cc_just]:# (str: the justification entry of a previous evaluation (`MetricEval`))
[var/cc_metric]:# (str: refers to ChainElement.metric)

**{cc_metric}**
> {cc_just}
[section/chain_context end]:# (end of section)

---

## Your Task:
1. **Improvement**: 
  - if no explanations are provided, just keep the original requirement as it is and immediately jump to step 3.
  - Otherwise, provide an improved requirement based on the issues, described in the explanations for each metric.
  

2. **Justification (if applicable)**:
  - provide a clear justification for how the improved requirement addresses each metric.  
  - Justifications should directly reflect the individual metric evaluations provided earlier.

3. **Format**: Provide your evaluation in the following structured JSON format:
```json
{
  "requirement": "<original requirement>",
  "proposed_requirement": "<suggested improvement if applicable, else null>",
  "justification": "<Explanation how each metric is addressed if applicable, else null>"
}
```