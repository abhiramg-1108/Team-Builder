import streamlit as st
import plotly.graph_objects as go
import networkx as nx
import math

# ==========================================
# 1. CORE DSA ENGINE (Graphs, Hash Maps, Arrays)
# ==========================================
class TeamBuilder:
    def __init__(self, required_skills, team_size, skill_weight=50, friend_weight=30, schedule_weight=20):
        # ARRAY: List of required project skills
        self.required_skills = required_skills
        self.team_size = team_size
        
        # Normalized 0-100 weights scaled cleanly for scoring
        self.skill_weight = skill_weight
        self.friend_weight = friend_weight
        self.schedule_weight = schedule_weight
        
        # HASH MAP: student_id -> student profile dict
        self.students = {}
        
        # GRAPH (Adjacency List): student_id -> {other_student_id: +1 or -1}
        self.preference_graph = {}
        
        # ARRAY: Execution logs for DSA demonstration
        self.logs = []

    def log(self, message):
        self.logs.append(message)

    def add_student(self, student_id, name, skills, interests, availability):
        self.students[student_id] = {
            "name": name,
            "skills": skills,               # Array
            "interests": interests,         # Array
            "availability": availability    # Array
        }
        if student_id not in self.preference_graph:
            self.preference_graph[student_id] = {}

    def add_preference(self, student_a, student_b, weight):
        if student_a in self.preference_graph and student_b in self.students:
            self.preference_graph[student_a][student_b] = weight

    def has_conflict(self, candidate_id, team):
        for member_id in team:
            if member_id == candidate_id:
                continue
            edge_a_to_b = self.preference_graph.get(candidate_id, {}).get(member_id, 0)
            edge_b_to_a = self.preference_graph.get(member_id, {}).get(candidate_id, 0)
            if edge_a_to_b == -1 or edge_b_to_a == -1:
                return True
        return False

    def calculate_fit_score(self, candidate_id, current_team):
        candidate = self.students[candidate_id]
        
        # Round 1 (Empty Team): Pick strong anchor students first
        if not current_team:
            useful_skills = [s for s in candidate["skills"] if s in self.required_skills]
            has_friends = any(w == 1 for w in self.preference_graph.get(candidate_id, {}).values())
            # Slight holdback if they have a friend so they stay free to pair up in Round 2
            friend_holdback = -(self.friend_weight * 0.15) if has_friends else 0
            return (len(useful_skills) * self.skill_weight) + friend_holdback

        if self.has_conflict(candidate_id, current_team):
            return -9999

        team_skills = set()
        for member_id in current_team:
            team_skills.update(self.students[member_id]["skills"])

        score = 0

        # 1. Graph Preferences (+1 Friend / -1 Conflict)
        for member_id in current_team:
            edge_a_to_b = self.preference_graph.get(candidate_id, {}).get(member_id, 0)
            edge_b_to_a = self.preference_graph.get(member_id, {}).get(candidate_id, 0)
            score += (edge_a_to_b + edge_b_to_a) * self.friend_weight

        # 2. Skill Gaps vs Overlaps
        for skill in candidate["skills"]:
            if skill in self.required_skills:
                if skill not in team_skills:
                    score += self.skill_weight
                else:
                    # Overlap penalty scales with skill_weight so redundant skills stay separated
                    score -= (self.skill_weight * 0.35)

        # 3. Schedule & Interest Match (FIXED BUG: now properly checks member["interests"])
        for member_id in current_team:
            member = self.students[member_id]
            shared_time = set(candidate["availability"]).intersection(member["availability"])
            shared_interest = set(candidate["interests"]).intersection(member["interests"])
            score += len(shared_time) * self.schedule_weight
            score += len(shared_interest) * (self.schedule_weight * 0.8)

        return round(score, 1)

    def resolve_conflicts(self, teams):
        for t1_idx, team1 in enumerate(teams):
            for s1 in list(team1):
                if self.has_conflict(s1, team1):
                    self.log(f"⚠️ Conflict detected: {self.students[s1]['name']} ({s1}) in Team {t1_idx + 1}.")
                    swapped = False
                    for t2_idx, team2 in enumerate(teams):
                        if t1_idx == t2_idx:
                            continue
                        for s2 in list(team2):
                            temp_team1 = [m for m in team1 if m != s1]
                            temp_team2 = [m for m in team2 if m != s2]
                            if not self.has_conflict(s2, temp_team1) and not self.has_conflict(s1, temp_team2):
                                team1.remove(s1)
                                team2.remove(s2)
                                team1.append(s2)
                                team2.append(s1)
                                self.log(f"✅ Auto-Swapped {self.students[s1]['name']} (Team {t1_idx+1}) ↔ {self.students[s2]['name']} (Team {t2_idx+1}).")
                                swapped = True
                                break
                        if swapped:
                            break
                    if not swapped:
                        self.log(f"❌ No conflict-free swap possible for {self.students[s1]['name']}.")

    def form_teams(self):
        unassigned = set(self.students.keys())
        if not unassigned:
            return []
            
        num_teams = max(1, math.ceil(len(self.students) / self.team_size))
        teams = [[] for _ in range(num_teams)]

        round_num = 1
        # Keep drafting round-by-round until ALL students are assigned
        while unassigned:
            self.log(f"--- Draft Round {round_num} ---")
            for team_idx, team in enumerate(teams):
                if not unassigned:
                    break
                best_candidate = None
                best_score = -float('inf')

                for candidate_id in unassigned:
                    score = self.calculate_fit_score(candidate_id, team)
                    if score > best_score:
                        best_score = score
                        best_candidate = candidate_id

                if best_candidate is not None:
                    if best_score == -9999:
                        self.log(f"⚠️ Forced {self.students[best_candidate]['name']} into Team {team_idx+1} (Conflict!).")
                    else:
                        self.log(f"Team {team_idx+1} drafted {self.students[best_candidate]['name']} (Fit Score: {best_score})")
                    team.append(best_candidate)
                    unassigned.remove(best_candidate)
            round_num += 1

        self.resolve_conflicts(teams)
        return teams


