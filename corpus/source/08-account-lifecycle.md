# Account Lifecycle and Identity Provisioning Standard

**Northfield University Office of Information Technology**

| Field | Detail |
|---|---|
| **Policy Number** | 2025-IAM-03 |
| **Effective Date** | September 1, 2025 |
| **Version** | 3.0 |
| **Document Owner** | Identity and Access Management (IAM) Team |
| **Approved By** | Chief Information Officer, Northfield University |
| **Review Cycle** | Annual (next review: September 2026) |
| **Supersedes** | Version 2.1 (January 2024) |

---

## 1.0 Purpose

This standard defines the policies and procedures governing the full lifecycle of user accounts within the Northfield University information technology environment. It establishes requirements for account creation, modification, renewal, deactivation, and deletion across all university identity systems, ensuring consistent identity management practices that protect institutional resources while supporting the academic and administrative mission of the university.

## 1.1 Scope

This standard applies to all accounts provisioned within the Northfield University identity infrastructure, including but not limited to:

- **NetID accounts** (primary university identity)
- **Email and collaboration accounts** (Northfield Mail, Microsoft 365)
- **Learning Management System (LMS) accounts**
- **Enterprise application accounts** (HR, Finance, Student Information System)
- **VPN and remote access accounts**
- **Research computing and high-performance cluster accounts**

All individuals who hold or administer Northfield University accounts are subject to this standard, including students, faculty, staff, contractors, sponsored guests, and IT administrators.

## 1.2 Related Policies

This standard should be read in conjunction with the following Northfield University policies:

- **2025-SEC-01** — Information Security Policy
- **2025-IAM-01** — Access Control and Authentication Policy
- **2025-IAM-02** — Password and Credential Management Policy
- **2025-PRI-01** — Data Classification and Handling Policy
- **2025-HR-04** — Employee Onboarding and Separation Procedures
- **2025-REG-02** — Student Enrollment and Records Policy

## 2.0 Account Types and Provisioning

### 2.1 Student Accounts

Student accounts are provisioned automatically upon acceptance and confirmed enrollment at Northfield University. The Student Information System (SIS) serves as the authoritative source for student enrollment status. Account provisioning occurs as follows:

1. **Trigger**: The Office of Admissions records a confirmed enrollment (deposit received or registration completed) in the SIS.
2. **Provisioning Timeline**: Accounts are created within **two (2) business days** of the enrollment trigger.
3. **Credentials Delivery**: New students receive their NetID and initial password via their personal email address on file. Students must activate their account through the Northfield Identity Portal and complete Multi-Factor Authentication (MFA) enrollment before accessing university systems.
4. **Entitlements**: Student accounts receive a baseline set of entitlements including Northfield Mail, LMS access, library systems, campus Wi-Fi, and student portal access. Additional entitlements (e.g., lab software, departmental resources) are granted based on course enrollment and program affiliation.

### 2.2 Faculty and Staff Accounts

Faculty and staff accounts are provisioned based on appointment records in the **Human Resources Information System (HRIS)**. The HRIS is the system of record for all employment-related identity attributes.

1. **Trigger**: The hiring department submits a completed Personnel Action Form (PAF) through the HRIS, and the appointment is approved.
2. **Provisioning Timeline**: Accounts are created within **one (1) business day** of HRIS approval for start dates within 14 days, or on the business day preceding the appointment start date for future-dated appointments.
3. **Credentials Delivery**: New employees receive account credentials during the IT onboarding session coordinated by Human Resources. Credentials may also be delivered via secure email to the employee's personal address upon request.
4. **Entitlements**: Faculty and staff accounts receive entitlements based on their role, department, and job classification as defined in the HRIS. Entitlements are mapped through the university's Role-Based Access Control (RBAC) framework (see Policy 2025-IAM-01, Section 4.0).

### 2.3 Sponsored and Guest Accounts

Sponsored and guest accounts provide temporary access to university IT resources for individuals who do not hold a formal student or employee relationship with the university. Common use cases include visiting researchers, conference participants, external collaborators, and contractors.

