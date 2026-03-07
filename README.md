# Credit Approval System - Backend Assignment

A complete Django 4+ and Django Rest Framework (DRF) backend for a Credit Approval System. Fully dockerized and integrated with PostgreSQL, Redis, and Celery for background data ingestion.

## Features

- **Automated Data Ingestion**: Uses a Celery background worker to asynchronously ingest seed data from `customer_data.xlsx` and `loan_data.xlsx` upon startup.
- **Credit Score Calculation**: Algorithm evaluates multiple factors (past loans, current debt, payment history) to assign a dynamic credit score (0-100).
- **Automated Credit Engine**: Approves or denies loans based on predefined credit score slabs and intelligently corrects interest rates if they fall below the minimum allowed for that slab.
- **Fully Dockerized**: Runs the entire stack (Django API, Postgres DB, Redis Cache, Celery Worker) using a single `docker-compose` command.

---

## Setup & Initialization

### Prerequisites
Make sure you have **Docker** and **Docker Compose** (Docker Desktop) installed and running on your machine.

### Running the Application

1. Clone this repository.
2. Open a terminal in the project directory (where `docker-compose.yml` is located).
3. Run the following command:

```bash
docker-compose up --build
```

### What happens in the background?
1. Four containers are spun up (`db`, `redis`, `web`, `celery`).
2. The web entrypoint waits for PostgreSQL to be ready, then runs Django database migrations.
3. Automatically triggers an asynchronous Celery task to read the `.xlsx` files from the `files/` directory and populate the database.
4. The API becomes available at `http://localhost:8000/api/`.

*(Note: Data ingestion takes a few moments on the first boot. You can check the Celery container logs to see when it finishes.)*

---

## API Endpoints

### 1. Register a Customer
**`POST /api/register/`**

Adds a new customer and calculates their `approved_limit` based on their salary (`36 * monthly_salary`, rounded to the nearest lakh).

**Request Body:**
```json
{
    "first_name": "John",
    "last_name": "Doe",
    "age": 30,
    "monthly_income": 50000,
    "phone_number": 9876543210
}
```

### 2. Check Loan Eligibility
**`POST /api/check-eligibility/`**

Calculates the customer's credit score using historical test data and determines if a loan is approved, what the corrected interest rate is, and the calculated monthly EMI (using the compound interest EMI formula).

**Request Body:**
```json
{
    "customer_id": 1,
    "loan_amount": 500000,
    "interest_rate": 10,
    "tenure": 24
}
```

### 3. Create a Loan
**`POST /api/create-loan/`**

Processes a new loan request exactly like `/check-eligibility/`, but if approved, it saves the loan into the database and updates the customer's active debt.

**Request Body:**
```json
{
    "customer_id": 1,
    "loan_amount": 500000,
    "interest_rate": 10,
    "tenure": 24
}
```

### 4. View Specific Loan
**`GET /api/view-loan/<loan_id>/`**

Returns detailed information about a specific loan and the associated customer details.

**Example Request:**
```bash
curl http://localhost:8000/api/view-loan/7798/
```

### 5. View Customer's Loans
**`GET /api/view-loans/<customer_id>/`**

Returns a list of all current loans active for a specific customer, including the exact number of repayments remaining.

**Example Request:**
```bash
curl http://localhost:8000/api/view-loans/1/
```

---

## Tech Stack
- **Framework**: Django 4.x + Django Rest Framework
- **Database**: PostgreSQL
- **Background Tasks**: Celery + Redis
- **Containerization**: Docker + Docker Compose