# ==========================================
# 2. ENHANCED VISUALIZATIONS
# ==========================================
PALETTE = ["#6366F1", "#10B981", "#F59E0B", "#EC4899", "#3B82F6", "#8B5CF6"]

def plot_network_graph(builder, teams):
    G = nx.Graph()
    node_color_map = {}
    node_team_map = {}

    # Position nodes in circular clusters per team so visual grouping is crystal clear
    pos = {}
    num_teams = max(1, len(teams))
    for t_idx, team in enumerate(teams):
        angle_center = 2 * math.pi * t_idx / num_teams
        cx, cy = 2.2 * math.cos(angle_center), 2.2 * math.sin(angle_center)
        
        for m_idx, sid in enumerate(team):
            G.add_node(sid)
            node_color_map[sid] = PALETTE[t_idx % len(PALETTE)]
            node_team_map[sid] = f"Team {t_idx + 1}"
            
            sub_angle = 2 * math.pi * m_idx / max(1, len(team))
            pos[sid] = (cx + 0.75 * math.cos(sub_angle), cy + 0.75 * math.sin(sub_angle))

    for u, neighbors in builder.preference_graph.items():
        for v, weight in neighbors.items():
            if u in G.nodes and v in G.nodes:
                G.add_edge(u, v, weight=weight)

    edge_traces = []
    for u, v, data in G.edges(data=True):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        is_friend = data["weight"] == 1
        edge_traces.append(
            go.Scatter(
                x=[x0, x1, None], y=[y0, y1, None],
                mode="lines",
                line=dict(
                    width=3.5 if is_friend else 2.5,
                    color="#22C55E" if is_friend else "#EF4444",
                    dash="solid" if is_friend else "dot"
                ),
                hoverinfo="none",
                showlegend=False
            )
        )

    # Create legend traces per team so colors are clearly labeled
    team_traces = []
    for t_idx, team in enumerate(teams):
        if not team:
            continue
        t_color = PALETTE[t_idx % len(PALETTE)]
        team_traces.append(
            go.Scatter(
                x=[pos[sid][0] for sid in team],
                y=[pos[sid][1] for sid in team],
                mode="markers+text",
                name=f"Team {t_idx + 1}",
                text=[f"<b>{builder.students[sid]['name']}</b> ({sid})" for sid in team],
                textposition="top center",
                hovertext=[
                    f"<b>{builder.students[sid]['name']} ({sid})</b><br>"
                    f"Assigned: Team {t_idx+1}<br>"
                    f"Skills: {', '.join(builder.students[sid]['skills'])}<br>"
                    f"Free: {', '.join(builder.students[sid]['availability'])}"
                    for sid in team
                ],
                hoverinfo="text",
                marker=dict(size=32, color=t_color, line=dict(width=3, color="#1E293B"))
            )
        )

    fig = go.Figure(data=edge_traces + team_traces)
    fig.update_layout(
        title="<b>Interactive Student Graph & Team Clusters</b> <span style='font-size:12px;color:gray'>(Solid Green = +1 Preferred Partner | Dotted Red = -1 Conflict)</span>",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-3.8, 3.8]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-3.8, 3.8]),
        height=430,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    return fig