1. **Trigger**: A Northfield University faculty or staff member (the "sponsor") submits a Sponsored Account Request Form through the IT Service Portal.
2. **Sponsor Responsibilities**: The sponsor must (a) verify the guest's identity, (b) specify the required access level, (c) provide a business justification, and (d) acknowledge responsibility for the guest's compliance with university IT policies.
3. **Provisioning Timeline**: Sponsored accounts are created within **three (3) business days** of an approved request.
4. **Entitlements**: Sponsored accounts receive a restricted set of entitlements as specified on the request form. By default, sponsored accounts include campus Wi-Fi, Northfield Mail (limited), and library database access. Access to administrative systems, research data, or sensitive resources requires additional approval from the relevant data steward.

---
<!-- PAGE BREAK -->
---

## 3.0 Account Renewal and Continuation

Account renewal processes differ based on account type. Users are responsible for understanding the renewal process applicable to their account category. The following subsections describe the specific renewal mechanisms for each account type.

### 3.1 Student Account Renewal

Student accounts are **automatically renewed** each semester upon confirmed enrollment in the Student Information System. No action is required by the student. Accounts are deactivated **90 days** after the student's last active enrollment term.

The automatic renewal process operates as follows:

- At the beginning of each enrollment period, the SIS transmits enrollment confirmations to the Identity Management System (IdMS) via an automated nightly feed.
- The IdMS matches enrollment records to existing student accounts and extends the account expiration date to 90 days beyond the end of the enrolled term.
- Students who take an approved leave of absence retain their accounts for the duration of the approved leave, up to a maximum of **one (1) academic year**, provided the leave is recorded in the SIS.
- Students who withdraw or are dismissed follow the deactivation timeline described in Section 4.1.

Students approaching graduation should review the **Alumni Account Transition** information in Section 3.4 to understand post-graduation access options.

### 3.2 Faculty and Staff Account Renewal

Faculty and staff accounts are **tied to the Human Resources system** and remain active while the individual holds an active appointment. Upon separation, accounts enter a **30-day grace period** for data migration before deactivation. To extend access beyond separation, the departing employee's supervisor must submit an Account Extension Request through the IT Governance portal.

Additional details on faculty and staff account continuation:

- **Active Appointments**: As long as an employee maintains at least one active appointment in the HRIS, their account remains active with entitlements corresponding to their current role(s). Changes in role, department, or appointment status automatically trigger an entitlement review (see Section 5.0).
- **Emeritus Faculty**: Faculty members granted emeritus status by the Provost's Office receive an emeritus account with reduced entitlements (email, library access, and limited VPN). Emeritus accounts do not require periodic renewal.
- **Account Extension Requests**: Extensions beyond the 30-day grace period may be granted for up to **90 additional days** and require justification such as completion of research obligations, data transfer, or transition of responsibilities. Extensions are reviewed by the IAM Team and approved by the relevant Dean or Vice President.
- **Rehire Provisions**: Former employees who are rehired within **180 days** of separation may have their previous account restored rather than receiving a new account, subject to a security review.

### 3.3 Sponsored and Guest Account Renewal

Sponsored and guest accounts have a **maximum duration of six (6) months** and require a **faculty or staff sponsor**. To renew a sponsored account, the sponsor must submit a Sponsored Account Renewal Form at least **14 business days** before expiration. Renewals are limited to two consecutive terms (12 months total), after which a new sponsorship request is required.

Key provisions for sponsored account renewal:

- **Renewal Notifications**: The system sends automated email reminders to both the sponsor and the guest at **30 days**, **14 days**, and **7 days** before account expiration.
- **Sponsor Change**: If the original sponsor has left the university or is unable to continue sponsorship, a new eligible sponsor may assume responsibility by submitting a Sponsor Transfer Form along with the renewal request.
- **Compliance Review**: All sponsored account renewals are subject to a compliance review by the IAM Team, which verifies that the business justification remains valid, the guest has completed required security awareness training, and no policy violations have been recorded.
- **Post-Limit Re-Sponsorship**: After the 12-month maximum, a **60-day cooling period** must elapse before a new sponsorship request may be submitted for the same individual, unless a written exception is approved by the Chief Information Security Officer (CISO).

### 3.4 Alumni Account Transition

Upon degree conferral, graduating students are eligible for a **Northfield Alumni Account**, which provides continued access to a limited set of university services:

