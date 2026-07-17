# AEGIS Secure – Runtime Specialist

# Part 3 – Intelligence Layer, Evidence Builder, Prompt Engineering, Model Architecture & Runtime Reasoning Pipeline

---

# 24. Transition from Browser Observation to Intelligence

At this stage the Runtime Specialist had become capable of observing almost every important browser behavior.

It could collect

* Network Requests
* JavaScript Execution
* Console Errors
* Browser Dialogs
* Runtime DOM
* Forms
* Browser Storage
* Browser Permissions

However...

just like Infrastructure,

it still had **zero intelligence**.

It only knew

> **What happened**

It still could not answer

> **What does it mean?**

This distinction completely shaped the second half of the Runtime architecture.

---

# 25. Runtime is NOT a Browser

This sounds obvious,

but it became one of the most important design realizations.

Initially we thought

```text
Browser

↓

Collect Everything

↓

Return Everything
```

Immediately another problem appeared.

The browser produces

millions

of events.

Example

```text
Network

↓

250 Requests

↓

250 Responses

↓

50 Images

↓

20 CSS

↓

30 JavaScript

↓

15 XHR

↓

10 Fetch

↓

3 WebSockets

↓

Thousands of Console Messages
```

If we directly fed all of this into an LLM

the prompt would explode.

The model would spend

95%

of its computation

reading

instead of

reasoning.

Therefore another architecture was needed.

---

# 26. Birth of preprocessing.py

Exactly like Infrastructure,

Runtime also required

a preprocessing layer.

Initially collectors directly returned

```python
{

requests:[...]

responses:[...]

storage:[...]

forms:[...]

...

}
```

Immediately prompts became

```text
7000+

tokens.
```

This was unacceptable.

So Runtime adopted exactly the same philosophy.

```text
Collectors

↓

Raw Runtime Evidence

↓

Preprocessing

↓

Compact Runtime Evidence
```

---

# 27. Responsibilities of preprocessing.py

This file became

the Runtime Data Engineer.

Its responsibility is

```text
Normalize

↓

Aggregate

↓

Compress

↓

Remove Redundancy

↓

Prepare LLM Evidence
```

Notice

it still performs

NO

reasoning.

---

For example

instead of

```python
requests=[

250 entries

]
```

it computes

```python
{

request_count:250,

third_party_requests:91,

failed_requests:8,

xhr_requests:19,

fetch_requests:12

}
```

Immediately

250 network objects

become

5 numerical features.

---

Similarly

instead of

```python
console_logs=[...]

```

it computes

```python
{

console_errors:2,

console_warnings:4

}
```

Again

compression.

---

Storage

Instead of

```python
localStorage={

30 Keys

}
```

↓

```python
{

local_storage_keys:30,

local_storage_size:1204

}
```

Everything became

small

clean

structured.

---

# 28. Runtime Evidence Compression Philosophy

One design principle guided preprocessing.

> **The LLM does not need raw browser events.**

It needs

meaningful evidence.

For example

instead of

```text
Request #1

Request #2

Request #3

...

Request #210
```

we expose

```text
210 Requests

19 Failed

15 Third Party Domains

2 Downloads

1 WebSocket
```

The model now reasons much faster.

---

# 29. Why Compression Matters

Suppose Google loads

```text
Google Fonts

Analytics

Images

Ads

Maps

APIs

...
```

Hundreds

of requests.

Feeding everything

would waste

thousands

of tokens.

Compression converts

```text
Huge Browser Trace

↓

Runtime Profile
```

This profile is exactly what the Runtime Specialist reasons over.

---

# 30. Runtime Evidence Builder

Another architectural question appeared.

Who actually coordinates

all Runtime collectors?

Initially

predictor.py

looked like

```python
network()

javascript()

forms()

storage()

permissions()

...
```

Immediately rejected.

Exactly like Infrastructure,

predictor

should never know

how evidence is collected.

Instead

```text
Predictor

↓

Evidence Builder

↓

Collectors
```

---

# 31. Responsibilities of evidence_builder.py

This file became

the Runtime Orchestrator.

Responsibilities

```text
Launch Browser

↓

Navigate

↓

Run Collectors

↓

Merge Outputs

↓

Preprocess

↓

Return Runtime Evidence
```

Notice

this file never

loads

the model.

Never

builds prompts.

Never

predicts.

Only orchestration.

---

# 32. Why Browser Sharing Became Important

Initially

every collector launched

its own browser.

Example

```text
Network

↓

Launch Chromium

↓

Collect

Forms

↓

Launch Chromium

↓

Collect

Storage

↓

Launch Chromium

↓

Collect
```

Terrible.

The same page

loaded

five times.

Memory

multiplied.

Execution

multiplied.

Runtime

became

extremely slow.

---

We therefore redesigned

everything.

One browser.

One page.

Five collectors.

```text
Browser

↓

Page

↓

Network

↓

JavaScript

↓

Forms

↓

Storage

↓

Permissions
```

This became

one of the biggest

performance improvements.

---

# 33. Why Everything Became Async

Initially

collectors executed

sequentially.

```text
Network

↓

JavaScript

↓

Forms

↓

Storage

↓

Permissions
```

