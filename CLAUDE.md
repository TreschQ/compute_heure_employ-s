# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Streamlit application for analyzing employee timekeeping data from Excel files. The application calculates worked hours per employee and determines overtime status based on configurable role-specific thresholds.

## Key Commands

### Development Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run the Streamlit application locally
streamlit run app.py

# The app will be available at http://localhost:8501
```

### Testing and Validation
Since there are no formal test files, validate changes by:
1. Running the application locally with `streamlit run app.py`
2. Testing with sample Excel files (if available in data/ directory)
3. Verifying role assignments work correctly and persist in session state
4. Testing manual hour adjustments functionality
5. Checking print functionality generates valid HTML output

## Architecture

### File Structure
- `app.py` - Main Streamlit application with UI and business logic
- `utils.py` - Core data processing functions for Excel parsing and hour calculations
- `visualisation.py` - Chart generation functions using Altair
- `requirements.txt` - Python dependencies
- `data/` - Directory for sample or test data files

### Core Components

#### Data Processing Flow (`utils.py`)
1. `lire_onglet_excel()` - Reads Excel worksheet data
2. `traiter_fichier()` - Main processing function that:
   - Parses period information from Excel format (YYYY/MM/DD ~ MM/DD)
   - Detects day headers (numeric row indicating calendar days)
   - Extracts employee information blocks (ID, name, department)
   - Processes timestamp data and calculates worked hours
   - Handles multiple time entries per day and midnight crossovers
3. `determiner_statut()` - Determines overtime status based on thresholds

#### Visualization (`visualisation.py`)
- `creer_graphique_heures_par_employe()` - Role-specific bar charts with threshold lines
- `creer_graphiques_par_departement()` - Department analysis charts
- `creer_graphiques_tendance_journaliere()` - Daily trend analysis with heatmaps
- `afficher_statut_employes()` - Employee status dashboard with color-coded alerts

#### Main Application (`app.py`)
- Configurable role-specific thresholds (Cuisine: 42h/week, Salle: 39h/week)
- Employee role assignment system with session state persistence
- Month-based filtering with fallback to all data
- Manual hour adjustment system with session state tracking
- Print functionality with HTML report generation
- Interactive dashboards with multiple visualization tabs

### Key Features
- **Role-based overtime thresholds**: Different limits for Kitchen (Cuisine) and Dining Room (Salle) staff
- **Excel parsing**: Handles complex timekeeping Excel format with employee blocks and timestamp arrays
- **Data validation**: Manages odd timestamp counts and midnight boundary crossings
- **Interactive filtering**: Month selection with configurable alert margins
- **Manual adjustments**: Real-time hour editing with session persistence
- **Print reports**: HTML-based printable employee status reports
- **Multi-format visualization**: Bar charts, trend lines, heatmaps, and status dashboards

### Expected Excel Format
The application expects Excel files with:
- Period header: YYYY/MM/DD ~ MM/DD format
- Numeric day headers (1, 2, 3... representing calendar days)
- Employee information blocks with "Non:", "Nom:", "Département:" labels
- Timestamp data in HH:MM format, potentially multiple entries per cell separated by line breaks

### Data Processing Notes
- Hours are calculated by pairing timestamps (entry-exit)
- Odd timestamp counts are handled by dropping the last entry
- Midnight crossovers are automatically detected and handled
- Results include employee ID, name, department, date, and calculated hours

## Important Implementation Details

### Session State Management
The application uses Streamlit's session state to persist:
- `st.session_state.employee_roles`: Role assignments (Cuisine/Salle) per employee ID
- `st.session_state.manual_adjustments`: Manual hour corrections keyed by "emp_id|date_str"

### Print Functionality (`app.py:302-424`)
- Generates HTML reports with inline CSS for printing
- Uses JavaScript to trigger browser print dialog
- Provides downloadable HTML file as alternative
- Self-contained styling optimized for print media

### Role-Based Thresholds
- Monthly thresholds calculated as weekly_hours * 4.33
- Individual employee thresholds determined by assigned role
- Fallback to average of both thresholds for unassigned employees

### Error Handling
- Excel parsing handles malformed timestamp data gracefully
- Missing or empty cells in timekeeping data are skipped
- Robust pattern matching for employee information blocks