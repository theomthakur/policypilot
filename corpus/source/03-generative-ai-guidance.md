# Northfield University Office of Information Technology

## Generative AI and Large Language Model Usage Guidance

**Document Number:** NUOIT Policy 2026-AI-01
**Effective Date:** March 1, 2026
**Version:** 1.0
**Classification:** Level 2 – Internal
**Responsible Office:** Office of Information Technology, Information Security & Risk Management
**Approved By:** Dr. Sandra Meyers, Vice Provost for Information Technology & CIO
**Last Reviewed:** February 15, 2026
**Next Scheduled Review:** September 1, 2026

---

## 1.0 Purpose and Scope

### 1.1 Purpose

This document provides university-wide guidance on the acceptable and responsible use of generative artificial intelligence (GenAI) tools and large language models (LLMs) by Northfield University faculty, staff, researchers, and students. As AI technologies evolve rapidly, this guidance establishes a framework to promote innovation while safeguarding university data, preserving academic integrity, and ensuring compliance with applicable regulations and contractual obligations.

### 1.2 Scope

This policy applies to all members of the Northfield University community, including but not limited to:

- Full-time and part-time faculty
- Staff and administrators across all departments
- Graduate and undergraduate students
- Visiting scholars, contractors, and affiliates with access to university systems or data

This guidance covers the use of any generative AI tool or large language model, whether accessed via web browser, API, desktop application, mobile application, or integrated development environment plugin. Examples include, but are not limited to:

- OpenAI ChatGPT and GPT-series APIs
- Microsoft Copilot (consumer and enterprise editions)
- Google Gemini
- Anthropic Claude
- Meta Llama-based tools
- GitHub Copilot
- Midjourney, DALL·E, Stable Diffusion (image generation)
- Locally hosted or self-deployed open-source models

### 1.3 Related Policies

This guidance should be read in conjunction with the following Northfield University policies:

| Policy Number | Title |
|---|---|
| NUOIT Policy 2024-SEC-04 | Acceptable Use of Information Technology Resources |
| NUOIT Policy 2025-DCS-01 | Data Classification Standard and Handling Procedures |
| NUOIT Policy 2024-CLD-08 | Third-Party Cloud Vendor Assessment Policy |
| NUOIT Policy 2024-PRI-03 | Privacy and Personally Identifiable Information (PII) Policy |
| NUOIT Policy 2025-RES-02 | Research Data Management and Security Policy |
| NU Academic Affairs | Academic Integrity Policy (2024–2025 Academic Catalog) |

---
<!-- PAGE BREAK -->
---

## 2.0 Definitions and Data Restrictions

### 2.1 Definitions

- **Generative AI (GenAI):** Artificial intelligence systems capable of generating text, code, images, audio, video, or other content in response to user prompts. This includes large language models (LLMs), diffusion models, and multimodal foundation models.
- **Publicly Available AI Tool:** A generative AI tool offered to the general public, typically via a free or individually paid subscription, where the provider's standard consumer terms of service apply. Examples include consumer versions of ChatGPT, Google Gemini, and Claude.
- **University-Contracted Enterprise AI Tool:** A generative AI tool procured by Northfield University under an institutional license or agreement that includes negotiated data protection terms, a signed Data Protection Agreement (DPA), and successful completion of the Third-Party Cloud Vendor Assessment (NUOIT Policy 2024-CLD-08). Examples include Microsoft 365 Copilot (enterprise tenant), Northfield AI Sandbox, and approved API endpoints provisioned through NUOIT.
- **Prompt Data:** Any information—including text, code, files, images, or data—submitted to a generative AI tool as part of a query, instruction, or conversation.

### 2.2 Categories of Generative AI Tools

Northfield University recognizes two categories of generative AI tools, each with distinct data-handling permissions:

| Category | Description | Data Protection Agreement | Vendor Assessment | Examples |
|---|---|---|---|---|
| **Category A – University-Contracted Enterprise Tools** | Licensed by NUOIT under institutional agreements with negotiated data protections | Yes (signed DPA) | Completed per NUOIT Policy 2024-CLD-08 | Microsoft 365 Copilot (NU tenant), Northfield AI Sandbox, approved Azure OpenAI endpoints |
| **Category B – Publicly Available Tools** | Consumer-grade tools available to the general public under standard terms of service | No | Not completed | Consumer ChatGPT, Google Gemini, free-tier Claude, Midjourney |

A current list of approved Category A tools is maintained by the NUOIT AI Governance Team and published on the Northfield University IT website at `https://it.northfield.edu/ai/approved-tools`.

### 2.3 Data Restrictions for AI Tools

