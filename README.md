# Evidence-Based Decision Support System (DSS)

An AI/Algorithm-assisted DSS that focuses on transparent decision making.

## Principles
1.  **Transparency**: No black boxes. Explanable SAW algorithm.
2.  **Quality Gate**: No auto-correction. Warn on bad data.
3.  **Cooperative DSS**: Humans make final decisions (Edit/Override/Approve).

## Setup
1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Run the application:
    ```bash
    streamlit run app/main.py
    ```

## Structure
- `core/`: Logic layer (Project engines)
- `data/`: Data models and persistence
- `app/`: UI layer (Streamlit)
- `configs/`: YAML configurations
