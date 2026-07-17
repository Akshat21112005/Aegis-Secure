# AEGIS Secure – Runtime Specialist

# Part 4 – Engineering Journey, Problems Faced, Design Evolution, Performance Optimizations and Distributed Architecture

---

# 43. Beginning of Runtime Development

When the Runtime Specialist was first proposed, we assumed it would be significantly simpler than the Infrastructure Specialist.

The initial idea looked like

```text
URL

↓

Playwright

↓

Observe

↓

LLM
```

Essentially,

we thought

Playwright would automatically expose everything we needed.

Within the first day we realized

this assumption was completely wrong.

A browser is an extremely complex system.

Unlike Infrastructure,

where every collector independently queries external services,

Runtime depends entirely on

one

live

executing

browser.

Immediately,

architecture became the biggest challenge.

---

# 44. The Browser Bottleneck

The first implementation looked something like

```text
Network Collector

↓

Launch Browser

↓

Collect

↓

Close Browser



JavaScript Collector

↓

Launch Browser

↓

Collect

↓

Close Browser



Forms Collector

↓

Launch Browser

↓

Collect

↓

Close Browser
```

Every collector launched Chromium independently.

At first this seemed modular.

Unfortunately,

it was a disaster.

---

## Problems

Every collector

loaded

the webpage again.

Meaning

```text
Google

↓

5 Browser Launches

↓

5 Navigations

↓

5 JavaScript Executions

↓

5 Network Traces
```

Memory usage exploded.

Execution time exploded.

Network requests became duplicated.

Collectors no longer observed the same browser state.

---

Imagine

Collector A

runs

before login popup.

Collector B

runs

after popup.

They now disagree.

The architecture became inconsistent.

---

# 45. Browser Sharing

This became one of the most important redesigns.

Instead of

```text
Collector

↓

Browser
```

we inverted it.

```text
Browser

↓

Collectors
```

One browser.

One page.

One execution.

Multiple observers.

The architecture became

```text
Browser

↓

Chromium

↓

Context

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

Every collector now observes

exactly

the same execution.

---

Advantages

No duplicate rendering.

No duplicate requests.

No duplicate JavaScript execution.

Memory reduced dramatically.

Execution became deterministic.

---

# 46. Why Page Object Became the Heart of Runtime

During Infrastructure,

every collector accepted

```python
url
```

Runtime

is completely different.

Every collector now accepts

```python
page
```

This small decision

changed

the entire architecture.

The page object contains

everything.

DOM

Cookies

Storage

Network

JavaScript

Permissions

Execution Context

Console

Dialogs

Downloads

Workers

Every Runtime collector simply inspects

the same

browser page.

---

# 47. The Async Revolution

Initially,

collectors executed sequentially.

```text
Browser

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

Although browser sharing improved performance,

execution still felt unnecessarily slow.

Most collectors

spent

their time

waiting.

Waiting for JavaScript.

Waiting for browser APIs.

Waiting for Playwright.

The CPU remained idle.

---

We therefore redesigned

everything

around

asynchronous execution.

Instead of

```python
network()

javascript()

forms()

storage()

permissions()
```

we moved towards

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

while

network

is waiting for responses,

forms

can inspect the DOM.

Storage

can read LocalStorage.

Permissions

can query browser APIs.

JavaScript

can collect runtime hooks.

Every collector progresses simultaneously.

---

This single redesign

reduced overall Runtime latency dramatically

without changing

collector logic.

---

# 48. JavaScript Instrumentation

One of the longest engineering discussions

during Runtime development

was

How should we observe JavaScript?

Initially

we considered

creating

```text
hooks.js
```

that would inject

hundreds

of browser hooks.

Example

```text
eval

fetch

XMLHttpRequest

WebSocket

document.write

history

window.open

clipboard

postMessage
```

This would require

another directory

another build system

another injection layer.

---

Eventually

we rejected

that architecture.

Reason

Unnecessary complexity.

Instead,

everything

was placed directly inside

```text
javascript_runtime.py
```

The collector itself

injects

its own hooks.

One file.

Self-contained.

Easy to maintain.

Easy to understand.

---

# 49. Runtime vs Static JavaScript

Another major confusion

appeared.

Infrastructure already had

```text
script_analysis.py
```

Runtime

needed

```text
javascript_runtime.py
```

Initially

both seemed

to perform

JavaScript analysis.

After several discussions,

we realized

they answer

completely different questions.

Infrastructure asks

```text
What does the source code contain?
```

Runtime asks

```text
What actually happened?
```

One reads.

One executes.

This distinction

became one of the strongest architectural decisions

in AEGIS Secure.

---

# 50. Network Collector Evolution

Initially,

Runtime networking

was split into

```text
requests.py

responses.py

downloads.py

redirects.py
```

Every file

looked clean

individually.

Together,

they became

impossible to coordinate.

Every network event

belongs

to one

request lifecycle.

Splitting them

destroyed

context.

---

Eventually,

everything merged into

```text
network.py
```

One collector.

Complete request lifecycle.

Request

