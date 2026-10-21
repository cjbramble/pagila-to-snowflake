# Ground truth for the rule-reviewer blind test (fixed before the run)

Decisions the naive wording leaves open, and how the project settled each one.

| # | Gap | Settled as | Real-data impact (measured in Phases 1, 6, and 7A) |
|---|---|---|---|
| G1 | Partial days late: round up or down? | Up (human) | 27,738 of 27,750 late rentals are late by a partial day |
| G2 | Replacement cost replaces the daily fee, or adds to it? | Replaces (human) | 194 rentals more than 2x overdue |
| G3 | Never-returned rentals: fee or not? | Flag, no fee (human) | 241 rentals |
| G4 | Which store gets a payment: inventory, staff, or customer's? | Inventory's store (human) | All 51,061 payments; 499/500 managers work at another store (SRC-004) |
| G5 | Returned exactly at the due instant: on time or late? | On time (inclusive) | 2 rentals |
| G6 | Exactly 2x overdue: daily fee or replacement? | Daily (strict >) | Boundary only |
| G7 | Which time zone decides the month? | UTC | Offsets differ per value |
| G8 | Is "2x overdue" measured on exact time or whole days? | Exact time after due_at | Boundary only |
| G9 | Zero-amount payments: count them? | Yes, counted | 24 payments (SRC-002) |
| G10 | Customers with no payments: included with 0? | Yes, 0.00 | 2 customers |
| G11 | Payments dated before their rental: valid? | Counted normally | 14,665 payments (SRC-001) |
| G12 | Several payments on one rental: avoid fan-out in joins | Aggregate separately | At least 1 rental |
| G13 | Due date: exact timestamp + N x 24h, or calendar-date boundary? | Exact timestamp | All rentals |

Scoring:
- **Recall:** ground-truth gaps it raises as open questions, out of 13.
- **Precision:** findings that are real, relevant gaps, as a share of all its findings.
- **Evidence:** whether its counts match the measured impact above.
