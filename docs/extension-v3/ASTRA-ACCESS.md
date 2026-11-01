# How Astra was evaluated

Astra was evaluated through fresh, standalone requests to OpenAI's API endpoint.
This working Codex chat did not read the benchmark examples and assign Astra's
saved predictions itself. The harness sent the frozen question and example content
to `gpt-6-astra` and preserved the returned responses.

The completed route used separately authorized project subscription OAuth, **not
`OPENAI_API_KEY`**. Its endpoint was `api.openai.com/v1/responses`. This was the
frozen route; we have not relabeled it as API-key access or silently switched it.

A direct inspection of all 1,771 saved Astra requests found:

- One user input per request, with the frozen instructions/settings.
- `store:false` on every request.
- No `previous_response_id` or conversation link on any request.
- Only the intended candidate/task information for that condition, without this
  working chat's history or a previous benchmark answer supplied as context.

These are separate evaluation requests, not proof of a separate physical model
instance. The records do not identify hardware, serving workers or Azure
infrastructure, and no such claim is made. The examples share tasks/texts/templates,
so requests are not 1,771 statistically independent observations. Shared model-family
training or biases with the working assistant or another judge remain possible.
Switching from OAuth to an API key does not itself remove shared-model bias.

Astra made 1,771 confirmation attempts: 1,768 valid answers and 3 preserved transport
failures. Successful responses reported 786,259 input tokens and 40,965 output tokens;
failed-call usage is unknown. Its subscription route had zero incremental metered
API charge, which is not equivalent to zero model use or unlimited quota.

Subscription access remains authorized. No route change, subscription cancellation or
extra paid check is required merely to make this study traceable. Any future route
comparison would need its own hypothesis, versioned settings and cost review; it
would not turn exposed examples into fresh confirmation data.
