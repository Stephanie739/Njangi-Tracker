#we use the SQlite to store the Njangi Tracker data
import sqlite3
#sqlite3 is Python's build-in module for working in SQlite database
def connect_db():
#connect to database
    """
    Connect to the Njangi SQlite Database.
    If the database file doesn't exist,
    SQlite will create it automatically
    """
    connection = sqlite3.connect("njangi.db")
#connection represent our connection to the database
    return connection
#create the database table
def create_tables():
    """
    Create all the table needed for the Njangi Tracker,
    if they donot already exist.
    """
#this table stores informations about each njangi group
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups(
        group_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contribution_amount REAL NOT NULL,
        frequency TEXT NOT NULL
        )
        """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members(
            member_id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            FOREIGN KEY (group_id) REFERENCES groups(group_id)
        )
        """)
#create cycle table
#this table stores information about each cycle(round) of a njangi group
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cycles(
            cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            cycle_number INTEGER NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (member_id) REFERENCES members(member_id)
        )
        """)
#contribution table
# this table shows the contribution/records that each member has done in the Njangi cycle
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contributions(
            contribution_id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            cycle_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_status TEXT NOT NULL,
            FOREIGN KEY (member_id) REFERENCES members(member_id),
            FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id)
        )
        """) 
    connection.commit()
    connection.close()

#add a njangi group
def add_group(name, contribution_amount, frequency):
    """
    Add a new Njangi group to the database.
    Parameters:
    name (str): The name of the Njangi group
    contribution_amount (float): The amount each member contributes
    frequency (str): how often members contribute
    """
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO groups (name, contribution_amount, frequency)
        VALUES (?, ?, ?)
        """, (name, contribution_amount, frequency))
#VALUES (?, ?, ?) is a safety way to send python values to SQLite
    connection.commit()
#get the ID created auomatically by the SQLite
    group_id = cursor.lastrowid
    connection.close()
    return group_id
def add_member(group_id, name, phone):
    """
    Add a member to an existing Njangi group
    Parameters:
        group_id (int): The ID of the Njangi group
        name (str): The name of the member
        phone (str): The phone number of the member
    """
    connection = connect_db()
    cursor = connection.cursor()
#insert the member
    cursor.execute("""
        INSERT INTO members (group_id, name, phone)
        VALUES (?, ?, ?)
        """, (group_id, name, phone))
    connection.commit()
    member_id = cursor.lastrowid
    connection.close()
    return member_id
def add_cycle(member_id, cycle_number, status="OPEN"):
    """
    Create a new cycle for a Njangi group;
    Parameters:
        member_id (int): The ID of the member
        cycle_number (int): The number of the cycle
        status (str): current status of the cycle (default is "OPEN")
        """
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO cycles (member_id, cycle_number, status)
        VALUES (?, ?, ?)
        """, (member_id, cycle_number, status))
    connection.commit()
    cycle_id = cursor.lastrowid
    connection.close()
    return cycle_id
def add_contribution(member_id, cycle_id, amount):
    """
    Record a contribution made by a member
    The payment_status is automatically determined according the to the expected contribution amount.
    """
