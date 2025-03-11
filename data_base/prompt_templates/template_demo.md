[comment]:# (the [section] marker are required for specific dynamic context extensions but can be removed, if only static context is used for the prompt)
[comment]:# (each [section] allows specific variables [var/name] used by inserting them as {name} but they are all optional)
[comment]:# (all markdown comments [comment|section|var] are removed in the prompt processing)
# System prompt
- insert initial instructions here

[section/user_prompt]:# (if system and user prompt shall be separate inputs)
Example user prompt section

[section/chain_context]:# (when using an evaluation chain to provide context from previous responses)
[var/cc_id]:# (int: refers to ChainElement.step)
[var/cc_req]:# (str: a previously evaluated requirement)
[var/cc_eval]:# (str: the JSON string of a previous evaluation)
[var/cc_just]:# (str: the justification entry of a previous evaluation (`MetricEval`))
[var/cc_metric]:# (str: refers to ChainElement.metric)
[section/chain_context end]:# (end of section)
## Metric Definitions
[section/metric]:# (this section can be extended for each given metric)
[var/m_id]:# (int: e.g. 1,2,3,... | metric ID or evaluation step)
[var/m_name]:# (str: e.g. "Correctness" | metric name)
[var/m_definition]:# (str: e.g. "- is the requirement ...?" | metric definition as per `metric_definitions.json`, while the list items are formatted as bullet points)
[var/m_rating]:# (equivalent to m_definition as per `rating_definitions.json`)
### {m_id}. {m_name}
#### Definition
{m_definition}

#### Rating Scale
{m_rating}

[section/metric end]:# (end of section)

[section/few_shots]:# (removed, if `n_shots` == 0, can be extended for each given example)
Example few shots section
## Examples

[section/one_shot]:# (can be extended for each given example)
[var/os_id]:# (int: e.g. 1,2,3,...)
[var/os_rating]:# (str: e.g. "Poor" | maps rating to expression: [1,x] -> [1,3] -> {1->"Poor", 2->"Average", 3->"Excellent"})
[var/os_req]:# (str | requirement of the evaluation example)
[var/os_eval]:# (dict | evaluation example)
Example one shot section
### Example {os_id}: {os_rating} Requirement
**Requirement:**
> {os_req}

**Evaluation:**
```json
{os_eval}
```
[section/one_shot end]:# (end of section)
[section/few_shots end]:# (end of section)

## Requirement to evaluate
[comment]:# (the following variables are excluded in the `process_template` function of prompt_templates.py and can be used as general prompt template input kwargs. In the standard requirement evaluation, the input requirement is assigned to `query`.)
[var/query]:# (placeholder for the user query, e.g. the input requirement)
> {query}

[section/user_prompt end]:# (end of section)