The handling of university data with generative AI tools is governed by the data classification levels defined in the **Northfield University Data Classification Standard and Handling Procedures** (NUOIT Policy 2025-DCS-01). All members of the university community must identify the classification level of any data before using it as prompt data in a generative AI tool.

Faculty and staff **must not** input, paste, or upload **Level 3 (Confidential) or Level 4 (Restricted) data** into any publicly available generative AI tool, including but not limited to consumer versions of ChatGPT, Google Gemini, and similar services. Level 1 (Public) and Level 2 (Internal) data may be used with **university-contracted enterprise AI tools** that have a signed data protection agreement and have completed the Third-Party Cloud Vendor Assessment (see NUOIT Policy 2024-CLD-08).

The following matrix summarizes permissible data usage by tool category:

| Data Classification Level | Category A – Enterprise Tools | Category B – Publicly Available Tools |
|---|---|---|
| **Level 1 – Public** | ✅ Permitted | ✅ Permitted |
| **Level 2 – Internal** | ✅ Permitted | ⚠️ Permitted with caution; no expectation of confidentiality |
| **Level 3 – Confidential** | ✅ Permitted with approved DPA and completed vendor assessment | ❌ **Prohibited** |
| **Level 4 – Restricted** | ⚠️ Permitted only with explicit CISO approval and enhanced safeguards | ❌ **Prohibited** |

> **Important:** Even when using approved enterprise tools, users must not include data beyond what is necessary to accomplish the task. The principle of data minimization applies at all times. For guidance on classifying specific data elements, refer to NUOIT Policy 2025-DCS-01, Appendix A: Data Classification Examples.

### 2.4 Prohibited Uses Across All Tools

Regardless of tool category, the following uses are prohibited:

1. Submitting student education records protected by FERPA to any AI tool without prior authorization from the Registrar and a completed privacy impact assessment.
2. Submitting protected health information (PHI) subject to HIPAA to any AI tool unless it operates within a NUOIT-approved BAA-covered environment.
3. Submitting payment card data (PCI DSS scope) to any AI tool.
4. Using AI-generated output to make final, unreviewed decisions regarding student admissions, financial aid, employment, disciplinary actions, or Title IX matters.
5. Submitting data subject to active non-disclosure agreements (NDAs) or export control restrictions (ITAR/EAR) without prior Legal Affairs and Export Control Office review.

---
<!-- PAGE BREAK -->
---

## 3.0 Use Cases and Requirements

### 3.1 Administrative and Operational Use

Faculty and staff may use generative AI tools to support administrative functions such as drafting communications, summarizing meeting notes, generating first drafts of non-sensitive reports, brainstorming, and developing training materials—provided they comply with the data restrictions in Section 2.3.

**Requirements:**

- All AI-generated content used in official university communications must be reviewed and approved by a human author before distribution.
- Users must not represent AI-generated content as solely their own original work in contexts where attribution matters (e.g., policy drafting, official reports to accrediting bodies).
- Departments adopting AI tools for workflow automation must notify NUOIT to ensure alignment with security and licensing requirements.

### 3.2 Research Use

Northfield University encourages the responsible use of generative AI in research, including for literature review assistance, code generation, data analysis support, hypothesis exploration, and manuscript drafting.

**Requirements:**

- **IRB Protocols:** If AI tools are used in human subjects research, the use must be described in the IRB protocol. Researchers must assess whether prompts or outputs constitute identifiable data.
- **Data Handling:** Research data classified as Level 3 or Level 4 under NUOIT Policy 2025-DCS-01 must only be used with Category A enterprise tools, subject to the restrictions in Section 2.3. Sponsored research data may carry additional funder-imposed restrictions.
- **Reproducibility:** Researchers are encouraged to document AI tool names, versions, model identifiers, and prompt strategies to support reproducibility. Where feasible, locally hosted open-source models are recommended for sensitive research workflows.
- **Grant Compliance:** Use of AI tools on federally funded research must comply with applicable sponsor requirements (e.g., NSF, NIH, DOD data management plans). The Office of Sponsored Programs can assist with compliance review.
- **Intellectual Property:** Questions regarding ownership of AI-generated content in the context of university research should be directed to the Office of General Counsel and the Office of Technology Licensing.

### 3.3 Teaching and Learning

Faculty may integrate generative AI tools into course design and pedagogy at their discretion, subject to academic integrity policies and departmental guidelines.

**Guidance for Faculty:**

- Faculty who permit or require AI tool usage in coursework should clearly state expectations in the course syllabus, including which tools are permitted, acceptable use cases, and citation requirements.
- Faculty who prohibit AI tool usage should state this clearly and explain the pedagogical rationale.
- The Center for Teaching and Learning offers workshops and consultation on integrating AI tools effectively and ethically.

