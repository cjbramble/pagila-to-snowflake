# Business rules for the reporting marts (draft from the business analyst)

**Late returns and fees**
A rental is due back rental_duration days after it is rented (rental_duration is on the film).
A rental returned after its due date is late. Late rentals are charged $1.00 for every day
they are overdue. If a film is more than rental_duration * 2 overdue, charge the
replacement_cost.

**Monthly revenue by store**
Total payment amount for each store for each month.

**Customer lifetime value**
For each customer, the total of all their payments, plus how many payments and rentals they
have, and the dates of their first and last payment.
