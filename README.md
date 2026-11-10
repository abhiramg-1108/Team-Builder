# 🎯 Smart Project Team Formation Engine

An intelligent, full-stack decision-support platform designed to solve the college project allocation problem using applied **Data Structures and Algorithms (Graphs, Hash Maps, and Dynamic Arrays)**. Built with **Python**, **SQLite**, and **Streamlit**.

---

## 💡 The Ideology & Problem Statement

In academic environments, project teams are almost universally formed through one of two flawed mechanisms:

1. **Unconstrained Self-Selection (Friendship Groups):** Students partner with close friends. This routinely creates severe structural imbalances:
   - **Homogeneity & Skill Clones:** Four frontend engineers team up together, leaving their project without backend or database architecture.
   - **Interpersonal Echo Chambers:** Friendship groups often avoid conflict, struggle with accountability, or isolate students outside established social circles.
2. **Arbitrary Assignment (First-Come, First-Served / Random Draw):** Instructors group students alphabetically or randomly. While this distributes skill diversity by chance, it ignores:
   - **Scheduling Conflicts:** Teammates have zero mutually compatible free hours, causing communication breakdowns.
   - **Past Interpersonal Friction:** Forcing students with historical conflicts into the same team destroys project velocity.

### The Core Objective
To formulate team formation not as an arbitrary administrative task, but as a **Multi-Objective Constrained Optimization Problem**. The engine simultaneously:
- **Maximizes Skill Coverage:** Ensures every team possesses the core technical competencies (Frontend, Backend, AI/ML, Database) needed to deliver an end-to-end project.
- **Minimizes Redundancy:** Penalizes overlapping competencies so scarce skills are distributed equitably across the class.
- **Harmonizes Logistics:** Uses set intersection to pair students with overlapping free days for team coordination.
- **Respects Graph Dynamics:** Balances positive partner preferences (`+1` edges) against absolute conflict disqualifications (`-1` edges).

---

## 🔄 Two-Portal Workflow Architecture

The application operates on a strict **Zero-Trust, Three-Step Lifecycle** to prevent duplicate submissions, identity spoofing, and data corruption:

```text
[ Step 1: Professor Upload ]
           │
           ▼
┌──────────────────────────────────────────────┐
│  Upload Master Class CSV (roll_no, name)     │  -->  Initialized in SQLite
└──────────────────────────────────────────────┘       (All students set to registered = 0)
           │
           ▼
[ Step 2: Student Self-Registration ]
           │
           ▼
┌──────────────────────────────────────────────┐
│  Student selects Roll No from Unregistered   │
│  Submits: Skills, Interests, Free Days,      │  -->  Locked in SQLite (registered = 1)
│  Confidential Partner (+1) & Conflict (-1)   │       (Instantly removed from dropdown)
└──────────────────────────────────────────────┘
           │
           ▼
[ Step 3: Algorithmic Drafting & Export ]
           │
           ▼
┌──────────────────────────────────────────────┐
│  Professor Dashboard runs Round-Robin Draft  │
│  Resolves conflicts via Local-Search Swaps   │  -->  Export Formed Teams to CSV
│  Visualizes Network Graph & Radar Charts     │
└──────────────────────────────────────────────┘
```

1. **Step 1: Professor Master Roster Ingestion:** The database starts clean. The instructor uploads an official course roster (`roll_no, name`).
2. **Step 2: One-Time Student Claim & Lock:** Students access the **Student Portal**, select their name from a filtered dropdown containing *only unregistered students*, submit their competencies and preferences, and lock their profile. Once submitted, their profile cannot be overwritten or re-registered by anyone else.
3. **Step 3: Algorithmic Synthesis & Export:** The **Professor Dashboard** tracks real-time class registration, executes the multi-stage draft, displays interactive radar charts and network topology, and exports the final teams directly to CSV.

---

## 🧠 Data Structures & Algorithmic Complexity

| Data Structure | Python Implementation | Architectural Role | Time Complexity |
| :--- | :--- | :--- | :--- |
| **Hash Map** | `dict` (`self.students`) | Stores student records indexed by `student_id` (`skills`, `interests`, `availability`). | $O(1)$ average lookup / insertion |
| **Adjacency List Graph** | `dict` of `dicts` (`self.preference_graph`) | Models student relationships. Directed edges store weights: `+1` (preferred collaborator) and `-1` (interpersonal conflict). | $O(1)$ edge existence and weight check |
| **Dynamic Arrays / Lists** | `list` (`teams`, `required_skills`, `logs`) | Manages draft rounds, stores final team rosters, and retains execution audit trails. | $O(N)$ sequential operations |
| **Relational Database** | `sqlite3` (`class_roster.db`) | Enforces roster integrity, prevents duplicate claims, and provides session-independent persistence. | $O(\log N)$ indexed queries |