- Northfield Alumni email (forwarding address)
- Library database access (read-only)
- Career services portal
- Alumni directory and networking platform

Alumni accounts are provisioned automatically within **14 days** of degree conferral and do not require a separate application. Alumni accounts are permanent and do not require renewal, though they are subject to the university's Acceptable Use Policy.

---
<!-- PAGE BREAK -->
---

## 4.0 Account Deactivation and Deletion

### 4.1 Deactivation Triggers

Accounts are deactivated under the following circumstances:

| Account Type | Deactivation Trigger | Timeline |
|---|---|---|
| Student | No active enrollment in SIS | 90 days after last enrollment term |
| Faculty/Staff | Separation recorded in HRIS | 30-day grace period, then deactivated |
| Sponsored/Guest | Account expiration date reached | Immediate upon expiration |
| Any | Security incident or policy violation | Immediate, per CISO directive |
| Any | Account owner request | Within 2 business days |
| Any | Death of account holder | Within 1 business day of notification |

### 4.2 Deactivation Process

When an account is deactivated, the following actions are taken:

1. **Authentication Disabled**: The account is locked and all active sessions are terminated.
2. **Access Revoked**: All entitlements and group memberships are removed.
3. **Email**: Incoming email is held for **30 days** (student/sponsored) or **60 days** (faculty/staff) and an auto-reply is configured if requested.
4. **Data Preservation**: The contents of the account holder's university cloud storage (OneDrive, Northfield Drive) are preserved for **90 days** in a read-only archive accessible to the account holder's supervisor or designated data custodian.
5. **Notification**: The account holder (if reachable) and relevant department administrators are notified of the deactivation.

### 4.3 Account Deletion

Deactivated accounts are permanently deleted according to the following retention schedule:

- **Student accounts**: Deleted **one (1) year** after deactivation.
- **Faculty/staff accounts**: Deleted **two (2) years** after deactivation, subject to legal hold requirements.
- **Sponsored/guest accounts**: Deleted **six (6) months** after deactivation.

Prior to deletion, the IAM Team verifies that no legal holds, audit requirements, or records retention obligations apply. Accounts under legal hold are preserved indefinitely until the hold is released by the Office of General Counsel.

## 5.0 Account Modification and Entitlement Changes

### 5.1 Automated Entitlement Updates

Changes to a user's role, department, enrollment, or appointment status in the authoritative source systems (SIS, HRIS) automatically trigger an entitlement review in the IdMS. The system applies the following logic:

- **Added roles/enrollments**: New entitlements are provisioned within **one (1) business day**.
- **Removed roles/enrollments**: Former entitlements are revoked within **one (1) business day**, unless a transition period is approved.
- **Department transfers**: A **five (5) business day** overlap period is provided during which the user retains entitlements from both the former and new department to ensure continuity.

### 5.2 Manual Entitlement Requests

Users or their supervisors may request additional entitlements beyond those automatically assigned through the **IT Service Portal**. All manual requests require:

- Business justification
- Approval from the data steward or system owner for the requested resource
- Verification that the request is consistent with the principle of least privilege (see Policy 2025-IAM-01, Section 3.2)

### 5.3 Name and Identity Changes

Account holders who legally change their name or other identity attributes must submit a Name/Identity Change Request along with supporting documentation to the appropriate office:

- **Students**: Office of the Registrar
- **Faculty/Staff**: Human Resources
- **Sponsored/Guest**: IT Service Desk with sponsor approval

Identity changes are processed within **five (5) business days** and are reflected across all connected university systems. The previous NetID alias is maintained as a secondary alias for **one (1) year** to ensure continuity of email delivery and system access.

---
<!-- PAGE BREAK -->
---

## 6.0 Account Recovery

### 6.1 Self-Service Recovery

Account holders may recover access to their accounts through the **Northfield Identity Portal** using one of the following methods:

- **Multi-Factor Authentication reset**: Verify identity through a registered MFA device and reset the password online.
- **Security questions**: Answer previously configured security questions to initiate a password reset (available only for accounts that have not yet enrolled in MFA).
- **Recovery email/phone**: Receive a one-time verification code at a pre-registered personal email address or mobile phone number.

