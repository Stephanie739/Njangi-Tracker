from database import(
    create_tables,
    add_group,
    add_member,
    add_cycle,
    add_contribution
)
create_tables()
print("Database tables are ready!")

group_id = add_group("Njangi Group 1", 10000.0, "Monthly")
print(f"Group created with ID: {group_id}")

member_id = add_member(group_id, "Ryo Sukuna", "123-456-7890")
print(f"Member created with ID: {member_id}")

cycle_id = add_cycle(member_id, 1)
print(f"Cycle created with ID: {cycle_id}")

contribution_id = add_contribution(member_id, cycle_id, 10000.0, "PAID")
print(f"Contribution created with ID: {contribution_id}")

print("All test data was added successfully!")