def plot_radar_chart(team_name, skill_counts, required_skills, color):
    values = [skill_counts.get(skill, 0) for skill in required_skills]
    categories = required_skills + [required_skills[0]]
    values = values + [values[0]]

    fig = go.Figure(
        data=go.Scatterpolar(
            r=values,
            theta=categories,
            fill="toself",
            fillcolor=f"rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, 0.25)",
            line=dict(color=color, width=2.5),
            marker=dict(size=7, color=color),
            name=team_name
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max(2, max(values))], dtick=1, gridcolor="rgba(148,163,184,0.2)"),
            angularaxis=dict(gridcolor="rgba(148,163,184,0.2)")
        ),
        showlegend=False,
        height=240,
        margin=dict(l=35, r=35, t=25, b=25),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig


# ==========================================
# 3. STREAMLIT UI & STATE MANAGEMENT
# ==========================================
st.set_page_config(page_title="DSA Smart Team Builder", layout="wide")

# Custom CSS for sleek cards & badges
st.markdown("""
<style>
.team-card {
    padding: 18px;
    border-radius: 12px;
    background: rgba(148, 163, 184, 0.08);
    border: 1px solid rgba(148, 163, 184, 0.2);
    margin-bottom: 16px;
}
.skill-badge {
    display: inline-block;
    padding: 3px 10px;
    margin: 2px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    background: rgba(99, 102, 241, 0.15);
    color: #818CF8;
    border: 1px solid rgba(99, 102, 241, 0.3);
}
</style>
""", unsafe_allow_html=True)

st.title("🎯 Smart Project Team Formation Engine")
st.caption("DSA Architecture: **Adjacency List Graph** (Preferences & Conflicts) • **Hash Map** (`O(1)` Student Lookups) • **Arrays** (Round-Robin Greedy Draft & Conflict Swap)")

# --- Initialize Presets in Session State ---
DEFAULT_6_STUDENTS = [
    ("S1", "Aarav",  ["Frontend", "UI/UX"],   ["Web", "EdTech"],   ["Mon", "Wed"]),
    ("S2", "Bhavya", ["Backend", "Database"], ["Web", "FinTech"],  ["Mon", "Fri"]),
    ("S3", "Charan", ["AI/ML"],               ["EdTech", "Health"],["Mon", "Wed"]),
    ("S4", "Diya",   ["Frontend", "Backend"], ["Health", "AI"],    ["Tue", "Thu"]),
    ("S5", "Eshan",  ["AI/ML", "Database"],   ["Health", "Web"],   ["Tue", "Thu"]),
    ("S6", "Farah",  ["Frontend"],            ["Web", "EdTech"],   ["Tue", "Thu"]),
]
DEFAULT_6_EDGES = [
    ("S1", "S6", 1), ("S6", "S1", 1),
    ("S1", "S3", 1), ("S3", "S1", 1),
    ("S6", "S5", -1), ("S6", "S4", -1)
]

PRESET_12_STUDENTS = DEFAULT_6_STUDENTS + [
    ("S7", "Gaurav", ["Backend", "AI/ML"],    ["FinTech", "AI"],   ["Mon", "Wed"]),
    ("S8", "Hima",   ["Frontend", "Database"],["Web", "Health"],   ["Tue", "Fri"]),
    ("S9", "Ishaan", ["AI/ML", "UI/UX"],      ["EdTech", "AI"],    ["Mon", "Thu"]),
    ("S10", "Jiya",  ["Backend"],             ["Web", "FinTech"],  ["Wed", "Fri"]),
    ("S11", "Kiran", ["Database", "Frontend"],["Health", "EdTech"],["Tue", "Thu"]),
    ("S12", "Laksh", ["AI/ML", "Backend"],    ["AI", "Web"],       ["Mon", "Fri"]),
]
PRESET_12_EDGES = DEFAULT_6_EDGES + [
    ("S7", "S8", 1), ("S8", "S7", 1),
    ("S9", "S12", -1), ("S10", "S11", 1)
]

if "students_list" not in st.session_state:
    st.session_state.students_list = list(DEFAULT_6_STUDENTS)
