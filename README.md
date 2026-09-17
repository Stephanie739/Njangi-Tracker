
Njangi Tracker
A digital home for one of Africa's oldest financial systems
What This Project Is

Across Cameroon and much of West and Central Africa, millions of people already practice a form of community banking that predates any bank branch reaching their neighborhood: the Njangi — also called a tontine, esusu, or chama depending on the country. A group of people — neighbors, market women, colleagues, church members, classmates — agree to contribute a fixed amount of money on a regular schedule (weekly, biweekly, or monthly). Each round, the entire pooled amount goes to one member. The rotation continues until every member has received a payout once, at which point the group either disbands or starts again.

It works because it runs on trust. And that is also exactly where it breaks down.

Njangi Tracker is a web application that gives these groups the one thing they've never had: a shared, tamper-evident digital record of who paid, who owes, who's next, and who can be trusted with more responsibility — without asking anyone to give up how they already do things. Members still send money the way they always have, by mobile money, bank transfer, or cash in hand. The app's job is to remember everything correctly, transparently, and automatically, so no one has to rely on a notebook, a WhatsApp thread, or one person's memory.

Note: This system is a digital ledger, not a payment processor. It does not hold, move, or have access to real money — contributions continue to be collected the way they already are (cash or mobile money), and simply get recorded here for transparency.

The Problem This Solves
Njangi groups are almost universally run on paper notebooks, spoken agreements, or scattered WhatsApp messages. This works fine until it doesn't — and when it doesn't, it tends to fail in the same few ways, over and over, in groups all over the region:

Disputes over who paid. Without a shared, timestamped record, "I already sent it" versus "I never received it" becomes a he-said-she-said that can quietly end friendships and family relationships.
A single point of failure. One person — usually a treasurer — holds the entire group's financial memory in their head or their notebook. If they make a mistake, disappear, or act in bad faith, the whole group has no recourse.
No accountability for reliability. A member who always pays late, or never pays at all, is treated exactly the same as a member who has never missed a contribution. There is no cost to unreliability and no reward for consistency.
A rigid, unforgiving schedule. Life doesn't wait for your turn in the rotation. If someone has a genuine emergency three months before their scheduled payout, the traditional system offers no legitimate way to move up — only informal favors and awkward begging.
Idle money. Late fees, unclaimed reserves, and penalty payments usually just... sit there, or get absorbed by the treasurer, instead of benefiting the group that generated them.

Njangi Tracker directly targets every one of these failure points — not by replacing the social trust that makes Njangi work, but by backing it with a system that remembers perfectly, treats every member fairly, and turns "trust" from a vague feeling into something the group can actually see and measure.

How It Works
The core loop: groups, members, and rotation

A Group Admin (usually the person who already plays treasurer in real life) creates a group in the app, sets the contribution amount and payment frequency, and adds every member. When the group starts its first cycle, the app assigns the first recipient and opens a contribution window. As members pay, the app tracks each contribution's status automatically:

Paid — full amount, on or before the due date
Partial — something was paid, but less than expected
Late — the full amount arrived, but after the deadline
Missed — nothing arrived, and the deadline has passed

Once every member has paid in full, the Group Admin closes the cycle. The app hands the pool to that round's recipient, automatically advances the rotation to the next member in line, and opens the next cycle — no manual recalculation, no arguing about whose turn it is.

Beyond record-keeping: the loan feature

Money doesn't have to sit idle between rotations. A member facing an unexpected expense can request a loan directly against the group's current pool. The Group Admin approves it, the system disburses it, and the borrower repays in installments — with a small interest rate that stays with the group rather than going to an outside lender. This mirrors what many real Njangi groups already do informally; the app just makes it visible, trackable, and fair to everyone, not just whoever the treasurer likes best.

What makes this different from "just digitizing the notebook"

Most tools that claim to modernize Njangi groups stop at exactly that — a digital version of the same paper ledger. Njangi Tracker goes further, borrowing ideas from real financial systems and adapting them to how these groups actually behave in practice.

1. Credit Reliability Scoring & Collateral Locking

Every member builds a Reliability Index over time, calculated from their real payment history — on-time contributions weighed against delays, partial payments, and misses. This turns "so-and-so is unreliable" from gossip into a transparent, data-backed number the whole group can see.

That score isn't just for show. Members with a lower reliability score are required to keep a Collateral Guarantee Pool — a portion of their own round share (for example, 20%) held in escrow within the collective pool until they've fulfilled their responsibilities for that round. If a member defaults on a contribution, the system applies automated penalty deductions, drawn from their eventual payout or dividend rights, rather than leaving the group to absorb the loss or chase the person down themselves.

This is the foundation the other two features are built on top of.

2. Dynamic Rotation Bidding & Position Swapping

The traditional Njangi rotation is fixed the day the group forms — which is exactly the problem when real life doesn't cooperate with a schedule set months in advance. Njangi Tracker introduces two ways to make the rotation flexible without making it chaotic:

Emergency Bidding — a member facing a genuine cash shortfall ahead of their scheduled turn can place a bid (a small rebate or bonus fee) to move their payout earlier, compensating the group for the inconvenience rather than simply asking for a favor.
Consensual Peer Swapping — two members can propose and approve a direct 1-on-1 trade of their rotation slots. The app recalculates the full payout schedule automatically the moment both sides agree — no spreadsheet edits, no confusion about who agreed to what.

3. Automated Cycle Closing & Performance Dividends

In a traditional group, late fees and unused reserves rarely go anywhere productive — money just sits, gets forgotten, or disappears into a single person's hands. Njangi Tracker pools that money and returns it to the members who actually deserve it: at the close of each rotation, members who paid in full, on time, and maintained a minimum reliability score (for example, ≥ 70%) become eligible for a proportional dividend, redistributed from that period's accumulated penalties and unused reserves. Punctuality is no longer just a personal virtue — it pays.

Software Development Methodology

This project follows a lightweight Scrum approach, organized around GitHub's native project management tools:

Product Backlog — tracked as GitHub Issues, one per task (see docs/github_issues.md for the original templates)
User Stories — see docs/user_stories.md, organized into epics with Given/When/Then acceptance criteria
Sprints — tracked via GitHub Milestones
Sprint Board — tracked via this repository's GitHub Project (Kanban) board
Team Organization — each of the four members owns a distinct area of the system, working on individual branches and merging into main via Pull Requests that reference the issue they close (e.g. Closes #1)git