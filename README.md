Njangi Tracker
Collaborative Financial Tracking &amp; Rotational Savings Management System

1. Purpose of the Project
Traditional Njangi (tontine / rotational savings) groups frequently encounter challenges including
manual ledger errors, a lack of contribution transparency, delayed payments, and cumbersome
calculations during cycle closure.
The primary purpose of Njangi Tracker is to provide an accessible, transparent digital web platform that:
 Replaces error-prone manual paper ledgers with an interactive real-time dashboard.
 Fosters accountability and financial consistency among members via automated reliability tracking.
 Simplifies cycle closures, penalty pools, and dividend redistribution through proven algorithms.

2. Aims and Objectives
2.1 General Aim
To design, implement, and deploy a robust full-stack software application that automates member
administration, payment tracking, and rotational cycle resolutions for community savings groups.
2.2 Specific Objectives
 Interactive Member Portal: Provide group administrators with an intuitive web interface to monitor
member enrollment, expected contributions, and balances in real time.
 Dynamic Reliability Metric: Establish a dynamic 0–100% reliability metric that adjusts according to
individual payment behavior (on-time, partial, or late payments).
 Automated Dividend Redistribution: Implement cycleClosing.py to systematically redistribute group
reserves, interest, and penalty pools proportionally among compliant members.
 Architectural Integrity &amp; Testing: Follow Object-Oriented software design principles (supported by UML
use case, class, and sequence diagrams) and validate core modules using automated unit tests.

3. Key Features
 Real-Time Contribution Dashboard: Displays live summary statistics (Total Members, Fully Paid
Members, Outstanding Balances, Total Expected Funds) alongside individual status flags (Paid, Partial,
Pending).
 Behavioral Reliability Scoring: Every member begins with a baseline of 100%. Automatic deductions
occur when partial or delinquent payments are recorded, visually highlighted with green, orange, or red
badges.
 Automated Cycle Closing &amp; Dividend Calculation: Filters recipients based on complete contributions
(Paid) and a minimum reliability threshold (&gt;= 70%), distributing accumulated dividend pools
proportionally according to paid amounts.
 RESTful API Architecture: Clean endpoints (/api/members, /api/contributions, /api/cycle/close) ensuring
structured asynchronous communication between the Python backend and browser client.

4. Team Information
SN Member Name Registration
Number

Team Role GitHub Handle

1 [Lead Developer
Name]

[Reg Number] Project Lead / Full-

Stack

@username

2 [Member Name] [Reg Number] Frontend / UI-UX @username
3 [Member Name] [Reg Number] Backend Engineer @username
4 [Member Name] [Reg Number] QA / Testing
Engineer

@username

5. Technology Stack
 Backend: Python 3.x, Flask (Microframework)
 Frontend: HTML5, Modern CSS3 (Variables, Grid/Flexbox), Vanilla JavaScript (Async/Fetch API)
 Design &amp; Modeling: Object-Oriented Design (UML Use Case, Class, and Sequence Diagrams)
 Testing Framework: Python unittest framework

Upon cycle closure, dividend redistribution follows a weighted proportional model among verified
members:
Member Dividend = ( Member Contribution / Total Eligible Contributions ) × Total Pool
