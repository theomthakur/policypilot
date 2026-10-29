# Northfield University Office of Information Technology

## Remote Work and Personal Device Security Standard

**Policy Number:** NUOIT Policy 2026-REM-01
**Version:** 2.0
**Effective Date:** February 1, 2026
**Last Revised:** January 10, 2026
**Document Owner:** Office of the Chief Information Security Officer (CISO)
**Approved By:** Dr. Michael Chen, Chief Information Security Officer; IT Governance Board
**Review Cycle:** Annual (next review scheduled January 2027)
**Supersedes:** Version 1.0 (August 15, 2024)

---

## 1.0 Purpose

The purpose of this policy is to establish security requirements and standards for Northfield University faculty, staff, and authorized affiliates who perform work remotely or use personal devices to access university information systems and data. As remote and hybrid work arrangements become increasingly common, maintaining a robust security posture across distributed environments is essential to protecting university data, ensuring regulatory compliance, and minimizing institutional risk.

## 2.0 Scope

This policy applies to all Northfield University employees (faculty, staff, student employees, and contractors) who:

- Perform work duties from any location outside of official Northfield University campus facilities;
- Access university information systems, applications, or data from personal (non-university-owned) devices;
- Connect to the Northfield University network remotely via Virtual Private Network (VPN) or other remote-access technologies;
- Store, process, or transmit university data on personal devices or over non-university networks.

This policy covers all categories of university data as defined in the Northfield University Data Classification and Handling Policy (NUOIT Policy 2026-DCH-02), including but not limited to Restricted, Confidential, Internal, and Public data.

## 3.0 Definitions

| Term | Definition |
|------|------------|
| **Remote Work** | Any arrangement in which an authorized employee performs official university duties from a location other than their assigned on-campus workspace, including telecommuting, hybrid work, and travel-based work. |
| **BYOD (Bring Your Own Device)** | The practice of using a personally owned computing device (laptop, desktop, tablet, or smartphone) to access university systems, data, or networks. |
| **Full-Tunnel VPN** | A VPN configuration in which all network traffic from the connected device is routed through the university's VPN gateway, regardless of destination. |
| **Split-Tunnel VPN** | A VPN configuration that allows some traffic to route directly to the internet while other traffic is sent through the VPN tunnel. This configuration is **prohibited** under standard operating conditions. |
| **University Data** | Any data created, collected, stored, or processed in the course of university operations, research, or administration, regardless of format or storage location. |
| **MFA (Multi-Factor Authentication)** | An authentication method requiring two or more independent verification factors before granting access. |

## 4.0 Remote Work Security Requirements

### 4.1 General Requirements

All remote work arrangements must comply with the following baseline security requirements:

1. **Formal Authorization.** Remote work arrangements must be formally approved by the employee's supervisor and department head. A Remote Work Agreement form must be filed with Human Resources and a copy submitted to the Office of Information Technology prior to commencement of remote work.

2. **Security Awareness Training.** All remote workers must complete the Northfield University Information Security Awareness Training program (offered through NULearn) prior to beginning remote work and annually thereafter. Completion records are maintained by the Office of Information Technology.

3. **Multi-Factor Authentication (MFA).** All remote access to university systems must use MFA via the Northfield University Duo Security integration. This requirement applies to VPN connections, email access, cloud application logins, and all systems classified as handling Restricted or Confidential data.

4. **Session Management.** Remote sessions accessing university systems must be configured to automatically lock or disconnect after **15 minutes** of inactivity. Users must manually lock their devices when stepping away, even briefly.

5. **Physical Security.** Remote workers must ensure that university data displayed on screens is not visible to unauthorized individuals. Work involving Restricted or Confidential data should be performed in a private setting. University-owned equipment must be stored securely when not in use.

---
<!-- PAGE BREAK -->
---

### 4.2 VPN Usage Requirements

The Northfield University VPN service (GlobalProtect) is the sole authorized method for establishing remote network connectivity to on-campus university resources. The following requirements apply to all VPN usage:

1. **Mandatory VPN for Sensitive Data.** Any remote access to systems containing Restricted or Confidential data as defined in NUOIT Policy 2026-DCH-02 **must** be conducted over the university VPN. This includes, but is not limited to, access to Banner, PeopleSoft HR, financial systems, research data repositories, and student information systems.

