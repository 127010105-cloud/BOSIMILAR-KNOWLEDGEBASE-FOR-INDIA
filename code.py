import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

# ==========================================
# 1. DATABASE INITIALIZATION & SCHEMA SETUP
# ==========================================
def init_db():
    conn = sqlite3.connect("biosimilar_kb.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS molecules (
        molecule_id INTEGER PRIMARY KEY AUTOINCREMENT,
        generic_name TEXT UNIQUE NOT NULL,
        drug_class TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS manufacturers (
        manufacturer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        country TEXT DEFAULT 'India'
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS biosimilars (
        biosimilar_id INTEGER PRIMARY KEY AUTOINCREMENT,
        molecule_id INTEGER,
        manufacturer_id INTEGER,
        brand_name TEXT NOT NULL,
        reference_product TEXT NOT NULL,
        approval_year INTEGER NOT NULL,
        indications TEXT NOT NULL,
        cdsco_link TEXT,
        FOREIGN KEY (molecule_id) REFERENCES molecules(molecule_id),
        FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(manufacturer_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evidence (
        evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
        biosimilar_id INTEGER,
        analytical_evidence TEXT,
        non_clinical_evidence TEXT,
        pk_pd_evidence TEXT,
        phase_3_evidence TEXT,
        clinical_trials_waived TEXT CHECK(clinical_trials_waived IN ('Yes', 'No')),
        waiver_basis TEXT,
        FOREIGN KEY (biosimilar_id) REFERENCES biosimilars(biosimilar_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS regulatory_comparison (
        comparison_id INTEGER PRIMARY KEY AUTOINCREMENT,
        molecule_id INTEGER,
        cdsco_status TEXT NOT NULL,
        ema_status TEXT NOT NULL,
        usfda_status TEXT NOT NULL,
        fda_purple_book_link TEXT,
        FOREIGN KEY (molecule_id) REFERENCES molecules(molecule_id)
    );
    """)

    # Seed Sample Data if database is empty
    cursor.execute("SELECT COUNT(*) FROM molecules")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO molecules (generic_name, drug_class) VALUES ('Adalimumab', 'Monoclonal Antibody')")
        cursor.execute("INSERT INTO molecules (generic_name, drug_class) VALUES ('Trastuzumab', 'Monoclonal Antibody')")

        cursor.execute("INSERT INTO manufacturers (company_name, country) VALUES ('Zydus Cadila', 'India')")
        cursor.execute("INSERT INTO manufacturers (company_name, country) VALUES ('Biocon', 'India')")

        # Adalimumab sample record
        cursor.execute("""
        INSERT INTO biosimilars (molecule_id, manufacturer_id, brand_name, reference_product, approval_year, indications, cdsco_link)
        VALUES (1, 1, 'Exemptia', 'Humira (AbbVie)', 2014, 'Rheumatoid Arthritis, Psoriatic Arthritis, Ankylosing Spondylitis', 'https://cdsco.gov.in')
        """)
        cursor.execute("""
        INSERT INTO evidence (biosimilar_id, analytical_evidence, non_clinical_evidence, pk_pd_evidence, phase_3_evidence, clinical_trials_waived, waiver_basis)
        VALUES (1, 'Physicochemical & structural comparability validated', 'In vitro cell-based bioassays completed', 'PK bioequivalence demonstrated in healthy subjects', 'Confirmatory Phase 3 trial in RA patients', 'No', 'N/A')
        """)
        cursor.execute("""
        INSERT INTO regulatory_comparison (molecule_id, cdsco_status, ema_status, usfda_status, fda_purple_book_link)
        VALUES (1, 'Approved (2014)', 'Approved (2017)', 'Approved (2016)', 'https://purplebooksearch.fda.gov')
        """)

        # Trastuzumab sample record
        cursor.execute("""
        INSERT INTO biosimilars (molecule_id, manufacturer_id, brand_name, reference_product, approval_year, indications, cdsco_link)
        VALUES (2, 2, 'CANMAb', 'Herceptin (Roche)', 2013, 'HER2-Positive Metastatic Breast Cancer', 'https://cdsco.gov.in')
        """)
        cursor.execute("""
        INSERT INTO evidence (biosimilar_id, analytical_evidence, non_clinical_evidence, pk_pd_evidence, phase_3_evidence, clinical_trials_waived, waiver_basis)
        VALUES (2, 'High-resolution mass spectrometry & SPR spectroscopy', 'In vivo xenograft models executed', 'Comparative PK/PD study completed', 'Phase 3 trial in breast cancer patients', 'No', 'N/A')
        """)
        cursor.execute("""
        INSERT INTO regulatory_comparison (molecule_id, cdsco_status, ema_status, usfda_status, fda_purple_book_link)
        VALUES (2, 'Approved (2013)', 'Approved (2017)', 'Approved (2017)', 'https://purplebooksearch.fda.gov')
        """)

    conn.commit()
    conn.close()

# Helper function to sanitize the waived string to guarantee 'Yes' or 'No'
def clean_waived_status(val):
    val_str = str(val).strip().capitalize()
    if val_str in ['Yes', 'Y', 'True', '1']:
        return 'Yes'
    return 'No'

# Helper function to insert a single record into the DB
def insert_biosimilar_record(generic_name, drug_class, brand_name, reference_product, company_name, approval_year, indications, cdsco_link, analytical, non_clinical, pk_pd, phase_3, waived, waiver_basis, ema_status, usfda_status):
    conn = sqlite3.connect("biosimilar_kb.db")
    cursor = conn.cursor()

    # Normalize 'waived' column value to prevent CHECK constraint failures
    clean_waived = clean_waived_status(waived)

    cursor.execute("INSERT OR IGNORE INTO molecules (generic_name, drug_class) VALUES (?, ?)", (generic_name, drug_class))
    cursor.execute("SELECT molecule_id FROM molecules WHERE generic_name = ?", (generic_name,))
    molecule_id = cursor.fetchone()[0]

    cursor.execute("INSERT OR IGNORE INTO manufacturers (company_name) VALUES (?)", (company_name,))
    cursor.execute("SELECT manufacturer_id FROM manufacturers WHERE company_name = ?", (company_name,))
    manufacturer_id = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO biosimilars (molecule_id, manufacturer_id, brand_name, reference_product, approval_year, indications, cdsco_link)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (molecule_id, manufacturer_id, brand_name, reference_product, approval_year, indications, cdsco_link))
    biosimilar_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO evidence (biosimilar_id, analytical_evidence, non_clinical_evidence, pk_pd_evidence, phase_3_evidence, clinical_trials_waived, waiver_basis)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (biosimilar_id, analytical, non_clinical, pk_pd, phase_3, clean_waived, waiver_basis))

    cursor.execute("""
        INSERT INTO regulatory_comparison (molecule_id, cdsco_status, ema_status, usfda_status, fda_purple_book_link)
        VALUES (?, ?, ?, ?, 'https://purplebooksearch.fda.gov')
    """, (molecule_id, f"Approved ({approval_year})", ema_status, usfda_status))

    conn.commit()
    conn.close()

# ==========================================
# 2. STREAMLIT USER INTERFACE & NAVIGATION
# ==========================================
st.set_page_config(page_title="Indian Biosimilar Knowledgebase", layout="wide", page_icon="🧬")

# Initialize Database
init_db()

st.title("🧬 Biosimilar Knowledgebase for India")
st.markdown("---")

# Navigation Sidebar
menu = ["📊 Dashboard & Timeline", "🔍 Browse & Query Database", "⚖️ Regulatory Comparison (EMA / FDA)", "➕ Add New Entry", "📁 Upload CSV Data"]
choice = st.sidebar.selectbox("Navigation", menu)

# --- TAB 1: DASHBOARD & TIMELINE ---
if choice == "📊 Dashboard & Timeline":
    st.header("Approval Timeline & Overview")
    
    conn = sqlite3.connect("biosimilar_kb.db")
    df = pd.read_sql_query("""
        SELECT b.brand_name, m.generic_name, mf.company_name, b.approval_year, b.reference_product
        FROM biosimilars b
        JOIN molecules m ON b.molecule_id = m.molecule_id
        JOIN manufacturers mf ON b.manufacturer_id = mf.manufacturer_id
    """, conn)
    conn.close()

    if not df.empty:
        col1, col2 = st.columns(2)
        col1.metric("Total Approved Biosimilars", len(df))
        col2.metric("Molecules Tracked", df['generic_name'].nunique())

        st.subheader("Approval Timeline Visualizer")
        fig =This error happens because the `clinical_trials_waived` column in the SQLite database has a strict SQL CHECK constraint that **only** allows exact strings: `'Yes'` or `'No'`. 

If your CSV has values like `'yes'`, `'no'`, `'TRUE'`, `'FALSE'`, or blank cells, SQLite rejects the entry.

---

### Fixed CSV Code Section

Here is the updated **"📁 Upload CSV Data"** section of your Streamlit code. It automatically cleans and converts `Yes`/`No` values (including `true`, `false`, `1`, `0`, and lowercase text) before saving them to the database so the constraint never fails again.

Replace your **Tab 5 (`choice == "📁 Upload CSV Data"`)** code with this:

```python
# --- TAB 5: UPLOAD CSV DIRECTLY TO DATABASE ---
elif choice == "📁 Upload CSV Data":
    st.header("Upload CSV File to Database")
    st.write("Upload a CSV file to bulk-import biosimilar entries directly into the database.")

    with st.expander("ℹ️ Click to view required CSV Format & Columns"):
        st.write("Your CSV file should include the following column headers:")
        st.code("""generic_name,drug_class,brand_name,reference_product,company_name,approval_year,indications,cdsco_link,analytical_evidence,non_clinical_evidence,pk_pd_evidence,phase_3_evidence,clinical_trials_waived,waiver_basis,ema_status,usfda_status""")

    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            csv_df = pd.read_csv(uploaded_file)
            st.write("### Preview Uploaded Data:")
            st.dataframe(csv_df, use_container_width=True)

            if st.button("Import Data into Database"):
                records_inserted = 0
                for _, row in csv_df.iterrows():
                    # Sanitize 'clinical_trials_waived' to strictly match SQLite 'Yes' / 'No' constraint
                    raw_waived = str(row.get('clinical_trials_waived', 'No')).strip().capitalize()
                    if raw_waived in ['True', '1', 'Y']:
                        waived_val = 'Yes'
                    elif raw_waived in ['False', '0', 'N']:
                        waived_val = 'No'
                    elif raw_waived in ['Yes', 'No']:
                        waived_val = raw_waived
                    else:
                        waived_val = 'No'

                    insert_biosimilar_record(
                        generic_name=str(row.get('generic_name', 'Unknown')),
                        drug_class=str(row.get('drug_class', 'Monoclonal Antibody')),
                        brand_name=str(row.get('brand_name', 'Unknown')),
                        reference_product=str(row.get('reference_product', 'N/A')),
                        company_name=str(row.get('company_name', 'Unknown')),
                        approval_year=int(row.get('approval_year', 2024)),
                        indications=str(row.get('indications', 'N/A')),
                        cdsco_link=str(row.get('cdsco_link', '[https://cdsco.gov.in](https://cdsco.gov.in)')),
                        analytical=str(row.get('analytical_evidence', 'Submitted')),
                        non_clinical=str(row.get('non_clinical_evidence', 'Submitted')),
                        pk_pd=str(row.get('pk_pd_evidence', 'Submitted')),
                        phase_3=str(row.get('phase_3_evidence', 'Submitted')),
                        waived=waived_val,
                        waiver_basis=str(row.get('waiver_basis', 'N/A')),
                        ema_status=str(row.get('ema_status', 'Approved')),
                        usfda_status=str(row.get('usfda_status', 'Approved'))
                    )
                    records_inserted += 1

                st.success(f"Successfully imported {records_inserted} records into the database!")
        except Exception as e:
            st.error(f"Error processing CSV file: {e}")
