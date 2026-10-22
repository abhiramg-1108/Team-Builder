# Team-Builder
# 🎯 Smart Project Team Formation Engine (DSA Mini-Project)

An interactive algorithm visualizer and team formation engine built with **Python** and **Streamlit**. 

In college courses, students often form project teams based on friendship or first-come-first-served choices—leading to teams with overlapping skills, critical missing skills, or interpersonal conflicts. This project applies core **Data Structures and Algorithms (Graphs, Hash Maps, and Arrays)** to form balanced, conflict-free teams automatically.

---

## 🧠 Core Data Structures Used

| Data Structure | Python Implementation | Role in the Algorithm | Time Complexity |
| :--- | :--- | :--- | :--- |
| **Hash Map** | `dict` (`self.students`) | Stores student profiles (skills, interests, schedule availability) indexed by `student_id`. | $O(1)$ average lookup |
| **Graph (Adjacency List)** | `dict` of `dicts` (`self.preference_graph`) | Models student relationships as a weighted directed graph: `+1` for preferred partners and `-1` for conflicts to avoid. | $O(1)$ edge weight check |
| **Arrays / Dynamic Lists** | `list` (`self.required_skills`, `teams`, `self.logs`) | Tracks required project competencies, stores formed team rosters, and records step-by-step execution logs. | $O(N)$ traversal |

---

## ⚙️ How the Algorithm Works

1. **Round-Robin Greedy Draft:**
   - Rather than filling Team 1 completely before moving to Team 2 (which leaves later teams with weak leftovers), the engine drafts students in **rounds** (like a sports draft) so every team gets a strong anchor member first.
2. **Multi-Factor Fit Scoring (`calculate_fit_score`):**
   - **Hard Conflict Filter:** Checks the **Adjacency List Graph** for any `-1` edges between the candidate and current team members. If found, returns `-9999` to prevent pairing incompatible students.
   - **Skill Gap vs. Overlap Scoring:** Rewards candidates who bring a required skill the team is currently missing, and applies an overlap penalty if the team already possesses that skill.
   - **Schedule & Interest Alignment:** Uses set intersections on student availability and interest arrays to ensure teammates actually have common free hours to meet.
   - **Partner Preferences:** Adds a weighted bonus for `+1` graph edges without letting friendships override essential skill coverage.
3. **Post-Draft Conflict Resolution (`resolve_conflicts`):**
   - If the final remaining student in the pool is forced onto a team with a `-1` conflict, a local-search swap step inspects other formed teams and performs a 1-for-1 member swap that leaves both teams 100% conflict-free.

---

## ✨ Key Dashboard Features

- **🕸️ Interactive Network Graph:** Visualizes students as nodes clustered by their assigned team, with green solid edges (`+1` friend preference) and red dotted edges (`-1` conflict).
- **🕸️ Team Skill Radar Charts:** Displays a polygon radar chart for each team across core required skills (`Frontend`, `Backend`, `AI/ML`, `Database`) to visually verify balanced coverage.
- **🎛️ Live "What-If" Weight Sliders (0–100):** Dynamically adjust the priority of Skill Coverage, Friendship Graph Edges, and Schedule Overlap to see teams rebalance in real time.
- **🔄 Manual Swap Simulator:** Test manual overrides between any two students and immediately see if the swap triggers a conflict alert or reduces skill coverage.
- **🔍 Built-in DSA Viva Inspector:** View the raw JSON Hash Map, Graph Adjacency List, and step-by-step draft/swap execution logs directly inside the UI.

---

## 🚀 How to Run Locally

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git](https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git)
   cd YOUR-REPO-NAME
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the Streamlit app:**
   ```bash
   python -m streamlit run app.py
   ```
# Radha Ma'am told to go through Bipartite algorithm and clustering algorithms for our project instead of Greedy approach 