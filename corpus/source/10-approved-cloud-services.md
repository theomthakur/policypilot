# Northfield University Office of Information Technology

## Approved Cloud Services Registry

| Field | Detail |
|---|---|
| **Registry Number** | NUOIT-REG-2026-003 |
| **Version** | 2.4 |
| **Effective Date** | May 1, 2026 |
| **Last Updated** | September 15, 2026 |
| **Registry Owner** | Cloud Governance and Architecture |
| **Approved By** | Chief Information Security Officer and IT Governance Board |

---

## 1.0 Purpose

This registry identifies externally hosted platforms that Northfield University has assessed for institutional use. Approval is specific to the data classifications and service configurations shown here. A vendor's appearance in this registry does not authorize every product offered by that vendor.

University agreements, tenant controls, identity integration, and data protection terms distinguish an approved institutional service from a consumer account. Users must access every service through the Northfield tenant and university single sign-on. Personal subscriptions and free-tier accounts are not approved for institutional data above Level 1.

## 1.1 Hosted Service Categories

The Office of IT describes hosted platforms by function rather than by consumer marketing terminology:

- **Collaborative content workspaces** support documents, messages, and team files.
- **Managed object persistence** stores research files and application objects in durable buckets.
- **Controlled analytics enclaves** provide isolated computation and storage for regulated datasets.
- **Ephemeral transfer zones** support time-limited exchange and are not systems of record.

## 1.2 General Conditions

All approved services must use Northfield single sign-on and multi-factor authentication. Data owners remain responsible for classification, minimum-necessary access, retention, and legal or sponsor restrictions. Procurement through a university agreement is mandatory.

---
<!-- PAGE BREAK -->
---

## 2.0 Approved Service Matrix

| Institutional Service | Permitted Data | Required Configuration | Prohibited Use |
|---|---|---|---|
| **Northfield Collaboration Drive** | Levels 1 and 2 | Northfield tenant, SSO, MFA, external sharing disabled by default | Level 3 or 4 data |
| **Northfield Research Vault** | Levels 1, 2, and 3 | Research project workspace, named data owner, annual access review, encryption at rest | Level 4 data and public links |
| **Secure Enclave Object Repository** | Levels 1 through 4 | Controlled analytics enclave, CISO approval, named-user allowlist, quarterly access review, customer-managed encryption keys | Anonymous access, public endpoints, consumer credentials |
| **Northfield Managed Object Store** | Levels 1, 2, and 3 | Private bucket, university organization account, encryption and versioning enabled | Level 4 data without enclave controls |
| **Temporary Transfer Zone** | Levels 1 and 2 | Links expire within seven days; recipient authentication required | Long-term retention or regulated datasets |

### 2.1 Confidential Research Material

Level 3 research material may use **Northfield Research Vault** or **Northfield Managed Object Store**. The workspace or bucket must be private, encryption at rest must be enabled, and access must be limited to project members with a documented need to know. A data protection agreement is already incorporated into the university contracts for these institutional configurations.

Level 3 material must not be placed in Northfield Collaboration Drive, a personal file-sharing account, or a bucket outside the university organization. Public link sharing is prohibited.

### 2.2 Restricted and Regulated Datasets

Level 4 material, including protected health information and export-controlled technical data, may be persisted only in the **Secure Enclave Object Repository** after written CISO approval. The approved pattern is called a **controlled analytics enclave**. It combines a named-user allowlist, customer-managed encryption keys, private network endpoints, immutable audit logs, and quarterly access review.

A general-purpose cloud drive, ordinary object bucket, or personal subscription is not an approved persistence target for Level 4 material. Researchers must submit the Hosted Research Environment Review before transferring any regulated dataset.

---
<!-- PAGE BREAK -->
---

## 3.0 Retention, Backup, and Recovery

### 3.1 Northfield Research Vault

Research Vault provides daily snapshots retained for **35 days**. Deleted files remain recoverable by project owners for 30 days and by OIT backup administrators for an additional five days. Research Vault is a working repository, not a permanent archive. At project close, the principal investigator must select records for transfer to the Research Archive.

### 3.2 Managed Object Persistence

Northfield Managed Object Store and Secure Enclave Object Repository use versioning and cross-zone replication. Backup and recovery targets are:

- Recovery point objective: no more than 24 hours.
- Recovery time objective: no more than 8 hours for standard buckets and 24 hours for enclave repositories.
- Deleted object versions: retained for 90 days.
- Audit records: retained for seven years for enclave repositories and one year for standard buckets.

### 3.3 Temporary Transfer Zone

Files in Temporary Transfer Zone are automatically deleted **seven days** after upload. The service does not provide backup or recovery. It must never be treated as durable storage or the authoritative copy of a university record.

## 4.0 Exception Process

A data owner who cannot meet a research or operational requirement with a listed service must submit a Cloud Service Exception through the IT Governance Portal. The request must include the data classification, proposed architecture, vendor assessment, contractual terms, risk analysis, and compensating controls.

Exceptions for Level 3 require approval from Cloud Governance and the data owner. Exceptions involving Level 4 require written approval from the CISO and Office of General Counsel. Approvals expire after twelve months unless renewed.

## 5.0 Service Support and Incident Reporting

Operational incidents should be reported to the IT Service Desk. Suspected unauthorized access, accidental public sharing, credential exposure, or loss of Level 3 or Level 4 material must be reported to the CSIRT immediately under the Cybersecurity Incident Response Plan.

## 6.0 Revision History

| Version | Date | Description |
|---|---|---|
| 2.2 | January 10, 2025 | Added Research Vault institutional agreement |
| 2.3 | May 1, 2026 | Added controlled analytics enclave requirements |
| 2.4 | September 15, 2026 | Clarified managed object persistence and transfer-zone retention |

---
*Synthetic document for a take-home assignment. Not an official NYU policy. | Northfield University Office of IT*
