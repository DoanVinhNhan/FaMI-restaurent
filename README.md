# FaMÌ POS - Restaurant Management System

A comprehensive Point of Sale (POS) and Restaurant Management backend built with Django & Django REST Framework.

## Features

- **Sales (POS)**: Table management, Ordering, Real-time status, Payment processing.
- **Menu Management**: Creating items, categories, and price history tracking.
- **Kitchen (KDS)**: Real-time Kitchen Display System for managing orders.
- **Inventory**: Ingredient tracking, Stock adjustments, and Stock Taking (Audits).
- **Reporting**: Sales, Inventory, and Waste analytics.
- **HR & Admin**: User role management (Manager, Cashier, Kitchen, Inventory) and System Settings.

## Tech Stack

- **Backend**: Python 3.12, Django 5.0
- **API**: Django REST Framework
- **Database**: SQLite (Development) / PostgreSQL (Production ready)
- **Frontend**: Django Templates + Bootstrap 5 + HTMX (for dynamic interactions)

## Getting Started

### Prerequisites
- Python 3.10+
- Git

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Doanvinhnhan24/restaurent_source.git
    cd fami_backend
    ```

2.  **Create and Activate Virtual Environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.a. **Configure Environment Variables**:
    Create a file named `.env` in the `fami_backend` folder (next to `manage.py`) and add the following content:
    ```env
    DEBUG=True
    SECRET_KEY=django-insecure-your-secret-key-here
    ALLOWED_HOSTS=127.0.0.1,localhost
    DATABASE_URL=sqlite:///db.sqlite3
    ```

4.  **Database Setup**:
    ```bash
    python manage.py migrate
    ```

5.  **Create Superuser (Admin)**:
    ```bash
    python manage.py createsuperuser
    ```

6.  **Run the Server**:
    ```bash
    python manage.py runserver
    ```
    Access the system at: `http://127.0.0.1:8000/`

## User Roles (Default Permissions)

- **Manager**: Full access to all modules.
- **Cashier**: Access to POS (Sales) and Payment only.
- **Kitchen**: Access to KDS Board only.
- **Inventory**: Access to Stock Management and Reports.

## Project Structure

- `core/`: Authentication, User Management, Settings.
- `sales/`: Tables, Orders, POS Views.
- `menu/`: Menu Items, Categories, Pricing.
- `inventory/`: Ingredients, Stock Tracking, Stock Takes.
- `kitchen/`: KDS Views and APIs.
- `reporting/`: Analytics and Charts.
