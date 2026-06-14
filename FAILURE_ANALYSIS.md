# Failure Analysis: Census Analytics Chatbot

This document details 3 inputs/scenarios where the system might break or degrade, explaining the root cause and proposing technical fixes.

---

## 1. Scenario: Ambiguous District Names across States
- **Example Input**: *"What is the sex ratio in Bijapur?"*
- **Description of Degradation**: Bijapur is a major district in Karnataka (present in our data, code 557) but is also a district in Chhattisgarh (not in our current data). If more states are added, name collisions occur.
- **Root Cause**: The agent might run a search or SQL query like `df[df['district_name'] == 'Bijapur']` and return multiple rows, or arbitrary pick one, or throw an indexing error if it assumes a single value is returned (e.g., `.values[0]`).
- **Proposed Fix**: 
  - Update the agent's system instructions: *"If a district name is found in multiple states, always check `state` and ask the user for clarification, or present the data for both states clearly distinguished."*
  - Add a safety check in any generated code to handle cases where multiple matching rows are returned.

---

## 2. Scenario: Multi-page Table Splitting
- **Example Input**: *"Show me the work participation rate for all districts in Odisha."* (If querying raw text pages instead of the pre-parsed CSV).
- **Description of Degradation**: When reading a specific page, the agent only sees a subset of the districts. For example, Statement 22 (WPR) spans two pages in the report due to length.
- **Root Cause**: The page segmentation (`<!-- page X -->` split) cuts the markdown tables at arbitrary page boundaries. If the agent retrieves Page 58, it sees districts 370-385; if it retrieves Page 59, it sees districts 386-399. The agent fails to compile the complete list because it only reads one page at a time.
- **Proposed Fix**:
  - We solved this for the code executor by pre-parsing and merging tables into a single global CSV (`census_master.csv`) during offline preprocessing.
  - For raw text searches, we can modify `read_page` to accept a `range` of pages (e.g., `read_pages(state, start_page, end_page)`) or automatically include the subsequent page if a markdown table is truncated at the end of the text.

---

## 3. Scenario: Complex Multi-step Plotting and Outlier Calculations
- **Example Input**: *"Compare population growth vs literacy rate across all districts in MP and Karnataka, generate a scatter plot, fit a regression line, identify the top 3 outliers, and write a detailed analysis for each outlier."*
- **Description of Degradation**: The agent writes a python script that runs successfully but fails to output a complete answer, or exceeds the maximum loop iterations (10 turns) due to debugging python runtime errors.
- **Root Cause**: Complex plotting + statistical fitting + outlier analysis requires many libraries (pandas, matplotlib, numpy, scipy). If the agent hits a small syntax warning, pandas depreciation warning, or index error, it enters a self-correction loop. With a limit of 10 turns, the reasoning capacity might be exhausted before it can structure the final JSON response, leading to a timeout or failure refusal.
- **Proposed Fix**:
  - Increase the max iteration count to 15 for queries containing complex mathematical keywords (e.g., "regression", "scatter", "outlier").
  - Provide a pre-installed helper module `app/analytics_helpers.py` with standard functions like `plot_regression()`, `find_outliers()`, and `calculate_correlations()` so the agent can call simple, tested code rather than writing verbose numpy/scipy scripts.
