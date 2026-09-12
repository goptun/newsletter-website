## Purpose

Collects real, recent tech news and uses the LLM (via 9Router) to generate a daily newsletter draft edition that follows the owner's reference newsletter structure, without sponsored content or added editorial commentary.

## ADDED Requirements

### Requirement: Daily draft generation
The system SHALL generate one draft edition per day automatically on a schedule, without requiring a manual trigger to start generation.

#### Scenario: Scheduled generation produces a draft
- **WHEN** the daily generation schedule triggers
- **THEN** the system collects candidate news items and produces one draft edition stored for review

### Requirement: Real, sourced news only
The system SHALL only include news items backed by an actually fetched source, and SHALL NOT fabricate news, facts, sources, or links.

#### Scenario: No real news available
- **WHEN** no relevant, verifiable news items can be retrieved for the day
- **THEN** the system does not fabricate content and instead marks the draft as incomplete/failed for manual attention

### Requirement: Reference structure compliance
Each draft SHALL contain: a subject line summarizing 2-3 top stories, an opening "Curiosidade do dia" section, followed by one paragraph per selected news item, each ending with a sentence attributing the original source.

#### Scenario: Draft follows structure
- **WHEN** a draft is generated
- **THEN** it contains a subject line, a "Curiosidade do dia" opening paragraph, and one or more news paragraphs each ending in a sentence attributing the source

### Requirement: No sponsored content
The system SHALL NOT include sponsored/advertisement content in the draft, including any teaser segment appended after the "Curiosidade do dia" fact.

#### Scenario: Sponsored segment stripped
- **WHEN** the "Curiosidade do dia" section is generated
- **THEN** the output does not include a sponsored teaser sentence appended after the curiosity fact

### Requirement: No editorial commentary per news item
Each news paragraph SHALL contain only objective, factual summary content plus the closing source-attribution sentence, and SHALL exclude added editorial opinion or commentary about the news.

#### Scenario: Objective news paragraph
- **WHEN** a news paragraph is generated
- **THEN** the paragraph reports only factual summary content and ends with a source attribution, without an added personal or editorial remark

### Requirement: News selection criteria
The system SHALL select news items for the draft prioritizing relevance, recency, source quality, topic diversity, and usefulness to the reader.

#### Scenario: Selection reflects criteria
- **WHEN** multiple candidate news items are available for the day
- **THEN** the draft's selected items reflect varied topics and reputable sources rather than an arbitrary subset

### Requirement: Generation via 9Router
The system SHALL use the existing 9Router LLM gateway to generate the draft's narrative text (the "Curiosidade do dia" write-up and the news summaries).

#### Scenario: Content generated through 9Router
- **WHEN** the system generates the draft's narrative text
- **THEN** the generation request is served by the 9Router-backed LLM client
