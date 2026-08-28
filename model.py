#create a NjangiGroup class
class NjangiGroup:
#put the constructor to run as the class is created
#__init__ is a constructor
#self is use to specify a particular object
    def__init__(self, group_id, name, contribution_amount, frequency):
        self.group_id = group_id
        self.name = name
        self.contribution_amount = contribution_amount
        self.frequency = frequency
#create a class: Member
class Member:
#use the constructor __init__
#use self to specify a particular ibject
    def__init__(self, member_id, group_id, name, phone):
        self.member_id = member.id
        self.group_id = group.id
        self.name = name
        self.phone = phone
#create a class: Cycle
#Cycle is the coninous follow of the njangi process
class Cycle:
#__init__ use as a constructor
#use self to specify a particular object
    def__init__(self,cycle_id, member_id, cycle_number, status):
        self.cycle_id = cycle_id
        self.member_id = member_id
        self.cycle_number = cycle_number
        self.status = status
class Contribution:
#create a class: Contribution
#this class is to know the amount of money is processing in the njangi
    def__init__(self, contribution_id, member_id, cycle_id, amount, payment_status):
#use __init__ as a constructor
#use self as a specifier of particularr objects
        self.contribution_id = contribution_id
        self.member_id = member_id
        self.cycle_id = cycle_id
        self.amount = amount
        self.payment_status = payment_status