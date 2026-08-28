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
def add_contribution(member_id, cycle_id, amount, payment_status):
    """
    Record a contribution made by a member
    Parameters:
        member_id (int): The ID of the member
        cycle_id (int): The ID of the cycle
        amount (float): The amount contributed
        payment_status (str): The status of the payment
    """
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO contributions (member_id, cycle_id, amount, payment_status)
        VALUES (?, ?, ?, ?)
        """, (member_id, cycle_id, amount, payment_status))
    connection.commit()
    contribution_id = cursor.lastrowid
    connection.close()
    return contribution_id
#create the NjangiGroup table
#this table stores informations about each njangi group
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
  
   