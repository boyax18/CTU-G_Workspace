# WF-07 - SSG Finance and Payments implementation record

Implemented 25 November 2026. This record documents the current Student Finance and Payments foundation. It does not claim that accounting administration, receipts, cashiers, expense records, or financial reporting are complete.

Parent: [Workflow catalogue](./CTU-G_Workspace_System_Workflow_Catalogue.md).

## Scope implemented

| Area | Implementation |
| --- | --- |
| Backend models | Added Student assessments and payment submissions. |
| Student summary | Returns the latest assessment total, verified paid amount, balance, and payment history. |
| Student payment submission | Allows a Student to submit a positive payment not greater than the current balance. |
| Pending verification | New payments default to `pending`. |
| Verified payments | Only `verified` payments reduce the Student balance. |
| Cashier verification | Payment status verification is restricted to Django Admin for the current implementation. |
| Dashboard integration | Added an effective-permission-gated **Payments & receipts** dashboard entry. |
| Frontend page | Shows three summary cards, a payment form, and payment history. |

## Data model

### `Assessment`

| Field | Rule |
| --- | --- |
| `student` | Foreign key to the Student account; related name is `assessments`. |
| `semester` | Maximum 40 characters. |
| `total` | Maximum 12 digits with 2 decimal places; defaults to `0.00`. |

`Assessment` enforces one record per Student and semester.

### `Payment`

| Field | Rule |
| --- | --- |
| `student` | Foreign key to the Student account; related name is `payments`. |
| `reference` | Unique, generated payment reference. |
| `amount` | Maximum 12 digits with 2 decimal places. |
| `status` | `pending` or `verified`; defaults to `pending`. |
| `created_at` | Automatically records submission time. |

Payment records are ordered newest first.

## Backend files

| File | Change |
| --- | --- |
| `backend/apps/finance/models.py` | Defines `Assessment` and `Payment`. |
| `backend/apps/finance/serializers.py` | Validates payment amount and exposes approved payment fields. |
| `backend/apps/finance/views.py` | Provides Student summary and payment submission APIs. |
| `backend/apps/finance/permissions.py` | Restricts access to eligible Students with Finance self-read grants. |
| `backend/apps/finance/urls.py` | Defines summary and payment routes. |
| `backend/apps/finance/admin.py` | Allows semester, office, or accounting staff to manage assessments and payment status. |
| `backend/apps/finance/migrations/0001_initial.py` | Creates the Finance tables and seeds Student self-read permission grants. |
| `backend/config/urls.py` | Mounts `/api/v1/finance/...`. |

## API routes

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/finance/summary/` | Authenticated Student with a Finance self-read grant | Return assessment total, verified paid amount, balance, and own payments. |
| POST | `/api/v1/finance/payments/` | Authenticated Student with a Finance self-read grant | Submit a pending payment. |

Payment submissions:

- Must use a positive amount.
- Cannot exceed the current balance.
- Automatically belong to the authenticated Student.
- Default to `pending`.
- Cannot set `status` or `reference` from the request.

## Frontend files

| File | Change |
| --- | --- |
| `frontend/src/features/finance/api.ts` | Loads and submits Finance information through the shared API client. |
| `frontend/src/features/finance/FinancePage.tsx` | Displays summary cards, payment form, and payment history. |
| `frontend/src/features/dashboard/navigation.ts` | Makes **Payments & receipts** a working permission-gated shell. |
| `frontend/src/features/dashboard/SessionDashboardPage.tsx` | Mounts the Finance page. |
| `frontend/src/App.tsx` | Adds the `/finance` route. |

## Page behavior

The page shows:

- Total assessment
- Verified amount paid
- Remaining balance
- Payment submission form
- Payment history table

Payment history includes:

- Reference
- Amount
- Status
- Submission date

Pending payments use an amber status pill. Verified payments use a green status pill.

The page handles loading, submission, API errors, and an empty payment history.

## Permission behavior

The Student links require either:

- `finance.payments.self.read`
- `finance.receipts.self.read`

Frontend permission visibility is only a navigation hint. Django independently verifies the account, active Student role, service state, role grant, and effective permission for every protected request.

## Migration and run commands

```powershell
cd backend
python manage.py makemigrations finance
python manage.py migrate
python manage.py check
```

Frontend validation:

```powershell
cd frontend
npm run build
npm test
```

## Manual test

1. Open Django Admin.
2. Add or update an `Assessment` for the target approved Student.
3. Set a total larger than zero.
4. Sign in as that Student.
5. Open `/finance` or select **Payments & receipts**.
6. Confirm the total, paid amount, and balance are displayed.
7. Submit a valid positive payment below or equal to the balance.
8. Confirm the new row appears as `Pending verification`.
9. In Django Admin, change the payment status to `Verified`.
10. Reload `/finance`.
11. Confirm the verified payment reduces the balance.

## Current limitations

- The Cashier/Admin verification workflow has no dedicated protected API or frontend yet.
- Receipts are not yet generated or stored.
- The system does not expose a full accounting ledger or financial reports.
- Assessment and payment status changes remain Admin/Django staff operations until separate role-managed workflows are implemented.
- Email notifications, offline payments, and payment-provider integration are not implemented.