#Get the expected contribution amount
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT groups.contribution_amount
        FROM groups
        JOIN members ON groups.group_id = members.group_id
        WHERE members.member_id = ?
        """, (member_id,))
    result = cursor.fetchone()
#check if the member exist
    if result is None:
        connection.close()
        print("Error: member not found")
        return None
    expected_amount = result[0]
#validate the amount
    if not validate_payment_amount(amount, expected_amount):
        connection.close()
        return None
    if amount == 0:
        payment_status = "Pending"
    elif amount < expected_amount:
        payment_status = "Partial"
    else:
        payment_status = "Paid"
    cursor.execute("""
    INSERT INTO contributions
    (member_id, cycle_id, amount, payment_status)
    VALUES(?, ?, ?, ?)
    """,(member_id, cycle_id, amount, payment_status))
    connection.commit()
    contribution_id = cursor.lastrowid
    connection.close()
    return contribution_id

def get_groups():
    """
    Get all Njangi groups from database.
    """
    conn = sqlite3.connect("njangi.db")
    cursor = conn.cursor()
#get the results from the database
    cursor.execute("SELECT * FROM groups")
#get all groups from the database
    groups = cursor.fetchall()
    conn.close()
    return groups
def get_members():
    """
    Get all the members from the database.
    """
    conn = sqlite3.connect("njangi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members")
    members = cursor.fetchall()
    conn.close()
    return members
def get_members_by_group(group_id):
    """
    Get all members who belongs to a specific Njangi group.
    """
    conn = sqlite3.connect("njangi.db")
    cursor = conn.cursor()
#get members that belong to a specific group using the group_id
    cursor.execute("SELECT * FROM members WHERE group_id = ?",
                   (group_id,)
                   )
    members = cursor.fetchall()
    conn.close()
    return members
def get_cycles():
    """
    Get all the cycles of the Njangi groups from the database.
    """
    conn = sqlite3.connect("njangi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cycles")
    cycles = cursor.fetchall()
    conn.close()
    return cycles
def get_contributions():
    """
    Get all the contributions made by the members in the database.
    """
    conn = sqlite3.connect("njangi.db")
#Get the expected contribution amount
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contributions")
    contributions = cursor.fetchall()
    conn.close()
    return contributions
def get_contributions_by_cycle(cycle_id):
    """
    Get all contributions made in a specific cycle.
    """
    conn = sqlite3.connect("njangi.db")
    cursor = conn.cursor()
#get contributions from the selected cycle
    cursor.execute("SELECT * FROM contributions WHERE cycle_id = ?",
                   (cycle_id,)
                   )
    contributions = cursor.fetchall()
    conn.close()
    return contributions

def get_cycle_total(cycle_id):
    """
    Calculate the total amount contributed during a specific cycle.
    """
    conn = connect_db()
    cursor = conn.cursor()
#Add together all contributions belonging to this cycle
    cursor.execute("""
        SELECT SUM(amount)
        FROM contributions
        WHERE cycle_id = ?
    """, (cycle_id,))
#Get the result
    result = cursor.fetchone()
    conn.close()
#if there are no contributions, SUM return None
    if result[0] is None:
        return 0
    return result[0]

def get_expected_pool(group_id):
    """
    Calculate the total expected amount of a Njangi group.
    Expected pool = number of members * contribution amount
    """
    conn = connect_db()
    cursor = conn.cursor()
#Get the contribution amount and the number of member
    cursor.execute("""
        SELECT groups.contribution_amount, COUNT(members.member_id)
        FROM groups
        LEFT JOIN members
        ON groups.group_id = members.group_id
        WHERE groups.group_id = ?
        GROUP BY groups.group_id
    """,(group_id,))
    result = cursor.fetchone()
    conn.close()
#Check if group exist
    if result is None:
        result = 0

    contribution_amount = result[0]
    number_of_members = result[1]
#calculate the pool expected
    expected_pool = contribution_amount * number_of_members
    return expected_pool

def get_pool_summary(group_id, cycle_id):
    """
    Get summary of the Njangi pool.
    Returns:
        expected_pool = total amount expected
        collected_pool = amount collected actually
        remaining_pool = amount still missing
        progress = percentage of the pool collected
    """
#Get the expected total
    expected_pool = get_expected_pool(group_id)
#Get the amount actually collected
    collected_pool = get_cycle_total(cycle_id)
#Calculate the remaining amount
    remaining_pool = expected_pool - collected_pool
#Calculate the percentage collected
    if expected_pool == 0:
        progress = 0
    else:
        progress = (collected_pool / expected_pool) * 100
    return {
        "expected_pool": expected_pool,
        "collected_pool": collected_pool,
        "remaining_pool": remaining_pool,
        "progress": progress
    }
    
def get_pending_contributions():
    """
    Get all the contributions that are still pending(not paid).
    """
    conn = sqlite3.connect("njangi.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM contributions 
        WHERE payment_status = 'PENDING'
    """)
    contributions = cursor.fetchall()
    conn.close()
    return contributions
def update_contribution_status(contribution_id, amount, status):
    """
    Update the payment status of a contribution
    """
    conn = sqlite3.connect("njangi.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE contributions
        SET amount = ?, payment_status = ?
        WHERE contribution_id = ?
        """, (amount, status, contribution_id)
        )
    conn.commit()
    conn.close()

def update_contribution_payment(contribution_id, amount, expected_amount):
    """
    Update a contribution and automatically determine its payment status.
    """
#validate the payment amount first
    if not validate_payment_amount(amount, expected_amount):
        return None
    # Check the amount paid
    if amount == 0:
        payment_status = "Pending"
    elif amount < expected_amount:
        payment_status = "Partial"
    else:
        payment_status = "Paid"

    # Connect to the database
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE contributions
        SET amount = ?, payment_status = ?
        WHERE contribution_id = ?
        """,(amount, payment_status, contribution_id))
    connection.commit()
    connection.close()
    return payment_status
def validate_payment_amount(amount, expected_amount):
    """
    Check whether a contribution amount is valid.
    Returns:
    True   -> payment is valid
    False  -> payment is invalid
    """
#A payment cannot be negative 
    if amount < 0:
        print("Error: payment amount cannot be negative.")
        return False
#A payment cannot be greater than the expected cntribution
    if amount > expected_amount:
        print("Error: payment cannot be greater than the expected contribtion.")
        return False
    #If all payment pass, the payment is valid
    return True
    