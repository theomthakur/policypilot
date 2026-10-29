# Northfield University Office of Information Technology
## Acceptable Use and Guest Network Policy

| Field | Detail |
|---|---|
| **Document ID** | NUIT-POL-2026-001 |
| **Version** | 3.2 |
| **Effective Date** | September 1, 2026 |
| **Last Reviewed** | August 15, 2026 |
| **Policy Owner** | Office of Information Technology — Network & Infrastructure Division |
| **Applies To** | All students, faculty, staff, contractors, affiliates, and guests using Northfield University IT resources |
| **Approved By** | Dr. Catherine Morales, Vice Provost for Information Technology & CIO |

---

## 1.0 Purpose

The purpose of this policy is to define the acceptable use of information technology resources owned, leased, or operated by Northfield University. This policy exists to protect the university community, its data assets, and the integrity of shared computing and network infrastructure. All members of the university community — including temporary visitors and guests — are expected to comply with the standards outlined herein.

## 2.0 Scope

This policy applies to all information technology resources provided by Northfield University, including but not limited to:

- University-owned desktop computers, laptops, tablets, and mobile devices
- Campus wired and wireless networks, including **NorthfieldSecure**, **NorthfieldGuest**, and **NorthfieldIoT** service set identifiers (SSIDs)
- University-licensed software, cloud services, and electronic mail systems
- Data center infrastructure, virtual machines, and research computing clusters
- Printing, scanning, and audiovisual equipment managed by the Office of IT

This policy should be read in conjunction with the *Northfield University Data Classification and Handling Policy* (NUIT-POL-2026-004) and the *Information Security Incident Response Plan* (NUIT-POL-2026-007).

## 2.1 Definitions

- **Authorized User**: Any individual who has been granted credentials or explicit permission to access Northfield University IT resources.
- **Guest**: A visitor, prospective student, conference attendee, or other non-affiliated individual who accesses university network services on a temporary basis.
- **IT Resources**: All hardware, software, networks, data, and services provisioned or managed by the Office of Information Technology.
- **Registered Device**: A personal or university-owned device that has been enrolled in the Northfield Device Management portal and meets minimum security requirements.
- **Sponsored Account**: A temporary account created by a faculty or staff sponsor for a guest or external collaborator, subject to the terms of the *Sponsored Account Policy* (NUIT-POL-2026-012).

## 2.2 Acceptable Use — General Principles

All authorized users of Northfield University IT resources shall:

1. Use IT resources solely for purposes consistent with the university's educational, research, administrative, and community-service missions.
2. Respect the privacy and intellectual property rights of other users.
3. Refrain from attempting to gain unauthorized access to systems, accounts, or data for which they have not been granted explicit permission.
4. Comply with all applicable federal, state, and local laws, including the Family Educational Rights and Privacy Act (FERPA), the Computer Fraud and Abuse Act (CFAA), and the Digital Millennium Copyright Act (DMCA).
5. Report suspected security incidents, policy violations, or system compromises to the IT Security Operations Center (SOC) at **security@northfield.edu** or by calling **(555) 214-9000** within 24 hours of discovery.

## 2.3 Prohibited Activities

The following activities are strictly prohibited on Northfield University IT resources:

- **Unauthorized access**: Attempting to access, probe, or exploit systems, accounts, or data without authorization, including the use of network scanning or vulnerability assessment tools outside of sanctioned security testing.
- **Harassment and abuse**: Using IT resources to transmit threatening, harassing, discriminatory, or obscene material as defined by university conduct policies.
- **Copyright infringement**: Downloading, distributing, or sharing copyrighted material (including music, films, and software) without proper authorization or licensing.
- **Commercial use**: Using university IT resources for private commercial gain, unauthorized advertising, or solicitation unless expressly approved in writing by the Office of IT.
- **Network interference**: Deploying unauthorized wireless access points, DHCP servers, or network devices that interfere with campus network operations.
- **Cryptocurrency mining**: Using university computing resources, including research clusters, for cryptocurrency mining without prior written approval from the Chief Information Officer (CIO).

Violations of this section may result in immediate suspension of access privileges and referral to the Office of Student Conduct or Human Resources, as applicable. See *Northfield University Code of Conduct* (NU-GOV-2025-003) for additional guidance.

---
<!-- PAGE BREAK -->
---

## 3.0 Network Access

### 3.1 Campus Network Architecture

Northfield University operates three primary wireless networks across its campus:

| Network SSID | Purpose | Authentication |
|---|---|---|
| **NorthfieldSecure** | Primary network for students, faculty, and staff | 802.1X with university credentials (NetID + password) |
| **NorthfieldGuest** | Temporary access for visitors and guests | Captive portal with self-registration or sponsor code |
| **NorthfieldIoT** | Internet of Things devices and lab equipment | Pre-shared key issued by Network Services |

