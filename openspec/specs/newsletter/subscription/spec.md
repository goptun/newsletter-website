# newsletter/subscription Specification

## Purpose

Provides an API and persistent store for capturing and managing newsletter subscriber email addresses, to be called by the `portfolio-website` subscribe CTA.

## Requirements

### Requirement: Subscribe endpoint
The system SHALL provide an API to accept a subscriber email address and persist it as an active subscriber.

#### Scenario: New subscriber signs up
- **WHEN** a valid, well-formed email address is submitted to the subscribe endpoint
- **THEN** the system persists the email as an active subscriber and returns a success response

### Requirement: Duplicate subscription handling
The system SHALL NOT create duplicate active subscriber records for the same email address.

#### Scenario: Already-subscribed email resubmitted
- **WHEN** an email that is already an active subscriber is submitted again
- **THEN** the system treats the submission as a no-op success rather than creating a duplicate record

### Requirement: Invalid input rejection
The system SHALL reject syntactically invalid email addresses with a clear error and SHALL NOT persist them.

#### Scenario: Malformed email rejected
- **WHEN** a syntactically invalid email address is submitted
- **THEN** the system returns an error response and does not persist a subscriber record

### Requirement: Unsubscribe
The system SHALL provide a way for a subscriber to unsubscribe using their email; once unsubscribed, they SHALL NOT receive further editions.

#### Scenario: Subscriber unsubscribes
- **WHEN** a subscriber uses the unsubscribe mechanism tied to their email
- **THEN** the system marks that subscriber inactive and excludes them from future sends

### Requirement: Subscriber data scope
The system SHALL use stored subscriber emails only to deliver newsletter editions, and SHALL make only active subscribers available to the delivery capability.

#### Scenario: Delivery requests recipients
- **WHEN** the delivery capability requests recipients for an edition
- **THEN** only active subscriber emails are provided, and for no purpose other than sending that edition