if "edges_list" not in st.session_state:
    st.session_state.edges_list = list(DEFAULT_6_EDGES)

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🎛️ Class Dataset Preset")
col_p1, col_p2 = st.sidebar.columns(2)
if col_p1.button("6 Students (Demo)", use_container_width=True):
    st.session_state.students_list = list(DEFAULT_6_STUDENTS)
    st.session_state.edges_list = list(DEFAULT_6_EDGES)
    st.rerun()
if col_p2.button("12 Students (Large)", use_container_width=True):
    st.session_state.students_list = list(PRESET_12_STUDENTS)
    st.session_state.edges_list = list(PRESET_12_EDGES)
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Algorithm Weights (0–100)")
team_sz = st.sidebar.slider("Target Team Size", 2, 5, 3)
skill_w = st.sidebar.slider("Skill Coverage Priority", 0, 100, 60, step=5, help="Higher = Prioritizes filling missing team skills.")
friend_w = st.sidebar.slider("Friendship Preference (+1 Edge)", 0, 100, 35, step=5, help="Drag to 90+ and lower Skill Priority to see friends group up despite overlapping skills!")
sched_w = st.sidebar.slider("Schedule & Interest Match", 0, 100, 20, step=5)

# --- Add Any Student ---
with st.sidebar.expander("➕ Add New Student Node"):
    with st.form("add_student_form"):
        next_id = f"S{len(st.session_state.students_list)+1}"
        new_name = st.text_input("Student Name", "Navya")
        new_skills = st.multiselect("Skills", ["Frontend", "Backend", "AI/ML", "Database", "UI/UX"], default=["Backend", "Database"])
        new_interests = st.multiselect("Interests", ["Web", "AI", "EdTech", "FinTech", "Health"], default=["AI", "Web"])
        new_avail = st.multiselect("Free Days", ["Mon", "Tue", "Wed", "Thu", "Fri"], default=["Mon", "Wed"])
        if st.form_submit_button("Add to Hash Map") and new_name:
            st.session_state.students_list.append((next_id, new_name, new_skills, new_interests, new_avail))
            st.rerun()

# --- Add Graph Edge Between ANY Two Students ---
with st.sidebar.expander("🕸️ Add Friend / Conflict Graph Edge"):
    student_label_map = {sid: f"{name} ({sid})" for sid, name, _, _, _ in st.session_state.students_list}
    s_ids = list(student_label_map.keys())
    with st.form("add_edge_form"):
        u_node = st.selectbox("From Student", s_ids, format_func=lambda x: student_label_map[x])
        v_node = st.selectbox("To Student", s_ids, index=min(1, len(s_ids)-1), format_func=lambda x: student_label_map[x])
        edge_type = st.radio("Relationship Type", [1, -1], format_func=lambda w: "💚 Preferred Partner (+1)" if w == 1 else "🚫 Conflict / Avoid (-1)")
        both_ways = st.checkbox("Make Mutual (Bidirectional Edge)", value=True)
        if st.form_submit_button("Add Graph Edge") and u_node != v_node:
            st.session_state.edges_list = [(u, v, w) for u, v, w in st.session_state.edges_list if not (u == u_node and v == v_node)]
            st.session_state.edges_list.append((u_node, v_node, edge_type))
            if both_ways:
                st.session_state.edges_list = [(u, v, w) for u, v, w in st.session_state.edges_list if not (u == v_node and v == u_node)]
                st.session_state.edges_list.append((v_node, u_node, edge_type))
            st.rerun()

# --- Run the Engine ---
required_skills = ["Frontend", "Backend", "AI/ML", "Database"]
builder = TeamBuilder(required_skills, team_size=team_sz, skill_weight=skill_w, friend_weight=friend_w, schedule_weight=sched_w)

for sid, name, skills, interests, avail in st.session_state.students_list:
    builder.add_student(sid, name, skills, interests, avail)

for u, v, w in st.session_state.edges_list:
    builder.add_preference(u, v, w)

teams = builder.form_teams()

# --- Manual Swap Simulator ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Live Swap Simulator")
all_sids = list(builder.students.keys())
swap_a = st.sidebar.selectbox("Swap Student A", ["None"] + all_sids, format_func=lambda x: f"{builder.students[x]['name']} ({x})" if x != "None" else "None")
swap_b = st.sidebar.selectbox("With Student B", ["None"] + all_sids, format_func=lambda x: f"{builder.students[x]['name']} ({x})" if x != "None" else "None")

