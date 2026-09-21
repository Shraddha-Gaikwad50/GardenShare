# Domain model

GardenShare tracks people, seed packets, borrows, and garden plantings.

## Entities

### Member

A community gardener. Members register with a name and email. An inactive
member remains in the directory but cannot create borrow requests.

### Seed

A catalog variety (for example Tomato / Cherry). Quantity is on-hand stock.
`reserved_quantity` holds packets for pending borrow requests.
`minimum_quantity` is the restock threshold used by inventory checks.

### BorrowRequest

A member asking to take packets of one seed. Lifecycle:

`pending` → `approved` or `rejected` → `returned` (from approved only)

Pending requests reserve inventory. Approval decreases on-hand quantity.
Rejection releases the reservation and does not change on-hand quantity.
Return restores inventory for an approved request.

### GardenPlot

A bed or container assigned to a member, with a location and size.

### PlantingPlan

A scheduled sowing of a seed in a plot, with an expected harvest date
derived from crop duration rules (tomato 80 days, carrot 70, basil 45,
lettuce 40).

## Relationships

```
Member
  ↓
BorrowRequest
  ↓
Seed

Member
  ↓
GardenPlot
  ↓
PlantingPlan
  ↓
Seed
```

- One member has many borrow requests and many garden plots.
- One seed appears in many borrow requests and many planting plans.
- One garden plot has many planting plans.
- A planting plan always points at exactly one plot and one seed.

## Inventory vs catalog vs gardens

These associations are easy to mix up:

- **Catalog** answers "do we have a cherry tomato variety?"
- **Inventory** answers "how many packets are on the shelf?"
- **Borrowing** answers "who is holding packets, and when are they due?"
- **Gardens** answer "when will this plot be planted and harvested?"

A planting plan does not automatically decrease inventory. Taking packets
out of the library is always a borrow (or a coordinator inventory decrease).