### 6.2 Assisted Recovery

If self-service recovery is not available, account holders must visit the **IT Service Desk** in person with a valid government-issued photo ID. The Service Desk will:

1. Verify the individual's identity against the university's identity records.
2. Confirm account ownership through secondary verification (e.g., date of birth, employee ID, student ID number).
3. Issue a temporary password, which must be changed upon first login.
4. Re-enroll the user in MFA if their previous MFA devices are no longer accessible.

Assisted recovery requests are logged and audited in accordance with Policy 2025-SEC-01.

## 7.0 Shared and Functional Accounts

### 7.1 Definition

A **shared or functional account** is an account not tied to a single individual but used by a group or unit to perform a specific function (e.g., departmental email, service accounts for system integrations, lab computer accounts).

### 7.2 Requirements

All shared and functional accounts must comply with the following requirements:

- **Designated Owner**: Every shared account must have a designated individual owner (a Northfield faculty or staff member) who is responsible for the account's use and security.
- **Registration**: Shared accounts must be registered in the IAM Team's Shared Account Registry, which records the account purpose, owner, authorized users, and review schedule.
- **Password Management**: Shared account passwords must be stored in the university's approved enterprise password vault (see Policy 2025-IAM-02, Section 5.0). Passwords must be rotated every **90 days** or immediately upon any change in authorized users.
- **Access Logging**: All authentication events for shared accounts must be logged and attributable to an individual user wherever technically feasible.
- **Annual Review**: Shared accounts are subject to annual review by the account owner and the IAM Team. Accounts that are no longer needed must be deactivated promptly.

### 7.3 Prohibited Uses

Shared accounts **must not** be used to circumvent individual accountability requirements, access systems that require individual authentication for compliance purposes (e.g., FERPA-protected student records, HIPAA-regulated health data), or bypass audit trail requirements.

## 8.0 Auditing and Compliance

### 8.1 Periodic Access Reviews

The IAM Team conducts periodic access reviews to ensure that account entitlements remain appropriate:

- **Quarterly**: Review of privileged and administrative accounts.
- **Semi-annually**: Review of sponsored and guest accounts.
- **Annually**: Comprehensive review of all active accounts and entitlements.

Department managers and data stewards are required to participate in access reviews by certifying that the entitlements assigned to their users remain appropriate. Failure to complete a certification review within **15 business days** of notification will result in automatic suspension of uncertified entitlements.

### 8.2 Audit Logging

All account lifecycle events (creation, modification, deactivation, deletion, recovery) are recorded in the university's centralized audit log. Audit logs are retained for a minimum of **seven (7) years** in accordance with the university's Records Retention Policy and applicable regulatory requirements (FERPA, HIPAA, GLBA).

### 8.3 Compliance Reporting

The IAM Team provides quarterly compliance reports to the IT Governance Committee summarizing:

- Total active accounts by type
- Accounts created and deactivated during the reporting period
- Orphaned accounts identified and remediated
- Access review completion rates
- Policy exceptions granted

## 9.0 Exceptions

Requests for exceptions to this standard must be submitted through the **IT Governance Portal** and include a risk assessment, business justification, and proposed compensating controls. Exceptions are reviewed by the IAM Team and approved by the CISO. Approved exceptions are valid for a maximum of **one (1) year** and must be renewed annually.

## 10.0 Enforcement

Violations of this standard may result in account suspension, disciplinary action, or termination of access privileges in accordance with the Northfield University Acceptable Use Policy and applicable employment or student conduct policies. Repeated or egregious violations will be referred to the appropriate disciplinary body (Human Resources, Office of Student Conduct, or Office of General Counsel).

## 11.0 Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | September 1, 2022 | IAM Team | Initial release |
| 2.0 | March 15, 2023 | IAM Team | Added sponsored account procedures; updated deactivation timelines |
| 2.1 | January 10, 2024 | IAM Team | Clarified alumni account transition; added rehire provisions |
| 3.0 | September 1, 2025 | IAM Team | Comprehensive revision; added shared account requirements; updated renewal processes; aligned with new RBAC framework |

---
*Synthetic document for a take-home assignment. Not an official NYU policy. | Northfield University Office of IT*