if swap_a != "None" and swap_b != "None" and swap_a != swap_b:
    for team in teams:
        if swap_a in team and swap_b not in team:
            team[team.index(swap_a)] = swap_b
        elif swap_b in team and swap_a not in team:
            team[team.index(swap_b)] = swap_a
    st.sidebar.info(f"Swapped {builder.students[swap_a]['name']} ↔ {builder.students[swap_b]['name']}")

# --- Calculate Top Summary Metrics ---
coverage_scores = []
total_conflicts = 0
for team in teams:
    t_skills = {s for sid in team for s in builder.students[sid]["skills"] if s in required_skills}
    coverage_scores.append((len(t_skills) / len(required_skills)) * 100)
    if any(builder.has_conflict(sid, team) for sid in team):
        total_conflicts += 1

avg_coverage = sum(coverage_scores) / max(1, len(coverage_scores))
fairness = max(0.0, 100.0 - (max(coverage_scores) - min(coverage_scores))) if coverage_scores else 100.0

k1, k2, k3, k4 = st.columns(4)
k1.metric("👥 Total Students / Teams", f"{len(builder.students)} Students → {len(teams)} Teams")
k2.metric("📊 Avg Skill Coverage", f"{avg_coverage:.1f}%")
k3.metric("⚖️ Fairness Score", f"{fairness:.1f} / 100")
k4.metric("🛡️ Conflict Status", "0 Conflicts" if total_conflicts == 0 else f"{total_conflicts} Conflict(s)!", delta="Optimal" if total_conflicts == 0 else "Action Needed", delta_color="normal" if total_conflicts == 0 else "inverse")

# --- Network Graph ---
st.plotly_chart(plot_network_graph(builder, teams), use_container_width=True)

# --- 2-Column Responsive Team Cards ---
st.subheader("📋 Generated Teams & Skill Balance")
for row_start in range(0, len(teams), 2):
    row_cols = st.columns(2)
    for col_offset in range(2):
        t_idx = row_start + col_offset
        if t_idx >= len(teams):
            break
        team = teams[t_idx]
        t_color = PALETTE[t_idx % len(PALETTE)]
        
        with row_cols[col_offset]:
            skill_counts = {}
            for sid in team:
                for s in builder.students[sid]["skills"]:
                    skill_counts[s] = skill_counts.get(s, 0) + 1

            missing = [s for s in required_skills if s not in skill_counts]
            overlaps = [s for s, c in skill_counts.items() if c > 1]
            cov_pct = ((len(required_skills) - len(missing)) / len(required_skills)) * 100
            has_conf = any(builder.has_conflict(sid, team) for sid in team)

            member_badges = ""
            for sid in team:
                s_obj = builder.students[sid]
                skills_str = ", ".join(s_obj["skills"])
                member_badges += f"<div style='margin:4px 0;'>• <b>{s_obj['name']}</b> (<code>{sid}</code>) — <span class='skill-badge'>{skills_str}</span></div>"

            st.markdown(f"""
            <div class="team-card" style="border-left: 6px solid {t_color};">
                <h4 style="margin:0 0 8px 0;">Team {t_idx + 1} <span style="float:right;font-size:14px;color:{t_color};">{cov_pct:.0f}% Coverage</span></h4>
                {member_badges}
            </div>
            """, unsafe_allow_html=True)

            if has_conf:
                st.error("⚠️ Conflict Alert: Team contains members with a -1 Graph edge!")
            elif not missing:
                st.success("✅ All 4 Core Skills Covered & Conflict-Free")
            else:
                st.warning(f"⚠️ Missing Skills: {', '.join(missing)}")

            st.caption(f"**Overlapping Skills:** {', '.join(overlaps) if overlaps else 'None'}")
            st.plotly_chart(plot_radar_chart(f"Team {t_idx+1}", skill_counts, required_skills, t_color), use_container_width=True)

# --- DSA Inspector at Bottom ---
with st.expander("🔍 Inspect Underlying Data Structures & Execution Logs (DSA Viva Panel)"):
    tab1, tab2, tab3 = st.tabs(["📜 Draft & Swap Logs (Array)", "🕸️ Adjacency List (Graph)", "🗂️ Student Profiles (Hash Map)"])
    with tab1:
        st.code("\n".join(builder.logs), language="text")
    with tab2:
        st.json(builder.preference_graph)
    with tab3:
        st.json(builder.students)