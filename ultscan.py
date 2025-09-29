"""
Streamlit Application: UltScan Runner with CSV Preview
------------------------------------------------------

This Streamlit application provides a simple interface to run a CLI command 
(`python exec_ultscan.py`) with configurable parameters and securely supplied password. 
It streams the CLI output to the UI in real time, then automatically previews the latest 
CSV file generated in a specific directory and makes it available for download.

Features:
- Secure password input (not stored in code or logs).
- Real-time command output streaming in the UI.
- Automatic detection of the latest CSV file in the configured folder.
- CSV preview (first few rows) and download button.
- Toggleable logging for development vs production environments.

Global Variables:
- ENABLE_LOGGING: Switch logging on/off.
- CSV_OUTPUT_DIR: Folder where output CSV files are stored.
- CLI_BASE_COMMAND: The base CLI command to execute.
- CLI_DIR_CONFIG: Path to the CLI configuration directory.

Best Practices:
- Structured logging for debugging and monitoring.
- Clear function separation (CLI execution, CSV handling, UI).
- Defensive coding (error handling when reading CSVs).
"""
"""
Streamlit Application: UltScan Runner with CSV Management
---------------------------------------------------------

This app runs the UltScan CLI command with a password and displays its live output.  
It also provides summaries of the configured directory, previews the latest CSV, and 
lists all generated CSVs in the output directory.
"""

import subprocess
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

# ==========================================================
# Global Configuration
# ==========================================================
ENABLE_LOGGING = True  # Set to False to silence logs in production
CSV_OUTPUT_DIR = Path("./outputs/posts")
CSV_OUTPUT_DIR.mkdir(exist_ok=True)

# CLI_BASE_COMMAND = "python exec_ultscan.py"
CLI_BASE_COMMAND = "/home/adminuser/venv/bin/python exec_ultscan.py"
CLI_DIR_CONFIG = Path("./cfw-configs")

# Configure logging
if ENABLE_LOGGING:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )
else:
    logging.basicConfig(level=logging.CRITICAL)

logger = logging.getLogger(__name__)


# ==========================================================
# Utility Functions
# ==========================================================
def run_cli_command(password: str):
    """
    Execute the CLI command with a given password, streaming stdout line by line.
    Stops if 'Unauthorized access' is detected.
    """
    full_cmd = (
        f'{CLI_BASE_COMMAND} --dir-config="{CLI_DIR_CONFIG}" '
        f'--password="{password}"'
    )
    logger.info(f"Running command: {full_cmd}")

    process = subprocess.Popen(
        full_cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    if not process.stdout:
        logger.error("No stdout captured from process.")
        return

    for line in process.stdout:
        line = line.strip()
        yield line
        if "Unauthorized access" in line:
            logger.warning("Unauthorized access detected — stopping process.")
            process.kill()
            break

    process.wait()


def get_latest_csv_file(folder: Path) -> Path | None:
    """
    Find the most recent CSV file in the given folder.
    """
    csv_files = list(folder.glob("*.csv"))
    if not csv_files:
        return None
    return max(csv_files, key=lambda f: f.stat().st_mtime)


def load_config_summary(config_dir: Path) -> dict:
    """
    Load summary statistics from CSV files inside the config directory.
    """
    summary = {
        "sources_count": 0,
        "batch_ids": None,
        "posts_count": 0,
        "images_count": 0,
    }

    try:
        post_models_path = config_dir / "post_models.csv"
        if post_models_path.exists():
            df_models = pd.read_csv(post_models_path)
            summary["sources_count"] = len(df_models)
            if "batch_id" in df_models.columns:
                summary["batch_ids"] = df_models[["batch_id"]]
    except Exception as e:
        logger.warning(f"Failed to load post_models.csv: {e}")

    try:
        posts_path = config_dir / "processed_posts_urls.csv"
        if posts_path.exists():
            df_posts = pd.read_csv(posts_path)
            summary["posts_count"] = len(df_posts)
    except Exception as e:
        logger.warning(f"Failed to load processed_posts_urls.csv: {e}")

    try:
        images_path = config_dir / "processed_images_urls.csv"
        if images_path.exists():
            df_images = pd.read_csv(images_path)
            summary["images_count"] = len(df_images)
    except Exception as e:
        logger.warning(f"Failed to load processed_images_urls.csv: {e}")

    return summary


def list_csv_files(folder: Path) -> pd.DataFrame:
    """
    List all CSV files in the output directory with metadata.

    Returns:
        pd.DataFrame with columns: filename, created_at, size_kb, rows
    """
    data = []
    for f in folder.glob("*.csv"):
        try:
            stats = f.stat()
            created_at = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            size_kb = round(stats.st_size / 1024, 2)

            # count rows efficiently
            try:
                row_count = sum(1 for _ in open(f, "r", encoding="utf-8")) - 1
                if row_count < 0:
                    row_count = 0
            except Exception:
                row_count = "?"

            data.append({
                "filename": f.name,
                "created_at": created_at,
                "size_kb": size_kb,
                "rows": row_count
            })
        except Exception as e:
            logger.warning(f"Failed to process file {f}: {e}")

    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by="created_at", ascending=False).reset_index(drop=True)
    return df


