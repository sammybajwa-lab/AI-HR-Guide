# MF-POL-703 — HR Case Handling, Privacy, and Escalation

**Owner:** People Operations  
**Effective:** 1 May 2026  
**Policy version:** 1.6

## 1. Purpose
HR cases are used to route employee questions, requests, and concerns to the right owner while limiting unnecessary collection of personal information. A case record should contain enough information to understand the issue and next step, but not unrelated private detail.

## 2. Case categories
Common categories include pay and time, benefits, leave, accommodation, workplace conduct, manager support, work location, onboarding, employment records, and policy clarification. A case can have more than one category when the issues are connected.

## 3. Required information
A routine case normally needs the employee ID or other verified identity, a short description of the request, relevant dates, and the outcome requested. Additional fields should be collected only when they are needed for routing or decision-making.

For work-location cases, include destination and expected duration. For PTO questions, include the requested dates or number of hours when a balance determination is needed. For expense questions, include item type, amount, and whether purchase has already occurred.

## 4. Sensitive matters
Medical detail, allegations of harassment, immigration documents, identity documents, and security credentials should not be copied into a general case description unless the approved process requires it. The case should instead note that sensitive documentation is held in the designated system.

## 5. Escalation levels
**Routine:** policy explanation, record correction, ordinary benefits or PTO question.  
**Specialist review:** accommodation, leave, tax, immigration, payroll dispute, security review, or unclear policy conflict.  
**Urgent:** immediate safety threat, credible threat of violence, active security incident, or another situation where delay could cause serious harm.

The assistant should classify the routing need without making findings about disputed facts.

## 6. Creating a case
An automated system may draft a case summary. It may not create a final external or irreversible action without user confirmation. In this project, `create_mock_hr_ticket` is deliberately a mock operation. When `confirmed=false`, the tool returns a preview and does not write the ticket. When `confirmed=true`, it writes only to the synthetic runtime data file.

## 7. Manager messages
The assistant may draft a manager or People Operations message, but it does not send messages. The user remains responsible for reviewing the draft, especially when it contains sensitive facts.

## 8. Service expectations
Routine cases should be acknowledged within two business days when staffing allows. Urgent safety and security matters follow the incident process rather than the routine queue. This target is an operating expectation, not a guarantee of resolution within two days.

## 9. Records and retention
HR case records are company records and should be stored only in approved systems. Retention periods depend on case type and legal requirements. Employees should not create shadow case files in personal storage.

## 10. Evidence and uncertainty
When a policy question cannot be resolved from available sources, the case should state the unresolved point and route it to the owner. The assistant must not invent a policy, approval, balance, employment fact, or legal conclusion to make the response feel complete.
## 11. Case-writing standard
A good case summary is factual and short. It states who is requesting help, what happened or what decision is needed, relevant dates, the policy area, and the next owner. It avoids speculation about motive, diagnosis, legal liability, or credibility. When the employee's own wording matters, the summary can quote a brief phrase while keeping unnecessary sensitive detail out of the general record.

## 12. Duplicate and follow-up cases
If a new question clearly belongs to an open case, the employee should be directed to the existing case when practical. A new case can be appropriate when the subject is materially different, involves a separate confidentiality concern, or the existing case cannot be safely reused. The project mock tool does not merge cases automatically.
