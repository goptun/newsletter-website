## Purpose

Lets the site owner review and approve a generated draft edition, then sends the approved edition to all active subscribers via a transactional email provider, from the newsletter's own sender identity.

## ADDED Requirements

### Requirement: Draft requires approval before send
The system SHALL NOT send any edition to subscribers automatically. A send SHALL only occur after the owner explicitly approves that specific draft.

#### Scenario: Draft awaits approval
- **WHEN** a new draft is generated
- **THEN** it is held in a pending-review state and is not sent to any subscriber until approved

### Requirement: Approval triggers send
Once the owner approves a pending draft, the system SHALL send that edition to all active subscribers.

#### Scenario: Owner approves draft
- **WHEN** the site owner approves a pending draft
- **THEN** the system sends that edition to every active subscriber

### Requirement: Sender identity
The system SHALL send editions using `newsletter@matheusramos.dev` as the from-address.

#### Scenario: Edition sent with correct sender
- **WHEN** an edition is sent
- **THEN** the message's from-address is `newsletter@matheusramos.dev`

### Requirement: Delivery via transactional provider
The system SHALL send editions through a transactional email API rather than ad-hoc SMTP scripting.

#### Scenario: Edition delivered via provider
- **WHEN** an approved edition is sent
- **THEN** delivery is performed through the configured transactional email provider's API

### Requirement: Send status visibility
The system SHALL record whether an edition was sent successfully, including any per-recipient failures reported by the provider.

#### Scenario: Send outcome recorded
- **WHEN** a send completes
- **THEN** the system records the overall send status and any per-recipient failures reported by the provider

### Requirement: One send per approved draft
The system SHALL NOT send the same approved draft to subscribers more than once.

#### Scenario: Re-approval does not resend
- **WHEN** an already-sent draft is inspected again
- **THEN** the system does not send it a second time