Although

browser reuse

reduced overhead,

execution was still slower than necessary.

We therefore decided

every collector

should become

asynchronous.

Architecture

```python
await asyncio.gather(

network(),

javascript(),

forms(),

storage(),

permissions()

)
```

Now

while JavaScript

waits,

network

can still collect,

storage

can inspect,

permissions

can query,

forms

can analyze.

The browser becomes

fully utilized.

---

# 34. Prompt Engineering

The Runtime prompt

went through

many revisions.

Initially

```text
Analyze browser behavior.
```

Immediately

hallucinations.

The model

started inventing

browser events.

---

We therefore strengthened

the instructions.

Eventually

the prompt included

```text
You are

Runtime Specialist.

Use ONLY

provided evidence.

Never invent

requests.

Never invent

JavaScript execution.

Never infer

network traffic

that was not observed.

If evidence

is missing,

explicitly state

Missing Evidence.
```

This dramatically

improved consistency.

---

# 35. Runtime JSON Schema

Exactly like Infrastructure,

Runtime

needed

structured output.

Eventually

every Runtime report

followed

```json
{

module,

prediction,

confidence,

risk_score,

summary,

positive_indicators,

negative_indicators,

missing_evidence

}
```

This ensured

Fusion

could consume

every specialist

using

the same interface.

---

# 36. predictor.py

This file

became

the Runtime Brain.

Responsibilities

```text
Load Model

↓

Load Tokenizer

↓

Load Prompt

↓

Build Runtime Evidence

↓

Tokenize

↓

Generate

↓

Decode

↓

Extract JSON

↓

Return Runtime Report
```

Exactly

the same architecture

as Infrastructure.

This symmetry

was intentional.

Every specialist

should look

architecturally identical.

---

# 37. Why Runtime Reused Infrastructure Architecture

One major engineering goal

was consistency.

Infrastructure

and Runtime

should differ

only

in evidence.

Not

architecture.

Both therefore contain

```text
Collectors

↓

Preprocessing

↓

Evidence Builder

↓

Prompt

↓

Predictor

↓

Evaluate
```

This dramatically

reduces maintenance.

Developers

can understand

every specialist

almost immediately.

---

# 38. evaluate.py

Initially

evaluate.py

simply accepted

user input.

Later

we realized

benchmarking

requires

fixed test cases.

Eventually

evaluate.py

became

a testing framework.

Example

```text
Google

Github

Microsoft

Cloudflare

Known Phishing Samples

Internal Test URLs
```

This allows

consistent comparison

between

different prompts

and

different models.

---

# 39. Runtime Evaluation Philosophy

Evaluation

is not

about

accuracy alone.

It also measures

```text
Evidence Collection Time

↓

Browser Startup Time

↓

Navigation Time

↓

JavaScript Execution Time

↓

Inference Time

↓

Total Runtime
```

These measurements

became essential

because Runtime

is significantly more expensive

than Infrastructure.

---

# 40. Runtime Model

Initially

Runtime

was expected

to use

the same

Qwen2.5-1.5B-Instruct

model

as Infrastructure.

This simplified

deployment,

reduced maintenance,

and ensured

consistent output quality.

Because

all specialists

share

the same JSON schema,

Fusion

does not need

special handling

for different models.

---

# 41. Runtime Pipeline

After months

of redesign,

the Runtime pipeline

stabilized into

```text
URL

↓

Browser Manager

↓

Chromium

↓

Navigate

↓

JavaScript Executes

↓

Network Collector

↓

JavaScript Collector

↓

Forms Collector

↓

Storage Collector

↓

Permissions Collector

↓

Preprocessing

↓

Evidence Builder

↓

Prompt Construction

↓

Qwen Runtime Specialist

↓

JSON Extraction

↓

Runtime Report
```

Notice something remarkable.

The browser

is completely isolated

from

the model.

The browser

never reasons.

The model

never touches

the browser.

They communicate

only

through

structured evidence.

---

# 42. Runtime Specialist as an AI Browser Analyst

By the end of development,

the Runtime Specialist

had evolved into something much larger than a browser automation script.

It became

an autonomous

AI-powered

browser behavior analyst.

It does not merely

visit a webpage.

It observes

how the webpage behaves,

organizes those observations into structured evidence,

compresses them into a concise runtime profile,

and finally reasons over that profile to produce an explainable assessment.

Just as the Infrastructure Specialist became an expert in Internet infrastructure,

the Runtime Specialist became an expert in **live browser execution**, laying the foundation for dynamic phishing analysis within the AEGIS Secure multi-agent architecture.

---

**End of Part 3**

Part 4 covers the complete **engineering journey** of the Runtime Specialist:

* why browser reuse became mandatory,
* why everything was redesigned to be asynchronous,
* JavaScript instrumentation decisions,
* Playwright limitations,
* Cloudflare and dynamic-page challenges,
* timeout strategies,
* memory considerations,
* why some proposed files were merged or removed,
* and the evolution toward a distributed deployment architecture.

Continue to [Part 4 – Engineering Journey](./PART_4_ENGINEERING_JOURNEY.md).