2. **Full-Tunnel VPN Required.** All VPN connections to the Northfield University network **must** use a full-tunnel configuration. Under full-tunnel mode, all network traffic originating from the connected device is routed through the university's VPN gateway, enabling the university's network security controls (firewall, intrusion detection/prevention, content filtering, and logging) to inspect and protect all traffic.

3. **Split Tunneling Prohibited.** **Split-tunnel VPN configurations are strictly prohibited under standard operating conditions.** Split tunneling creates an unmonitored path between the remote device and the public internet, bypassing university security controls and exposing the device—and by extension, the university network—to increased risk of malware, data exfiltration, and man-in-the-middle attacks. Any device found to be using a split-tunnel configuration without an approved exception will be immediately disconnected from the university network, and the incident will be referred to the Information Security Office for investigation.

4. **VPN Client Compliance.** Only the university-provided and managed VPN client (Palo Alto GlobalProtect, distributed via the Northfield University Software Center) may be used. Third-party VPN clients, browser-based VPN extensions, and personal VPN services must not be used to access university resources.

5. **Automatic Connection Policy.** University-owned laptops are configured with an always-on VPN policy that automatically establishes a VPN connection whenever the device detects it is off-campus. Users must not disable or circumvent this feature.

### 4.3 Personal Device (BYOD) Security Requirements

Remote workers using personal devices must comply with all requirements in the Acceptable Use and Guest Network Policy (NUOIT Policy 2026-AUP-03), including full-disk encryption and approved antivirus software. In addition to those baseline requirements, personal devices used for remote work must meet the following standards:

1. **Operating System Currency.** Personal devices must run a currently supported operating system version. As of the effective date of this policy, minimum supported versions are: Windows 11 (22H2 or later), macOS 13 (Ventura) or later, iOS 17 or later, and Android 14 or later. Devices running unsupported or end-of-life operating systems will be denied VPN access.

2. **Patch Management.** All operating system and application security patches must be applied within **14 calendar days** of release. Critical and zero-day patches must be applied within **72 hours** of release, or the device must be disconnected from university systems until patching is complete.

3. **Local Firewall.** A host-based firewall must be enabled and properly configured on all personal devices used for remote work. Default-deny inbound policies are recommended.

4. **Endpoint Compliance Check.** Personal devices connecting to the university VPN are subject to an automated endpoint compliance check (via GlobalProtect Host Information Profile). Devices that fail compliance checks for encryption, antivirus, or OS version will be placed into a quarantine VLAN with access limited to remediation resources only.

5. **No Local Storage of Restricted Data.** Restricted data (as defined in NUOIT Policy 2026-DCH-02) must not be stored locally on personal devices under any circumstances. Restricted data may only be accessed through university-managed virtual desktop infrastructure (VDI) or approved cloud platforms with appropriate access controls.

---
<!-- PAGE BREAK -->
---

## 5.0 VPN Exception Process

### 5.1 Overview

Northfield University recognizes that in limited circumstances, the standard full-tunnel VPN requirement may create documented performance degradation or application compatibility issues that materially impair an employee's ability to perform their duties. In such cases, a VPN split-tunnel exception may be requested.

### 5.2 VPN Exception Request and Approval

Requests for VPN split-tunnel exceptions must be submitted through the IT Governance portal and require written approval from the **Chief Information Security Officer (CISO), currently Dr. Michael Chen**. Exceptions are granted only for documented performance or compatibility requirements and are reviewed quarterly.

The exception request must include:

1. **Business Justification.** A detailed description of the business need, including the specific applications or workflows affected by the full-tunnel requirement.
2. **Technical Documentation.** Measurable evidence of performance degradation or incompatibility (e.g., latency measurements, application error logs, bandwidth utilization reports).
3. **Risk Assessment.** A completed risk assessment (using the Northfield University IT Risk Assessment Template, available on the IT Governance portal) identifying the security risks introduced by the split-tunnel configuration and proposed compensating controls.
4. **Compensating Controls.** A description of additional security measures that will be implemented to mitigate the risks of split tunneling, which may include but are not limited to:
   - DNS-layer security filtering (e.g., Cisco Umbrella);
   - Enhanced endpoint detection and response (EDR) monitoring;
   - Application-layer encryption for all university data in transit;
   - Increased logging and monitoring of the device's network activity.
5. **Supervisor and Department Head Endorsement.** Written approval from the requesting employee's direct supervisor and department head.

