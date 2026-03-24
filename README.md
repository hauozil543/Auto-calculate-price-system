# Price Calculator System

A Streamlit-based web application designed to automate pricing calculations and manage workflows between Sales and Pricing teams. Built using Python, Pandas, and SQLite, featuring Role-Based Access Control (RBAC).

## Features

- **Multi-Role Dashboards**: Specific sidebar views and functional permissions for `Admin`, `Pricing`, and `Sales` teams.
- **Sales Pricing Tool**: Instant Guide Price calculator using dynamic Base Costs, GM Targets, and custom Price Gaps logic.
- **Pricing Management**: Dashboard for viewing manual quotation requests from the Sales team and supervising the raw database cache.
- **System Administration**: Interactive User Management forms (Create/Delete) and real-time Activity & System Access Logging trackings.
- **SQLite Database Cache**: Uses a persistent lightweight file-based SQL database built from external Excel data (`GuidePriceAIRaw.xlsx`), ensuring rapid calculations.

## Tech Stack

- **Frontend/Backend**: [Streamlit](https://streamlit.io/) (Python Web App Framework)
- **Data Manipulation**: Pandas, OpenPyXL
- **Database**: SQLite3 built-in module

## Project Structure

- `main.py` - Core application router & Streamlit entry point.
- `auth.py` - Session management, state trackers & user authentication controls.
- `database.py` - Database schema initiation, CRUD operations, and Excel to SQLite import handler.
- `ui_admin.py`, `ui_pricing.py`, `ui_sales.py` - Standalone interface scripts handling business logic for each specific role.

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/hauozil543/Auto-calculate-price-system.git
   cd Auto-calculate-price-system
   ```

2. **Install dependencies:**
   Make sure you have Python installed. You can install the required Python packages via pip:
   ```bash
   pip install streamlit pandas openpyxl
   ```

3. **Database Initialization:**
   Ensure `price_database.db` is present, or manually supply your `GuidePriceAIRaw.xlsx` table into the `data_raw/` directory and execute the database script to dynamically rebuild the local SQL cache:
   ```bash
   python database.py
   ```

4. **Run the Application:**
   Launch the interactive Streamlit server locally:
   ```bash
   streamlit run main.py
   ```

## Demo Accounts (For local development testing)
- **Admin Root**: `admin` / `admin123`
- **Pricing Manager**: `pricing_demo` / `123456`
- **Sales Representative**: `sales_demo` / `123456`