### 3.4 Student Use and Academic Integrity

Students must comply with the **Northfield University Academic Integrity Policy** when using generative AI tools. Unless a course instructor explicitly permits the use of AI tools for a specific assignment, students must assume that AI-assisted work is not permitted.

**Student Responsibilities:**

1. **Obtain permission** before using AI tools on any graded assignment, exam, or academic exercise.
2. **Disclose and cite** AI-assisted work as required by the instructor and in accordance with the citation guidelines published by the University Writing Center.
3. **Verify accuracy** of all AI-generated content. Students bear full responsibility for the correctness, originality, and integrity of submitted work.
4. **Do not submit** AI-generated text, code, or other output as entirely their own original work unless the instructor has explicitly authorized such use.

Violations of these requirements may constitute academic dishonesty and are subject to sanctions under the Academic Integrity Policy, ranging from a failing grade on the assignment to suspension or expulsion.

---
<!-- PAGE BREAK -->
---

## 4.0 Vendor Assessment and Procurement

### 4.1 Third-Party AI Vendor Assessment

Any generative AI tool that will process, store, or transmit **Level 2 (Internal) or higher** university data under an institutional agreement must undergo the Northfield University Third-Party Cloud Vendor Assessment process as defined in **NUOIT Policy 2024-CLD-08** before deployment.

The assessment evaluates:

- Data residency and storage locations
- Encryption practices (in transit and at rest)
- Model training policies (whether user data is used to train models)
- Sub-processor disclosures
- Incident response and breach notification commitments
- Data retention and deletion practices
- Regulatory compliance (FERPA, HIPAA, GLBA, GDPR where applicable)

### 4.2 Procurement Process

Departments or units wishing to procure a generative AI tool or service for institutional use must follow this process:

1. **Submit an AI Tool Request** via the NUOIT Service Portal (`https://it.northfield.edu/ai/request`).
2. **NUOIT AI Governance Review:** The request is reviewed for alignment with university policies, data classification requirements, and existing tool availability.
3. **Vendor Security Assessment:** If approved for further evaluation, the tool undergoes the Third-Party Cloud Vendor Assessment (NUOIT Policy 2024-CLD-08).
4. **Legal Review:** The Office of General Counsel reviews the vendor agreement, data protection addendum, and terms of service.
5. **Approval and Provisioning:** Upon successful completion of all reviews, NUOIT provisions the tool and communicates approved use parameters to the requesting department.

> **Note:** Individual faculty or staff members may not independently sign license agreements or terms of service for AI tools that will process institutional data classified at Level 2 or above. All such agreements must be executed through NUOIT and the Office of General Counsel.

### 4.3 Shadow AI and Unsanctioned Tool Use

The use of unsanctioned generative AI tools—sometimes referred to as "shadow AI"—to process university data above Level 1 (Public) poses significant security, privacy, and compliance risks. NUOIT may monitor network traffic patterns to identify unsanctioned AI tool usage and will work with departments to remediate risks.

Faculty, staff, or students who identify a need not met by currently approved tools should submit a request through the NUOIT Service Portal rather than adopting unsanctioned alternatives.

## 5.0 Roles and Responsibilities

| Role | Responsibilities |
|---|---|
| **Chief Information Security Officer (CISO)** | Approves exceptions for Level 4 data use with enterprise AI tools; oversees AI-related risk assessments |
| **NUOIT AI Governance Team** | Maintains the approved tools list; conducts vendor assessments; provides guidance to the university community |
| **Deans and Department Heads** | Ensure departmental compliance with this guidance; support faculty awareness |
| **Faculty** | Clearly communicate AI use expectations in syllabi; model responsible use |
| **Staff** | Comply with data restrictions; report concerns to NUOIT |
| **Students** | Follow instructor and university policies on AI use; maintain academic integrity |
| **Office of General Counsel** | Reviews AI vendor contracts; advises on intellectual property and liability questions |

## 6.0 Enforcement and Exceptions

Violations of this guidance may result in disciplinary action in accordance with applicable university policies, including the Acceptable Use of Information Technology Resources policy (NUOIT Policy 2024-SEC-04), the Academic Integrity Policy, and applicable employment policies.

Requests for exceptions to any provision of this guidance must be submitted in writing to the NUOIT AI Governance Team at `ai-governance@northfield.edu` and must include a risk assessment and business justification. Exception requests involving Level 4 (Restricted) data require CISO approval.

## 7.0 Document History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | March 1, 2026 | NUOIT AI Governance Team | Initial publication |

---
*Synthetic document for a take-home assignment. Not an official NYU policy. | Northfield University Office of IT*
