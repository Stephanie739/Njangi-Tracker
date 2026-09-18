# Njangi Tracker

A web application that digitizes the management of a **njangi** (also known as a *tontine*) — a rotating savings and credit group where members contribute a fixed amount regularly, and one member receives the full pooled amount each cycle, on rotation.
Njangi Tracker A digital home for one of Africa's oldest financial systems What This Project Is

---

## Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Testing](#testing)
- [Methodology](#methodology)
- [Team](#team)
- [Course Information](#course-information)

---

## The Problem

Njangis are a widespread informal savings practice across Cameroon, but are almost always managed through paper notebooks, memory, or scattered WhatsApp messages. This leads to lost records, disputes over who has paid, confusion about whose turn is next, and no reliable history when conflicts arise.
Across Cameroon and much of West and Central Africa, millions of people already practice a form of community banking that predates any bank branch reaching their neighborhood: the Njangi — also called a tontine, esusu, or chama depending on the country. A group of people — neighbors, market women, colleagues, church members, classmates — agree to contribute a fixed amount of money on a regular schedule (weekly, biweekly, or monthly). Each round, the entire pooled amount goes to one member. The rotation continues until every member has received a payout once, at which point the group either disbands or starts again.


## The Solution

Njangi Tracker replaces manual bookkeeping with a transparent web application where an admin creates a group, adds members, and logs contributions — while the system automatically manages the rotation order, classifies payment status, and keeps a full permanent history of every cycle.
Njangi Tracker is a web application that gives these groups the one thing they've never had: a shared, tamper-evident digital record of who paid, who owes, who's next, and who can be trusted with more responsibility — without asking anyone to give up how they already do things. Members still send money the way they always have, by mobile money, bank transfer, or cash in hand. The app's job is to remember everything correctly, transparently, and automatically, so no one has to rely on a notebook, a WhatsApp thread, or one person's memory.


> **Scope note:** This system is a digital ledger, not a payment processor. It does not hold, move, or have access to real money. Contributions continue to be collected the way they already are today (cash or mobile money) and are simply recorded here for transparency and accountability.

**How It Works The core loop: groups, members, and rotation**

A Group Admin (usually the person who already plays treasurer in real life) creates a group in the app, sets the contribution amount and payment frequency, and adds every member. When the group starts its first cycle, the app assigns the first recipient and opens a contribution window. As members pay, the app tracks each contribution's status automatically:

Paid — full amount, on or before the due date Partial — something was paid, but less than expected Late — the full amount arrived, but after the deadline Missed — nothing arrived, and the deadline has passed

Once every member has paid in full, the Group Admin closes the cycle. The app hands the pool to that round's recipient, automatically advances the rotation to the next member in line, and opens the next cycle — no manual recalculation, no arguing about whose turn it is.

Beyond record-keeping: the loan feature

Money doesn't have to sit idle between rotations. A member facing an unexpected expense can request a loan directly against the group's current pool. The Group Admin approves it, the system disburses it, and the borrower repays in installments — with a small interest rate that stays with the group rather than going to an outside lender. This mirrors what many real Njangi groups already do informally; the app just makes it visible, trackable, and fair to everyone, not just whoever the treasurer likes best.

## Features

- Create a njangi group with a custom contribution amount and frequency
- Add members to a group
- **Automatic rotation logic** — recalculated from stored history rather than a fragile in-memory queue, so it's always correct even after restarting the app
- Log member contributions with automatic status classification: **Paid / Partial / Late / Missed / Pending**
- Automatic total pool calculation per cycle
- Dashboard showing current cycle status, who still owes, and who's next in line
- Full historical record of every past cycle
- Close a cycle once every member has paid in full
- Each group's data is kept fully separate from other groups (multi-tenancy via `group_id`)

---

## Architecture

The application is split into three independent layers, so each one can be built, understood, and tested without needing the others:

```
┌─────────────────────────────┐
│   app.py (Flask routes)     │  <- receives web requests
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│   service.py                 │  <- connects logic to storage
│   (the only file that        │
│    imports BOTH sides below) │
└──────┬────────────────┬──────┘
       │                │
┌──────▼──────┐  ┌──────▼───────┐
│ models.py   │  │ database.py  │
│ (business   │  │ (SQLite      │
│  logic)     │  │  storage)    │
└─────────────┘  └──────────────┘
```

- **`models.py`** knows the *rules* (rotation order, what counts as "late") but nothing about databases.
- **`database.py`** knows how to *store and retrieve rows* but has zero business logic.
- **`service.py`** is the bridge: it calls `database.py` to fetch data, uses `models.py`'s classes to apply the correct rules to that data, and saves the result back.

This separation means `models.py`'s logic has been fully unit-tested on its own, with no database required.

---

## Tech Stack

| Layer | Technology | Role |
|---|---|---|
| Backend | Python 3 + Flask | Web routes, request handling |
| Business logic | Plain Python (OOP) | Rotation rules, payment status rules |
| Database | SQLite | Permanent storage — no server required |
| Frontend | HTML + CSS | java script |
| Testing | Python `unittest` | Automated verification of core logic |
| Version control | Git + GitHub | Source control, Issues, Milestones, Project board |
| Deployment | Render / PythonAnywhere | Public live hosting |

---

## Project Structure

```
njangi-tracker/
├── models.py            # Member, Contribution, Cycle, NjangiGroup, PaymentStatus
├── database.py          # Table creation + INSERT/SELECT/UPDATE for all 4 tables
├── service.py           # Connects models.py logic with database.py storage
├── app.py               # Flask routes (Create Group, Add Member, Log Payment, Dashboard...)
├── njangi.db            # SQLite database file (created automatically, not committed)
├── templates/
│   ├── create_group.html
│   ├── add_member.html
│   ├── log_payment.html
│   ├── dashboard.html
│   └── cycle_history.html
├── static/
│   └── style.css
├── tests/
│   └── test_models.py   # unittest suite
├── docs/
│   ├── use_case_diagram.png
│   ├── class_diagram.png
│   └── sequence_diagrams/
└── README.md
```

### Database Schema

Four linked tables, each `Member`/`Cycle`/`Contribution` tagged with the `group_id` (or `cycle_id`) it belongs to, which is what keeps different njangi groups' data separate:

```
groups (group_id, group_name, contribution_amount, frequency_days)
   │
   ├── members (member_id, group_id, name, phone_number, join_date)
   │
   └── cycles (cycle_id, group_id, cycle_number, recipient_id, due_date, closed)
           │
           └── contributions (contribution_id, cycle_id, member_id,
                               amount_expected, amount_paid, status, date_paid)
```

---


## Testing

Core business logic (`models.py`) and persistence (`database.py`) are covered by a `unittest` suite:

```bash
python3 -m unittest discover tests
```

Covered scenarios include: correct rotation order across multiple cycles, Paid/Partial/Late/Missed/Pending classification, pool total calculation, and cycle-closing logic (a cycle cannot close until every member has paid in full).

---

## Methodology

Developed using **Agile (Scrum)** across a 5-week sprint plan (25 August – 28 September 2026), tracked through:
- **GitHub Issues** — the product backlog, one issue per feature
- **GitHub Milestones** — one per sprint/phase, each with a due date
- **GitHub Project board** — visual To Do / In Progress / Done tracking
- **Commit history** — each feature closed via `Closes #<issue>` in commit messages

| Sprint | Focus |
|---|---|
| 1 | Team & GitHub setup, requirements gathering |
| 2 | Requirements finalization, design start |
| 3 | UML: use case diagram, class diagram, 5 sequence diagrams |
| 4 | Core implementation: routes, pages, integration |
| 5 | Testing, deployment, report, presentation |

---

## Team

| Name | Role |
|---|---|
| [NZEKO PRINCESSE S.] | Scrum Master|
| [TANTOH PEREVET ] |Product Owner|
| [NDOUTOU ULRICH] | Member|
| [NGUEYA AUDREY] | Memebr |