All campus buildings, residence halls, and common outdoor spaces are covered by the NorthfieldSecure and NorthfieldGuest wireless networks. The NorthfieldIoT network is available only in approved laboratory, facility-management, and research spaces.

### 3.2 Guest Network Access

Northfield University provides the **NorthfieldGuest** wireless network as a courtesy to campus visitors, prospective students and their families, conference attendees, and other short-term guests. Guest network access is subject to the following conditions:

1. **Duration**: Guest sessions are valid for **24 hours** from the time of registration. Guests requiring extended access must obtain a sponsored account through a Northfield University faculty or staff member (see Section 3.3).
2. **Bandwidth**: Unregistered guest devices are limited to **10 Mbps download and 2 Mbps upload** on the NorthfieldGuest wireless network. Registered devices sponsored by a department may request standard bandwidth through the Network Services portal.
3. **Content Filtering**: The NorthfieldGuest network applies the university's standard content-filtering profile, which blocks categories of content deemed harmful or in violation of applicable law. Guests may not circumvent content filtering through the use of VPN tunnels, proxy servers, or anonymization tools.
4. **No Access to Internal Resources**: Guest network users do not have access to internal university systems, file shares, library databases, or administrative applications. Access to such resources requires a valid NetID and connection to the NorthfieldSecure network.
5. **Acceptable Use**: All provisions of this Acceptable Use Policy (Sections 2.2 and 2.3) apply to guest network users. The university reserves the right to terminate guest sessions at any time and without notice for policy violations.
6. **Logging**: Connection metadata (MAC address, IP assignment, session duration) is logged for a minimum of **90 days** for security and compliance purposes, consistent with the *Data Retention and Disposal Policy* (NUIT-POL-2026-009).

### 3.3 Sponsored Guest Accounts

Faculty and staff members may sponsor guest accounts for external collaborators, visiting researchers, or contractors who require access beyond the standard 24-hour guest session. Sponsored accounts are subject to the following requirements:

- The sponsor must submit a request through the **IT Service Portal** at least **five (5) business days** before the guest's arrival.
- Sponsored accounts are valid for a maximum of **180 days** and may be renewed once upon written justification from the sponsoring department head.
- The sponsor assumes responsibility for the guest's compliance with all applicable university IT policies during the account's active period.
- Sponsored guests may be granted access to the NorthfieldSecure network and, where justified, to specific internal resources approved by the relevant data steward.

### 3.4 Wired Network Access

Wired Ethernet connections in offices, classrooms, and laboratories require device registration through the **Northfield Device Management** portal. Unregistered devices connected to wired ports are automatically placed on a quarantine VLAN with access limited to the Device Management registration page. Residence hall wired connections follow the same registration process and are subject to the bandwidth policies described in Section 4.0.

---
<!-- PAGE BREAK -->
---

## 4.0 Bandwidth and Network Performance

### 4.1 Fair Use Bandwidth Policy

Northfield University employs a fair-use bandwidth management framework to ensure equitable access to network resources for all users. The Office of IT reserves the right to implement traffic-shaping measures during periods of peak demand, including but not limited to:

- Prioritization of academic and research traffic over recreational streaming and gaming
- Throttling of peer-to-peer (P2P) file-sharing protocols that consume disproportionate bandwidth
- Rate limiting of individual devices that exceed **50 GB of data transfer** within a rolling seven-day period on residential networks

Users who are rate-limited will receive an automated notification via their Northfield University email address. Rate limits are lifted automatically at the beginning of the next seven-day cycle. Appeals may be submitted to the **IT Help Desk** at **helpdesk@northfield.edu**.

### 4.2 Residential Network Allocation

Each residence hall room is provisioned with a shared connection supporting up to **200 Mbps download and 100 Mbps upload**. This allocation is shared among all registered devices in the room. Students experiencing performance issues should contact the IT Help Desk to schedule a diagnostic assessment.

### 4.3 Research and High-Performance Networking

Faculty and research staff requiring dedicated high-bandwidth connectivity for data-intensive research (e.g., genomics pipelines, large-scale simulations, remote instrument access) may request a connection to the **Northfield Research Network (NRN)**. The NRN provides 10 Gbps and 100 Gbps uplinks to Internet2 and regional research networks. Requests must be submitted through the **Research Computing Services** office and require approval from both the department chair and the Office of IT.

### 4.4 Network Abuse and Violations

The Office of IT continuously monitors network traffic for anomalies, security threats, and policy violations using industry-standard intrusion detection and prevention systems (IDS/IPS). Activities that may trigger an investigation include:

- Sustained traffic volumes significantly above normal thresholds for a given user profile
- Outbound connections to known malicious command-and-control servers
- Unauthorized scanning of internal or external IP address ranges
- Deployment of rogue network services (DHCP, DNS, wireless access points)

