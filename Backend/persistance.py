
from datetime import date

from models import PaymentStatus, Member, Contribution, Cycle, NjangiGroup
from loans import Loan, LoanStatus
from schema import get_connection, create_schema, DB_PATH


def save_group(group: NjangiGroup, conn=None) -> int:
   
    own_conn = conn is None
    conn = conn or get_connection()
    create_schema(conn)
    cur = conn.cursor()

    # --- group itself ---
    cur.execute(
        """
        INSERT INTO njangi_group (group_name, contribution_amount, frequency_days)
        VALUES (?, ?, ?)
        ON CONFLICT(group_name) DO UPDATE SET
            contribution_amount = excluded.contribution_amount,
            frequency_days = excluded.frequency_days
        """,
        (group.group_name, group.contribution_amount, group.frequency_days),
    )
    cur.execute("SELECT group_id FROM njangi_group WHERE group_name = ?", (group.group_name,))
    group_id = cur.fetchone()[0]

    queue_position = {m.member_id: i for i, m in enumerate(group.rotation_queue)}
    for m in group.members:
        cur.execute(
            """
            INSERT INTO member (member_id, group_id, name, phone_number, join_date, queue_position)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(member_id, group_id) DO UPDATE SET
                name = excluded.name,
                phone_number = excluded.phone_number,
                queue_position = excluded.queue_position
            """,
            (m.member_id, group_id, m.name, m.phone_number,
             m.join_date.isoformat(), queue_position.get(m.member_id)),
        )

    # --- cycles + contributions ---

    for cyc in group.cycles:
        cur.execute(
            """
            INSERT INTO cycle (group_id, cycle_number, recipient_id, due_date, closed)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(group_id, cycle_number) DO UPDATE SET
                recipient_id = excluded.recipient_id,
                due_date = excluded.due_date,
                closed = excluded.closed
            """,
            (group_id, cyc.cycle_number, cyc.recipient.member_id,
             cyc.due_date.isoformat(), int(cyc.closed)),
        )
        cur.execute(
            "SELECT cycle_pk FROM cycle WHERE group_id = ? AND cycle_number = ?",
            (group_id, cyc.cycle_number),
        )
        cycle_pk = cur.fetchone()[0]

        for member_id, contrib in cyc.contributions.items():
            cur.execute(
                "SELECT contribution_pk FROM contribution WHERE cycle_pk = ? AND member_id = ?",
                (cycle_pk, member_id),
            )
            existing = cur.fetchone()
            date_paid_str = contrib.date_paid.isoformat() if contrib.date_paid else None

            if existing:
                cur.execute(
                    """
                    UPDATE contribution
                    SET amount_expected = ?, amount_paid = ?, date_paid = ?, status = ?
                    WHERE contribution_pk = ?
                    """,
                    (contrib.amount_expected, contrib.amount_paid, date_paid_str,
                     contrib.status.value, existing[0]),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO contribution
                        (cycle_pk, member_id, group_id, amount_expected, amount_paid, date_paid, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (cycle_pk, member_id, group_id, contrib.amount_expected,
                     contrib.amount_paid, date_paid_str, contrib.status.value),
                )

    # --- loans ---

    for loan in group.loans:
        date_approved_str = loan.date_approved.isoformat() if loan.date_approved else None
        cur.execute(
            """
            INSERT INTO loan
                (loan_id, group_id, member_id, amount, interest_rate,
                 status, date_requested, date_approved, amount_repaid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(loan_id, group_id) DO UPDATE SET
                status = excluded.status,
                date_approved = excluded.date_approved,
                amount_repaid = excluded.amount_repaid
            """,
            (loan.loan_id, group_id, loan.member.member_id, loan.amount,
             loan.interest_rate, loan.status.value,
             loan.date_requested.isoformat(), date_approved_str, loan.amount_repaid),
        )

    conn.commit()
    if own_conn:
        conn.close()
    return group_id


def load_group(group_name: str, conn=None) -> NjangiGroup | None:
    """
    Rebuilds a full NjangiGroup (with its members, cycles, contributions
    and loans) from SQLite. Returns None if no group with that name
    exists.

    Task 5: this is the load-side of group separation — every SELECT
    below is filtered `WHERE group_id = ?`, so loading "Family Njangi"
    can never accidentally pull in another group's rows.
    """
    own_conn = conn is None
    conn = conn or get_connection()
    create_schema(conn)
    cur = conn.cursor()

    cur.execute(
        "SELECT group_id, contribution_amount, frequency_days FROM njangi_group WHERE group_name = ?",
        (group_name,),
    )
    row = cur.fetchone()
    if row is None:
        if own_conn:
            conn.close()
        return None
    group_id, contribution_amount, frequency_days = row

    group = NjangiGroup(group_name, contribution_amount, frequency_days)

    # --- members (scoped to this group_id) ---
    cur.execute(
        """
        SELECT member_id, name, phone_number, join_date, queue_position
        FROM member WHERE group_id = ? ORDER BY member_id
        """,
        (group_id,),
    )
    member_rows = cur.fetchall()
    members_by_id: dict[int, Member] = {}
    max_id = 0
    for member_id, name, phone_number, join_date_str, queue_position in member_rows:
        m = Member(member_id, name, phone_number)
        m.join_date = date.fromisoformat(join_date_str)
        members_by_id[member_id] = m
        group.members.append(m)
        max_id = max(max_id, member_id)
    group._next_member_id = max_id + 1

    queue_pairs = [
        (queue_position, member_id)
        for member_id, _, _, _, queue_position in member_rows
        if queue_position is not None
    ]
    queue_pairs.sort(key=lambda pair: pair[0])
    group.rotation_queue = [members_by_id[mid] for _, mid in queue_pairs]

    # --- cycles + contributions (scoped to this group_id) ---
    cur.execute(
        """
        SELECT cycle_pk, cycle_number, recipient_id, due_date, closed
        FROM cycle WHERE group_id = ? ORDER BY cycle_number
        """,
        (group_id,),
    )
    for cycle_pk, cycle_number, recipient_id, due_date_str, closed in cur.fetchall():
        recipient = members_by_id[recipient_id]
        due_date_obj = date.fromisoformat(due_date_str)

        cyc = Cycle(cycle_number, group.members, group.contribution_amount,
                    recipient, due_date_obj)
        cyc.closed = bool(closed)

        cur.execute(
            """
            SELECT member_id, amount_expected, amount_paid, date_paid, status
            FROM contribution WHERE cycle_pk = ?
            """,
            (cycle_pk,),
        )
        for m_id, amount_expected, amount_paid, date_paid_str, status_str in cur.fetchall():
            contrib = cyc.contributions.get(m_id)
            if contrib is None:
                continue
            contrib.amount_expected = amount_expected
            contrib.amount_paid = amount_paid
            contrib.date_paid = date.fromisoformat(date_paid_str) if date_paid_str else None
            contrib.status = PaymentStatus(status_str)

        group.cycles.append(cyc)

    # --- loans (scoped to this group_id) ---
    cur.execute(
        """
        SELECT loan_id, member_id, amount, interest_rate, status,
               date_requested, date_approved, amount_repaid
        FROM loan WHERE group_id = ? ORDER BY loan_id
        """,
        (group_id,),
    )
    max_loan_id = 0
    for (loan_id, member_id, amount, interest_rate, status_str,
         date_requested_str, date_approved_str, amount_repaid) in cur.fetchall():
        member = members_by_id.get(member_id)
        if member is None:
            continue
        loan = Loan(loan_id, member, amount, interest_rate)
        loan.status = LoanStatus(status_str)
        loan.date_requested = date.fromisoformat(date_requested_str)
        loan.date_approved = date.fromisoformat(date_approved_str) if date_approved_str else None
        loan.amount_repaid = amount_repaid
        group.loans.append(loan)
        max_loan_id = max(max_loan_id, loan_id)
    group._next_loan_id = max_loan_id + 1

    if own_conn:
        conn.close()
    return group


def list_group_names(conn=None) -> list:
    own_conn = conn is None
    conn = conn or get_connection()
    create_schema(conn)
    cur = conn.cursor()
    cur.execute("SELECT group_name FROM njangi_group ORDER BY group_name")
    names = [row[0] for row in cur.fetchall()]
    if own_conn:
        conn.close()
    return names