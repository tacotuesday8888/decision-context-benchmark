# Decision Context Benchmark

A research project on whether knowing the user’s task helps AI models detect prompt injection: text that tries to redirect an assistant.

## What I tested

I compared Jev and other decision models with general-purpose language models, testing detection with and without task information.

The data include 761 task–text combinations from AgentDojo, AgentDyn and InjecAgent, and 3,000 clean/attacked page pairs from BrowseSafe++. GPT-6.1 Sol was tested on 500 of those page pairs. There are also smaller checks using other sources. [Data and model details](../DATA.md)

## What I found

Task information did not always help. On BrowseSafe++, Jev made fewer false alarms but missed more attacks. GPT-6 Luna and GPT-6.1 Sol made more errors on average with task information. These results apply to the tested data and settings.

## Files

- [Results](../docs/paper-preparation/README.md)
- [Methods and related work](../docs/critical-review/METHODS-NOTE.md)
- [How to check the results](../REPRODUCING.md)

Code is in `scripts/`, notes in `docs/`, and results in `results/`. The paper is not written yet.