↓

Response

↓

Redirect

↓

Download

↓

Completion

Much simpler.

Much more maintainable.

---

# 51. Forms Collector Evolution

Initially,

Forms

were considered

part of HTML.

Exactly like Infrastructure.

Later,

we discovered

JavaScript

creates forms

after

page load.

Infrastructure

never sees them.

Runtime

does.

Forms therefore became

an independent Runtime collector.

This separation

allows

dynamic phishing kits

to be detected.

---

# 52. Storage Collector Evolution

Originally,

cookies

were considered

sufficient.

Then we realized

modern phishing websites

store

far more

than cookies.

Examples

```text
Local Storage

Session Storage

IndexedDB

Cache API

Service Workers
```

All of these

became

the responsibility

of

storage.py.

---

# 53. Permissions Collector Evolution

Initially,

permissions

were ignored.

Later,

we realized

browser permissions

often reveal

intent.

Examples

```text
Camera

Clipboard

Notifications

Geolocation
```

A login page

requesting

Bluetooth

or

USB

is unusual.

Rather than

hardcoding

rules,

we simply expose

permission states.

Again

Collectors observe.

Models reason.

---

# 54. Timeouts

Timeouts

became

another surprisingly difficult problem.

Initially

we used

```python
30000
```

milliseconds.

We later discussed

what

30000

actually means.

Eventually

timeouts

were separated into

```text
Navigation Timeout

Action Timeout

JavaScript Wait
```

instead of

one giant timeout.

This provides

finer control

over browser execution.

---

# 55. Dynamic Websites

Unlike Infrastructure,

Runtime

cannot assume

a webpage

ever finishes loading.

Examples

```text
Live Dashboards

Infinite Scrolling

Streaming Websites

SPAs

React

Angular

Vue

WebSockets

Polling APIs
```

Waiting forever

is impossible.

Therefore,

Runtime eventually adopted

controlled waiting

followed by

evidence collection,

rather than insisting

on a perfectly "finished" page.

---

# 56. Cloudflare Challenges

Another issue

was

anti-bot protection.

Examples

```text
Cloudflare

Turnstile

CAPTCHA

JavaScript Challenges
```

Some websites

never expose

their real content

to automated browsers.

Rather than bypassing these protections,

the Runtime Specialist records

what it actually observes.

If execution is blocked,

that becomes part of the evidence instead of being hidden.

---

# 57. Memory Constraints

One of the biggest practical limitations

came from hardware.

Your development machine

contained

approximately

4 GB

of GPU memory.

Initially,

we planned

to keep

multiple models

loaded simultaneously.

Very quickly,

we discovered

this was impossible.

Each

1.5B parameter

instruction model

occupied

roughly

4 GB

by itself.

Infrastructure

*

Runtime

*

Semantic

*

OCR

could never coexist

locally.

---

# 58. Distributed Deployment

This limitation

completely changed

AEGIS Secure's deployment strategy.

Instead of

```text
One Machine

↓

Four Models
```

we moved toward

```text
Infrastructure Specialist

↓

Dedicated Hugging Face Space



Runtime Specialist

↓

Dedicated Hugging Face Space



Semantic Specialist

↓

Dedicated Hugging Face Space



OCR Specialist

↓

Dedicated Hugging Face Space
```

Each specialist

owns

its own

model,

its own

dependencies,

its own

memory.

---

# 59. Parallel Specialist Execution

This naturally led to

another optimization.

Instead of

```text
Infrastructure

↓

Runtime

↓

Semantic

↓

OCR
```

executing sequentially,

the backend

will launch

all specialists

concurrently.

Conceptually,

the flow becomes

```python
await asyncio.gather(

infrastructure(),

runtime(),

semantic(),

ocr()

)
```

Once every specialist finishes,

their structured reports are collected and passed to the Fusion Specialist.

This turns AEGIS Secure into a distributed, asynchronous multi-agent system where latency is determined by the slowest specialist rather than the sum of all specialists.

---

# 60. Runtime as an Independent AI Agent

By the end of its evolution,

the Runtime Specialist was no longer just a Playwright automation script.

It had become an independent AI agent with a clearly defined responsibility.

Its workflow is

```text
Observe Browser

↓

Collect Behaviour

↓

Normalize Evidence

↓

Compress Evidence

↓

Reason

↓

Explain
```

It does not know

WHOIS.

It does not know

DNS.

It does not know

OCR.

It knows

only

browser behaviour.

That specialization is precisely what makes the overall AEGIS Secure architecture scalable, explainable, and extensible.

---

**End of Part 4**

Part 5 concludes the Runtime Specialist documentation with:

* the finalized Runtime file tree,
* complete end-to-end data flow,
* architecture diagrams,
* interaction with Infrastructure, Semantic, OCR, and Fusion,
* future roadmap,
* research contributions,
* engineering lessons,
* and the final Runtime Specialist blueprint within the complete AEGIS Secure ecosystem.

Continue to [Part 5 – Final Runtime Architecture](./PART_5_FINAL_ARCHITECTURE.md).