# ==========================================================
# Page: Home
# ==========================================================
def home_page():
    st.title("UltScan Runner")
    st.write(
        "Run the UltScan CLI with secure parameters, view live output, "
        "and explore the results in CSV previews."
    )

    # Config summary toggle
    if st.checkbox("Show Config Directory Summary"):
        st.subheader("📊 Config Directory Summary")
        summary = load_config_summary(CLI_DIR_CONFIG)

        col1, col2, col3 = st.columns(3)
        col1.metric("Sources to process", summary["sources_count"])
        col2.metric("Posts processed", summary["posts_count"])
        col3.metric("Images processed", summary["images_count"])

        if summary["batch_ids"] is not None:
            st.write("Batch IDs from `post_models.csv`:")
            st.dataframe(summary["batch_ids"])

    # Sidebar
    st.sidebar.header("Configuration")
    st.sidebar.write(f"**Dir Config:** `{CLI_DIR_CONFIG}`")

    disabled = st.session_state.get("running", False)
    password = st.sidebar.text_input("Password", type="password", disabled=disabled)

    run_disabled = st.session_state.get("running", False)
    if st.sidebar.button("Run Command", disabled=run_disabled):
        if not password:
            st.error("Password is required to run the command.")
            return

        st.session_state.running = True

        st.subheader("⚙️ Command Output")
        output_placeholder = st.empty()
        output_lines = []

        unauthorized = False
        for line in run_cli_command(password):
            output_lines.append(line)
            output_placeholder.text("\n".join(output_lines))
            if "Unauthorized access" in line:
                unauthorized = True
                st.error("❌ Unauthorized access — please check your password.")
                break

        if not unauthorized:
            st.success("Command execution completed ✅")

        st.session_state.running = False

        if not unauthorized:
            st.subheader("📄 Latest CSV Preview")
            latest_csv = get_latest_csv_file(CSV_OUTPUT_DIR)
            if latest_csv and latest_csv.exists():
                try:
                    df = pd.read_csv(latest_csv)
                    st.dataframe(df.head())

                    with open(latest_csv, "rb") as f:
                        st.download_button(
                            label="Download Latest CSV",
                            data=f,
                            file_name=latest_csv.name,
                            mime="text/csv"
                        )
                except Exception as e:
                    st.error(f"Failed to read CSV: {e}")
                    logger.exception("Error reading CSV")
            else:
                st.warning("No CSV files found in output directory.")

    st.markdown("---")
    st.markdown("<small>Developed by Idaraty for CFW</small>", unsafe_allow_html=True)


# ==========================================================
# Page: Latest CSV
# ==========================================================
def latest_csv_page():
    st.title("Latest CSV Preview")
    latest_csv = get_latest_csv_file(CSV_OUTPUT_DIR)

    if latest_csv and latest_csv.exists():
        try:
            st.success(f"Latest file: `{latest_csv.name}`")
            df = pd.read_csv(latest_csv)
            st.dataframe(df)

            with open(latest_csv, "rb") as f:
                st.download_button(
                    label="Download Latest CSV",
                    data=f,
                    file_name=latest_csv.name,
                    mime="text/csv"
                )
        except Exception as e:
            st.error(f"Failed to read CSV: {e}")
            logger.exception("Error reading CSV")
    else:
        st.warning("No CSV files found in output directory.")

    st.markdown("---")
    st.markdown("<small>Developed by Idaraty for CFW</small>", unsafe_allow_html=True)


# ==========================================================
# Page: List CSVs
# ==========================================================
def list_csvs_page():
    st.title("📂 All CSV Files in Output Directory")

    df = list_csv_files(CSV_OUTPUT_DIR)
    if df.empty:
        st.warning("No CSV files found in output directory.")
    else:
        st.dataframe(df)

    st.markdown("---")
    st.markdown("<small>Developed by Idaraty for CFW</small>", unsafe_allow_html=True)


# ==========================================================
# Entry Point
# ==========================================================
def main():
    if "running" not in st.session_state:
        st.session_state.running = False

    page = st.sidebar.radio("Navigation", ["Home", "Latest CSV", "List CSVs"])

    if page == "Home":
        home_page()
    elif page == "Latest CSV":
        latest_csv_page()
    elif page == "List CSVs":
        list_csvs_page()


if __name__ == "__main__":
    main()
