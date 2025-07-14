import streamlit as st
import pandas as pd
import os

st.set_page_config(layout="wide")


def visualize_merged_csv(csv_path):
    """Visualize merged wildlife camera trap data from a CSV file using Streamlit."""
    merged_df = pd.read_csv(csv_path)
    # Center the title using markdown and HTML
    st.markdown(
        '<h1 style="text-align: center;">Wildlife Camera Trap Insights</h1>',
        unsafe_allow_html=True,
    )
    num_cols = 3  # Number of grid columns
    rows = merged_df.to_dict(orient="records")
    for i in range(0, len(rows), num_cols):
        cols = st.columns(num_cols)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(rows):
                break
            row = rows[idx]
            with col:
                img_path = row["sample_image"]
                if img_path and os.path.exists(img_path):
                    st.image(img_path, use_container_width=True)
                else:
                    st.write("No image")
                # Compact metadata display
                st.markdown(f"{row['folder']}", unsafe_allow_html=True)
                st.markdown(
                    f"{row.get('date','')} {row.get('time','')}",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<b>SpeciesNet:</b> {row['species']} <b>({row['max_count']})</b> &nbsp; | &nbsp; <b>GPT:</b> {row['gpt_species']} <b>({row['gpt_count']})</b>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<b>GPT Summary:</b> {row['gpt_summary']}", unsafe_allow_html=True
                )
                # Individuals table if present
                individuals_col = "gpt_individuals"
                try:
                    individuals = eval(row[individuals_col])
                    if individuals:
                        df_individuals = pd.DataFrame(individuals)
                        st.dataframe(df_individuals)
                except Exception:
                    pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Visualize merged wildlife camera trap data CSV with Streamlit."
    )
    parser.add_argument("csv_file", help="Path to merged CSV file")
    args = parser.parse_args()
    visualize_merged_csv(args.csv_file)
