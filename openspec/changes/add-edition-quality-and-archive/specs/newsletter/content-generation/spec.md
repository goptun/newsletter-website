## ADDED Requirements

### Requirement: Portuguese Language Consistency
Every item in a draft edition, including the subject line, SHALL be in Brazilian Portuguese (pt-BR). The system SHALL check each item's language after generation and, before the draft leaves draft state for review, automatically regenerate or translate any item found not to be in pt-BR.

#### Scenario: Non-Portuguese item detected
- **WHEN** a generated draft contains an item (including the subject) that is not in pt-BR
- **THEN** that item is regenerated or translated to pt-BR before the draft is held for owner approval

#### Scenario: All items already in Portuguese
- **WHEN** every item in a generated draft is already in pt-BR
- **THEN** the language check passes and no regeneration occurs

### Requirement: Subject-Body Numeric Consistency
Any number that appears in a draft's subject line SHALL also appear in the body. Currency amounts SHALL be formatted consistently as "US$" throughout the edition.

#### Scenario: Subject number missing from body
- **WHEN** a generated subject line contains a number that does not appear anywhere in the body
- **THEN** the subject line is regenerated before the draft is held for owner approval

#### Scenario: Currency formatting
- **WHEN** a draft includes a monetary amount, in the subject or the body
- **THEN** it is formatted using the "US$" notation consistently, not a mix of "US$" and "$"