Upon detection of a potential violation, the IT Security Operations Center may take immediate protective action, including isolation of the offending device, pending investigation. All incidents are documented and referred to the appropriate disciplinary body as outlined in the *Information Security Incident Response Plan* (NUIT-POL-2026-007).

## 5.0 University Email and Communication Systems

### 5.1 Official Communication Channel

Northfield University email (provided via the NorthfieldMail platform) is the official electronic communication channel for university business. Students, faculty, and staff are expected to monitor their Northfield University email accounts regularly and are responsible for the content of all communications sent from their accounts.

### 5.2 Email Retention

Email messages stored in university mailboxes are subject to the retention schedules defined in the *Data Retention and Disposal Policy* (NUIT-POL-2026-009). Users should not rely on email as a long-term records-management solution. Official university records must be preserved in approved records-management systems.

### 5.3 Mass Email and Distribution Lists

Mass email communications to university-wide or large departmental distribution lists require prior approval from the **Office of University Communications**. Unauthorized mass emails are subject to the sanctions described in Section 7.0.

---
<!-- PAGE BREAK -->
---

## 6.0 Personal Device Usage (Bring Your Own Device)

### 6.1 Overview

Northfield University permits students, faculty, and staff to connect personally owned devices to campus network infrastructure under the university's Bring Your Own Device (BYOD) framework. Personal device use is a privilege, not a right, and is contingent upon compliance with the security requirements outlined in this section.

### 6.2 Security Requirements for Personal Devices

All personal devices connecting to the NorthfieldSecure network must have **full-disk encryption enabled** and run a **supported antivirus solution** from the university's approved software list. Exceptions require written approval from the **Chief Information Security Officer (CISO)**.

Additional security requirements include:

- **Operating System Currency**: Devices must run a manufacturer-supported operating system version with all critical security patches applied within **14 days** of release.
- **Screen Lock**: A screen lock or biometric authentication mechanism must be enabled with an automatic lock timeout of no more than **5 minutes**.
- **Firewall**: Host-based firewalls must be enabled on all laptop and desktop operating systems.
- **No Jailbreaking or Rooting**: Mobile devices that have been jailbroken or rooted are prohibited from connecting to any Northfield University network.

The university's approved antivirus solutions are listed on the **Software Distribution** page of the IT website at **https://it.northfield.edu/software**. Students, faculty, and staff may download approved antivirus software at no cost through the university's site license agreements.

### 6.3 Device Registration

All personal devices must be registered through the **Northfield Device Management** portal prior to connecting to the NorthfieldSecure network. During registration, the user must:

1. Authenticate with their NetID and password.
2. Provide the device's MAC address (detected automatically during onboarding).
3. Attest that the device meets the security requirements described in Section 6.2.
4. Accept the university's Acceptable Use Policy.

Registered devices are subject to periodic compliance checks via the university's network access control (NAC) system. Devices found to be non-compliant will be moved to a remediation VLAN until the deficiency is corrected.

### 6.4 University Data on Personal Devices

Users who access, store, or process university data classified as **Confidential** or **Restricted** (as defined in the *Data Classification and Handling Policy*, NUIT-POL-2026-004) on personal devices must enroll those devices in the university's Mobile Device Management (MDM) program. MDM enrollment enables the Office of IT to enforce encryption, remotely wipe university data in the event of device loss or theft, and verify ongoing compliance with security requirements.

## 7.0 Enforcement and Sanctions

### 7.1 Reporting Violations

Members of the Northfield University community are encouraged to report suspected violations of this policy to the IT Help Desk at **helpdesk@northfield.edu** or **(555) 214-8500**. Reports may also be submitted anonymously through the university's **Ethics and Compliance Hotline**.

### 7.2 Sanctions

Violations of this policy may result in one or more of the following actions, depending on the severity and frequency of the offense:

| Severity | Examples | Possible Sanctions |
|---|---|---|
| **Minor** | Failure to register a device; accidental policy breach | Written warning; mandatory IT security training |
| **Moderate** | Unauthorized access attempt; bandwidth abuse; unauthorized mass email | Temporary suspension of IT privileges (up to 30 days); referral to department head |
| **Severe** | Data breach; copyright infringement; harassment via IT resources | Permanent revocation of IT privileges; referral to Office of Student Conduct or Human Resources; referral to law enforcement where applicable |

All sanctions are imposed in accordance with established university disciplinary procedures and are subject to appeal as described in the *Northfield University Grievance Policy* (NU-GOV-2025-010).

## 8.0 Policy Review

This policy is reviewed annually by the Office of Information Technology in consultation with the Information Security Governance Committee. The next scheduled review is **August 2027**. Proposed amendments should be directed to the Policy Owner listed on page 1 of this document.

---
*Synthetic document for a take-home assignment. Not an official NYU policy. | Northfield University Office of IT*
