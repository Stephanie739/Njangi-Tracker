from database import *
#Initialize Database
#Create the tables
create_tables()
#Test Groups
#Create the test group
group_id_1 = add_group("Group 1", 5000, "Weekly")
print(f"Group created with ID: {group_id_1}")
group_id_2 = add_group("Group 2", 10000.0, "Weekly")

#Test Members
#Add two members to Group 1
member1 = add_member(group_id_1, "Sukuna", "657498909")
member2 = add_member(group_id_1, "Stephanie", "564098454")
print(f"Member 1 created with ID: {member1}")
print(f"Member 2 created with ID: {member2}")
#Add to members to group 2
member3 = add_member(group_id_2, "Perevet", "69809089")
member4 = add_member(group_id_2, "Amiel", "67584958")
print(f"Member 3 created with ID: {member3}")
print(f"Member 4 created with ID: {member4}")

#Test cycles
#Create a cycle
cycle1 = add_cycle(member1, 1)
cycle2 = add_cycle(member3, 1)

#Test contributions
#Add one contribution for each member
add_contribution(member1, cycle1, 5000)
add_contribution(member2, cycle1, 5000)
add_contribution(member3, cycle2, 10000)
add_contribution(member4, cycle2, 10000)

#Test the poolsummary
expected, collected, remaining, progress = get_pool_summary(group_id_1, cycle1)
print("\n------- Group 1 Pool Summary -------")
print(f"Expected pool: {expected} FCFA")
print(f"Collected: {collected} FCFA")
print(f"Remaining: {remaining} FCFA")
print(f"Progress: {progress:.2f}%")

#Test the cycle status 
cycle_status = close_cycle(cycle1, group_id_1)
print(f"\nCycle status: {cycle_status}")

expected, collected, remaining, progress = get_pool_summary(group_id_2, cycle2)
print("\n------- Group 2 Pool Summary -------")
print(f"Expected pool: {expected} FCFA")
print(f"Collected: {collected} FCFA")
print(f"Remaining: {remaining} FCFA")
print(f"Progress: {progress:.2f}%")

cycle_status = close_cycle(cycle2, group_id_2)
print(f"\nCycle status: {cycle_status}")

#Test issuing a loan
loan_id = issue_loan(member1, 50000)
print(f"\nLoan created with ID: {loan_id}")
#Test partial loan repayment
status = repay_loan(loan_id, 20000)
print(f"Loan status after repayment: {status}")

print("\n------- MEMBER LOANS -------")
loans = get_loans_by_member(member1)
for loan in loans:
    print(loan)