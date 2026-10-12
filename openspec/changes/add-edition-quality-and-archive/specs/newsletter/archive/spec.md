## Purpose

Exposes newsletter editions to the public — the source-URL-enriched latest-edition API consumed by `portfolio-website`, and a server-rendered archive of past sent editions.

## ADDED Requirements

### Requirement: Source URL Exposure
The system SHALL persist each news item's original source URL alongside the edition it belongs to, and expose it via the public latest-edition API as an additive field that does not remove or restructure any existing field.

#### Scenario: Latest edition includes source URLs
- **WHEN** a client requests the latest sent edition and that edition has stored source URLs
- **THEN** the response includes each news item's source URL alongside the existing `subject`, `body`, and `sent_at` fields

#### Scenario: Older edition without stored source URLs
- **WHEN** the latest sent edition predates source-URL persistence
- **THEN** the response omits source URLs for that edition without error, and the existing fields render exactly as before

### Requirement: Public Edition Archive
The system SHALL provide a public, server-rendered list of past sent editions and a page for each individual edition's full content.

#### Scenario: Visitor browses the archive list
- **WHEN** a visitor requests the archive list page
- **THEN** they see every sent edition, most recent first, each linking to its own edition page

#### Scenario: Visitor views a single archived edition
- **WHEN** a visitor requests a specific edition's archive page
- **THEN** they see that edition's full subject and body content, rendered as HTML
