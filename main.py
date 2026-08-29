from database import(
    create_tables,
    add_group,
    add_member,
    add_cycle,
    add_contribution,
    get_members_by_group,
    get_contributions,
    get_cycle_total,
    get_expected_pool,
    get_pool_summary
)
create_tables()
print("Database tables are ready!")

group_id = add_group("Njangi Group 1", 10000.0, "Monthly")
print(f"Group created with ID: {group_id}")

member_id = add_member(group_id, "Ryo Sukuna", "123-456-7890")
print(f"Member created with ID: {member_id}")
member_id = add_member(group_id, "Stephanie", "1326-465-9087")
print(f"Member created with ID: {member_id}")
member_id = add_member(group_id, "Perevet", "1326-465-9067")
print(f"Member created with ID: {member_id}")
member_id = add_member(group_id, "Amiel", "1324-465-0987")
print(f"Member created with ID: {member_id}")

members = get_members_by_group(group_id)
print("\nMembers in Group 1:")
for member in members:
    print(member)

group_id_2 = add_group("Njangi Group 2", 5000.0, "Weekly")
print(f"Group created with ID: {group_id_2}")
member_id = add_member(group_id_2, "John Doe", "987-654-3210")
print(f"Member created with ID: {member_id}")
member_id = add_member(group_id_2, "Jane Smith", "465-4879-0987")
print(f"Member created with ID: {member_id}")

#get all members belonging to this group
members = get_members_by_group(group_id_2)
print("\nMembers in Group 2:")
for member in members:
    print(member)

cycle_id = add_cycle(member_id, 1)
print(f"Cycle created with ID: {cycle_id}")

contribution_id1 = add_contribution(member_id, cycle_id, 0)
print(f"Pending contribution ID: {contribution_id1}")

contribution_id2 = add_contribution(member_id, cycle_id, 5000)
print(f"Partial contribution ID: {contribution_id2}")

contribution_id3 = add_contribution(member_id, cycle_id, 10000)
print(f"Paid contribution ID: {contribution_id3}")

contributions = get_contributions()
print("\nAll contributions:")
for contribution in contributions:
    print(contribution)
total = get_cycle_total(cycle_id)
print("\nTotal amount collected in the cycle: ")
print(f"{total} FCFA")

#Test Njangi expected pool
expected_pool = get_expected_pool(group_id)
print("\n expected Njangi pool: ")
print(f"{expected_pool} FCFA")

#Test Njangi pool summary
expected, collected, remaining, progress = get_pool_summary(group_id, cycle_id)
print("\n----------Njangi Pool Summary----------")
print(f"Expected pool: {expected} FCFA")
print(f"Collected: {collected} FCFA")
print(f"Remaining: {remaining} FCFA")
print(f"Progress: {progress}")

contribution_id1 = add_contribution(member_id, cycle_id, 0)

print(f"Pending contribution ID: {contribution_id1}")

contribution_id2 = add_contribution(member_id, cycle_id, 5000)

print(f"Partial contribution ID: {contribution_id2}")

contribution_id3 = add_contribution(member_id, cycle_id, 10000)

print(f"Paid contribution ID: {contribution_id3}")