### Mathematical Fit Scoring Function

For any unassigned candidate $c$ and partially formed team $T$, the fit score $S(c, T)$ is computed as:

$$S(c, T) = \begin{cases} -\infty, & \text{if } \exists m \in T \text{ such that } (c, m) = -1 \text{ or } (m, c) = -1 \\ W_{\text{pref}} \cdot \sum_{m \in T} (E_{c, m} + E_{m, c}) + W_{\text{skill}} \cdot \Delta_{\text{skills}}(c, T) + W_{\text{sched}} \cdot \sum_{m \in T} \vert{}A_c \cap A_m\vert{} + W_{\text{int}} \cdot \sum_{m \in T} \vert{}I_c \cap I_m\vert{}, & \text{otherwise} \end{cases}$$

Where:
- $E_{u, v} \in \{+1, -1\}$ represents edge weight in the Adjacency List.
- $\Delta_{\text{skills}}(c, T)$ awards points for uncovered required skills and penalizes duplicate coverage.
- $A_u$ and $I_u$ represent Availability and Domain Interest sets respectively.

---

## ⚖️ Algorithmic Trade-offs: Why Greedy Draft vs. Bipartite vs. Clustering?

During project design, multiple algorithmic paradigms were evaluated:

### 1. Maximum Bipartite Matching (Hungarian Algorithm / Min-Cost Max Flow)
- **The Concept:** Create partition $U$ (Students) and partition $V$ (Team Skill Slots), adding edges where a student has the requisite skill.
- **The Theoretical Limitation:** By strict graph theory definition, bipartite graphs cannot contain edges within the same partition ($U \times U = \emptyset$). Because student-to-student preferences and conflicts reside strictly within the student partition, **pure bipartite matching cannot evaluate student-to-student edges**. Modeling both slot allocation and interpersonal constraints transforms the problem into an NP-hard Quadratic Assignment Problem.

### 2. Unsupervised Clustering (K-Means / Agglomerative)
- **The Concept:** Treat students as feature vectors and cluster them into $K$ teams based on distance metrics.
- **The "Homogeneity Paradox":** Clustering algorithms optimize for **intra-cluster similarity**. Running standard clustering on skill vectors clusters all frontend developers together and all backend engineers together—producing the exact failure mode the system seeks to eliminate.

### 3. Selected Solution: Round-Robin Greedy Draft with Local-Search Repair
- **Phase 1 (Drafting):** Fills teams round-by-round to distribute top anchors evenly across all teams.
- **Phase 2 (Local-Search Swap):** If edge constraints force an incompatible student into a team during the final draft round, a post-processing swap algorithm searches the solution space for a 1-for-1 conflict-free exchange between teams that preserves global skill coverage.

---

## 📊 Key UI & Visualization Features

- **🕸️ Clustered Network Topology:** Visualizes students as circular nodes grouped physically by assigned team. Edge colors denote relationship nature (Solid Green = `+1` Partner, Dotted Red = `-1` Conflict).
- **🕸️ Skill Polygon Radar Charts:** Each formed team displays a 4-axis spider chart (`Frontend`, `Backend`, `AI/ML`, `Database`). A balanced team forms a wide polygon; gaps appear as inward notches.
- **🎛️ Live Parameter Sliders (0–100):** Real-time sensitivity analysis. Adjust the priority of Skill Coverage vs. Friendship Graph Weight to observe how teams restructure dynamically.
- **📜 DSA Audit Inspector:** An expandable terminal at the bottom of the dashboard exposing the raw JSON Hash Map, the Graph Adjacency List, and step-by-step drafting logs.

---

## 🚀 Installation & Local Setup

### 1. Clone the Repository
```bash
git clone [https://github.com/abhiramg-1108/Team-Builder.git](https://github.com/abhiramg-1108/Team-Builder.git)
cd Team-Builder
```

### 2. Set Up a Virtual Environment & Install Dependencies
```bash
python -m venv venv

# Windows:
venv\Scripts\activate
# Mac / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Run the Application
```bash
python -m streamlit run app.py
```
Open your browser and navigate to `http://localhost:8501`.

---

## 📂 Project Structure

```text
Team-Builder/
├── app.py                  # Core application (Streamlit UI, SQLite layer, DSA TeamBuilder engine)
├── class_roster.db         # Persistent SQLite database (auto-generated on first run)
├── requirements.txt        # Production dependencies (streamlit, plotly, networkx)
└── README.md               # System documentation and algorithmic specification
```
