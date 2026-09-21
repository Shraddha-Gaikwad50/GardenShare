# Known demo bugs

GardenShare ships with **exactly three** intentionally seeded business-logic
defects. They are realistic mistakes, not syntax errors. The application
still starts, the happy paths work, and `pytest` (which ignores this folder's
sibling `tests/demo_bugs/`) should pass.

These notes exist so maintainers can confirm the defects on demand:

```
pytest tests/demo_bugs/
```

Do not "fix" these defects unless you are intentionally changing the demo.

---

## Bug 1 — Inventory restored incorrectly on empty-shelf return

**Affected modules**

- `app/seeds/inventory.py` — `restore_borrowed_quantity()`
- `app/borrowing/service.py` — `return_seed()` (calls the restock helper)

**Expected behavior**

Returning an approved borrow must increase on-hand inventory by the borrowed
quantity. Example: borrow 5 packets, return 5 packets, inventory increases
by 5.

**Actual behavior**

When the shelf is empty (`seed.quantity == 0`) at return time, restock uses
`max(borrowed_quantity, seed.minimum_quantity)` instead of the borrowed
quantity. If the member borrowed every remaining packet and that amount is
below the catalog minimum, inventory jumps to the minimum rather than to
the amount actually returned.

**Reproduction**

1. Create a seed with `quantity=5` and `minimum_quantity=8`.
2. An active member borrows 5 packets; approve the request (quantity becomes 0).
3. Return the request.
4. Observed quantity is `8`. Expected quantity is `5`.

**Why this is realistic**

Empty-bin handling is often special-cased. A developer can confuse "do not
leave the shelf below the minimum after a restock" with "put back what the
member returned." The happy path (returns while other packets remain) still
works, so the defect hides until a borrow depletes the variety.

**Diagnostic test**

`tests/demo_bugs/test_inventory_return_bug.py`

---

## Bug 2 — Overdue detection ignores the first 24 hours past due

**Affected modules**

- `app/utils/dates.py` — `is_overdue()`
- `app/borrowing/service.py` — `get_overdue_requests()` (via `is_request_overdue` in `app/borrowing/policies.py`)

**Expected behavior**

A borrow request is overdue as soon as the current timestamp is after
`due_date`. A request due three hours ago is overdue.

**Actual behavior**

`is_overdue()` uses `(as_of - due_at).days > 0`. `timedelta.days` is the
whole-day component, so a request that became due 3 hours ago still has
`days == 0` and is treated as on time. It only becomes overdue after a full
additional 24 hours.

**Reproduction**

1. Approve a borrow request.
2. Set `due_date` to three hours before `utc_now()`.
3. Call `get_overdue_requests()` or `is_overdue(due_date)`.
4. The request is missing from the overdue list.

A request whose due date is three *days* ago is still reported overdue, which
is why ordinary tests pass.

**Why this is realistic**

Python's `timedelta.days` is a common source of off-by-one time bugs.
Comparing "number of days" looks like a correct overdue check and fails
only on the same-day / sub-24-hour boundary.

**Diagnostic test**

`tests/demo_bugs/test_overdue_boundary_bug.py`

---

## Bug 3 — Low-inventory alert skips the minimum-quantity boundary

**Affected modules**

- `app/seeds/inventory.py` — `check_inventory_threshold()`
- `app/notifications/reminders.py` — `build_low_inventory_alert()` (uses the threshold helper)

**Expected behavior**

A seed is low stock when available quantity is **at or below**
`minimum_quantity`. Coordinators should restock when the bin hits the
configured minimum, not only after it has already gone under.

**Actual behavior**

The threshold uses a strict less-than comparison:

`get_available_quantity(seed) < seed.minimum_quantity`

When available quantity equals the minimum (for example 4 on hand, minimum 4),
no low-stock flag is set and `build_low_inventory_alert()` returns `None`.
Alerts still fire when quantity is strictly below the minimum.

**Reproduction**

1. Create a seed with `quantity=4` and `minimum_quantity=4`.
2. Call `check_inventory_threshold(seed)` or `build_low_inventory_alert(seed)`.
3. Result is "not low" / `None`. Expected: low stock, alert built with
   "Lettuce seeds are running low." (or the variety name in use).

**Why this is realistic**

Off-by-one inequalities (`<` vs `<=`) are typical in threshold checks,
especially when a comment says "below the minimum" while the product rule
is "at or below."

**Diagnostic test**

`tests/demo_bugs/test_low_inventory_alert_bug.py`