### 5.3 Exception Duration and Review

- All VPN exceptions are granted for a maximum period of **six (6) months**.
- Exceptions are subject to **quarterly review** by the Information Security Office to verify that the conditions justifying the exception remain valid.
- The CISO reserves the right to revoke any exception immediately if security conditions change, a security incident occurs, or compensating controls are found to be insufficient.
- Employees operating under a VPN exception must submit a brief quarterly compliance report confirming that all compensating controls remain in effect.

### 5.4 Exception Denial and Appeal

If a VPN exception request is denied, the requestor may appeal the decision to the IT Governance Board within **15 business days** of receiving the denial notice. The IT Governance Board's decision on appeal is final.

---
<!-- PAGE BREAK -->
---

## 6.0 Home Network Security Recommendations

While the university cannot mandate the configuration of employees' personal home networks, the following best practices are **strongly recommended** to reduce security risk for remote workers:

1. **Router Firmware.** Keep home router firmware updated to the latest version provided by the manufacturer. Enable automatic updates if available.
2. **Wi-Fi Encryption.** Use WPA3 encryption for home Wi-Fi networks. If WPA3 is not supported by the router, WPA2 with AES encryption is the minimum acceptable standard. WEP and open (unencrypted) networks must not be used to access university systems.
3. **Default Credentials.** Change default administrator passwords on all home networking equipment (routers, access points, and network-attached storage devices).
4. **Network Segmentation.** Where supported, create a separate Wi-Fi network or VLAN for work devices, isolating them from IoT devices (smart speakers, cameras, thermostats) and other household devices that may have weaker security profiles.
5. **Guest Network Isolation.** If hosting visitors, use a separate guest network that does not provide access to the primary network segment used for remote work.
6. **DNS Security.** Consider configuring home networks to use a secure DNS provider (e.g., Cloudflare 1.1.1.2 for Families, Quad9, or OpenDNS) to provide basic protection against known malicious domains.
7. **Public and Shared Networks.** When working from public locations (coffee shops, airports, hotels), always connect through the university VPN before accessing any university resources. Avoid accessing Restricted or Confidential data from public networks whenever possible.

## 7.0 Compliance and Enforcement

### 7.1 Monitoring

The Office of Information Technology reserves the right to monitor VPN connections, endpoint compliance status, and network traffic patterns to ensure adherence to this policy. Monitoring activities will be conducted in accordance with the Northfield University Electronic Monitoring and Privacy Policy (NUOIT Policy 2026-EMP-04).

### 7.2 Violations

Violations of this policy may result in:

- Immediate suspension of remote access privileges;
- Disconnection of non-compliant devices from the university network;
- Referral to Human Resources for disciplinary action, up to and including termination of employment;
- Referral to the Office of General Counsel if the violation involves a breach of legal or regulatory obligations;
- For students employed by the university, referral to the Office of Student Conduct.

### 7.3 Incident Reporting

Remote workers who suspect a security incident (lost/stolen device, malware infection, unauthorized access, or data exposure) must report the incident immediately to the Northfield University IT Service Desk at **help@northfield.edu** or **(555) 123-4500**, and file an incident report through the IT Service Management portal. Prompt reporting is critical to minimizing the impact of security incidents.

## 8.0 Related Policies and References

| Document | Policy Number |
|----------|---------------|
| Acceptable Use and Guest Network Policy | NUOIT Policy 2026-AUP-03 |
| Data Classification and Handling Policy | NUOIT Policy 2026-DCH-02 |
| Electronic Monitoring and Privacy Policy | NUOIT Policy 2026-EMP-04 |
| Identity and Access Management Standard | NUOIT Policy 2026-IAM-05 |
| Incident Response Plan | NUOIT Policy 2026-IRP-06 |
| NIST SP 800-46 Rev. 2, Guide to Enterprise Telework | — |
| NIST SP 800-114 Rev. 1, User's Guide to Telework Security | — |

## 9.0 Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | August 15, 2024 | Information Security Office | Initial release |
| 2.0 | February 1, 2026 | Dr. Michael Chen, CISO | Major revision: updated BYOD requirements, added VPN exception process, expanded home network guidance, aligned with NUOIT Policy 2026-AUP-03 |

---
*Synthetic document for a take-home assignment. Not an official NYU policy. | Northfield University Office of IT*
