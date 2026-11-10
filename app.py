import streamlit as st
import plotly.graph_objects as go
import networkx as nx
import sqlite3
import json
import math
import csv
import io

# ==========================================
# 1. PERSISTENT SQLITE DATABASE (ROSTER LOCK)
# ==========================================
DB_FILE = "class_roster.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # registered: 0 = Pending (Uploaded by Prof), 1 = Claimed & Submitted by Student
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            sid TEXT PRIMARY KEY,
            name TEXT,
            skills TEXT,
            interests TEXT,
            availability TEXT,
            registered INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS edges (
            u TEXT,
            v TEXT,
            weight INTEGER,
            PRIMARY KEY (u, v)
        )
    """)
    conn.commit()
    conn.close()

def clear_entire_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM students")
    c.execute("DELETE FROM edges")
    conn.commit()
    conn.close()

def import_master_roster(roster_rows):
    """Professor uploads (sid, name) list. Resets database to this fresh class roster."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM students")
    c.execute("DELETE FROM edges")
    for sid, name in roster_rows:
        c.execute(
            "INSERT OR REPLACE INTO students (sid, name, skills, interests, availability, registered) VALUES (?, ?, ?, ?, ?, 0)",
            (sid, name, json.dumps([]), json.dumps([]), json.dumps([]))
        )
    conn.commit()
    conn.close()

def register_student_submission(sid, skills, interests, avail, friend_id="None", avoid_id="None"):
    """Locks the student's profile (registered = 1) so no one else can select them."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """UPDATE students 
           SET skills = ?, interests = ?, availability = ?, registered = 1 
           WHERE sid = ? AND registered = 0""",
        (json.dumps(skills), json.dumps(interests), json.dumps(avail), sid)
    )
    if friend_id != "None" and friend_id != sid:
        c.execute("INSERT OR REPLACE INTO edges VALUES (?, ?, 1)", (sid, friend_id))
    if avoid_id != "None" and avoid_id != sid:
        c.execute("INSERT OR REPLACE INTO edges VALUES (?, ?, -1)", (sid, avoid_id))
    conn.commit()
    conn.close()

def unlock_student_registration(sid):
    """Allows the professor to reset a single student's submission if they made a mistake."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "UPDATE students SET skills = '[]', interests = '[]', availability = '[]', registered = 0 WHERE sid = ?",
        (sid,)
    )
    c.execute("DELETE FROM edges WHERE u = ?", (sid,))
    conn.commit()
    conn.close()

def fetch_roster_status():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT sid, name, skills, interests, availability, registered FROM students ORDER BY sid")
    rows = c.fetchall()
    
    unregistered = []
    registered = []
    all_students_map = {}
    
    for r in rows:
        sid, name, skills, interests, avail, reg = r[0], r[1], json.loads(r[2]), json.loads(r[3]), json.loads(r[4]), r[5]
        all_students_map[sid] = name
        if reg == 1:
            registered.append((sid, name, skills, interests, avail))
        else:
            unregistered.append((sid, name))
            
    c.execute("SELECT u, v, weight FROM edges")
    edges = [(r[0], r[1], r[2]) for r in c.fetchall()]
    conn.close()
    return unregistered, registered, edges, all_students_map


# ==========================================
# 2. CORE DSA ENGINE (Graphs, Hash Maps, Arrays)
# ==========================================
class TeamBuilder:
    def __init__(self, required_skills, team_size, skill_weight=60, friend_weight=35, schedule_weight=20):
        self.required_skills = required_skills
        self.team_size = team_size
        self.skill_weight = skill_weight
        self.friend_weight = friend_weight
        self.schedule_weight = schedule_weight
        
        # HASH MAP: student_id -> student profile dict
        self.students = {}
        # GRAPH (Adjacency List): student_id -> {other_student_id: +1 or -1}
        self.preference_graph = {}
        # ARRAY: Step-by-step execution logs
        self.logs = []

    def log(self, message):
        self.logs.append(message)

    def add_student(self, student_id, name, skills, interests, availability):
        self.students[student_id] = {
            "name": name,
            "skills": skills,
            "interests": interests,
            "availability": availability
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
        
        if not current_team:
            useful_skills = [s for s in candidate["skills"] if s in self.required_skills]
            has_friends = any(w == 1 for w in self.preference_graph.get(candidate_id, {}).values())
            friend_holdback = -(self.friend_weight * 0.15) if has_friends else 0
            return (len(useful_skills) * self.skill_weight) + friend_holdback

        if self.has_conflict(candidate_id, current_team):
            return -9999

        team_skills = set()
        for member_id in current_team:
            team_skills.update(self.students[member_id]["skills"])

        score = 0

        # 1. Graph Preferences (+1 / -1)
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
                    score -= (self.skill_weight * 0.35)

        # 3. Schedule & Interest Match
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
# 3. VISUALIZATIONS
# ==========================================
PALETTE = ["#6366F1", "#10B981", "#F59E0B", "#EC4899", "#3B82F6", "#8B5CF6"]

def plot_network_graph(builder, teams):
    G = nx.Graph()
    pos = {}
    num_teams = max(1, len(teams))
    
    for t_idx, team in enumerate(teams):
        angle_center = 2 * math.pi * t_idx / num_teams
        cx, cy = 2.2 * math.cos(angle_center), 2.2 * math.sin(angle_center)
        for m_idx, sid in enumerate(team):
            G.add_node(sid)
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
        title="<b>Registered Student Preference Graph & Formed Clusters</b> <span style='font-size:12px;color:gray'>(Solid Green = +1 Partner | Dotted Red = -1 Conflict)</span>",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-3.8, 3.8]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-3.8, 3.8]),
        height=420,
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
# 4. STREAMLIT UI (ROSTER -> CLAIM -> EXPORT)
# ==========================================
st.set_page_config(page_title="Dynamic Smart Team Builder", layout="wide")
init_db()

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

st.title("🎯 Classroom Team Formation System")
st.caption("Workflow: **1. Professor Imports Master Roll-Call CSV** $\\rightarrow$ **2. Students Claim Their Roll No Once & Submit Skills** $\\rightarrow$ **3. Engine Builds Teams & Exports CSV**")

unregistered_list, registered_list, edges_data, all_students_map = fetch_roster_status()
total_roster_count = len(unregistered_list) + len(registered_list)

ALL_SKILLS = ["Frontend", "Backend", "AI/ML", "Database", "UI/UX"]
ALL_INTERESTS = ["Web", "AI", "EdTech", "FinTech", "Health"]
ALL_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]

# ==========================================
# SIDEBAR: PROFESSOR ROSTER UPLOAD & WEIGHTS
# ==========================================
st.sidebar.header("📂 Step 1: Master Class Roster")

# Provide a downloadable sample CSV so testing takes 5 seconds
sample_roster_csv = "roll_no,name\nS101,Aarav Sharma\nS102,Bhavya Nair\nS103,Charan Reddy\nS104,Diya Patel\nS105,Eshan Verma\nS106,Farah Khan\n"
st.sidebar.download_button(
    "⬇️ Download Sample Roll-Call CSV",
    data=sample_roster_csv,
    file_name="sample_class_roster.csv",
    mime="text/csv",
    use_container_width=True
)

uploaded_roster = st.sidebar.file_uploader("Upload Class Roll-Call CSV (`roll_no, name`)", type=["csv"])
if uploaded_roster is not None:
    if st.sidebar.button("📥 Initialize Class Roster from CSV", type="primary", use_container_width=True):
        content = io.StringIO(uploaded_roster.getvalue().decode("utf-8-sig"))
        reader = csv.DictReader(content)
        roster_rows = []
        for row in reader:
            # Support flexible column headers (roll_no / sid / id and name / student_name)
            normalized = {k.strip().lower(): v.strip() for k, v in row.items() if k and v}
            sid = normalized.get("roll_no") or normalized.get("sid") or normalized.get("id")
            name = normalized.get("name") or normalized.get("student_name")
            if sid and name:
                roster_rows.append((sid, name))
        if roster_rows:
            import_master_roster(roster_rows)
            st.sidebar.success(f"Loaded {len(roster_rows)} students! Ready for registration.")
            st.rerun()
        else:
            st.sidebar.error("Could not find `roll_no` and `name` columns in CSV.")

if total_roster_count > 0:
    if st.sidebar.button("🗑️ Wipe Entire Database", use_container_width=True):
        clear_entire_db()
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Step 3: Algorithm Weights")
team_sz = st.sidebar.slider("Target Team Size", 2, 5, 3)
skill_w = st.sidebar.slider("Skill Coverage Priority", 0, 100, 60, step=5)
friend_w = st.sidebar.slider("Friendship Preference (+1 Edge)", 0, 100, 35, step=5)
sched_w = st.sidebar.slider("Schedule & Interest Match", 0, 100, 20, step=5)

# Allow Professor to unlock a student if someone accidentally submitted wrong info
if registered_list:
    with st.sidebar.expander("🔓 Admin: Reset a Student's Lock"):
        reg_ids = [sid for sid, _, _, _, _ in registered_list]
        reset_sid = st.selectbox("Select Registered Student", reg_ids, format_func=lambda x: f"{all_students_map[x]} ({x})")
        if st.button("Unlock Student for Re-submission", use_container_width=True):
            unlock_student_registration(reset_sid)
            st.rerun()


# ==========================================
# MAIN TABS: STUDENT PORTAL vs PROFESSOR VIEW
# ==========================================
tab_student, tab_prof = st.tabs([
    f"🎓 Step 2: Student Registration Portal ({len(unregistered_list)} Pending)",
    f"👨‍🏫 Step 3: Professor Dashboard & Team Builder ({len(registered_list)}/{total_roster_count} Ready)"
])

# ------------------------------------------
# TAB 1: STUDENT SELF-REGISTRATION PORTAL
# ------------------------------------------
with tab_student:
    st.subheader("🎓 One-Time Student Skill & Schedule Submission")
    
    if total_roster_count == 0:
        st.info("👈 **Waiting for Professor:** No class roster has been uploaded yet. Please upload a Roll-Call CSV in the left sidebar (`Step 1`) to begin.")
    elif len(unregistered_list) == 0:
        st.success("🎉 **100% of the class has registered!** All student profiles are locked in. Switch to the **Professor Dashboard** tab to view and export the teams.")
    else:
        st.write("Select your **Roll Number & Name** from the official class roster below. **Note:** Once you submit, your name will be locked and removed from this list so no one else can submit under your name.")
        
        unreg_ids = [sid for sid, _ in unregistered_list]
        all_roster_ids = list(all_students_map.keys())

        with st.form("locked_student_form", clear_on_submit=True):
            selected_sid = st.selectbox(
                "🔒 Select Your Name & Roll Number (Unregistered Students Only) *",
                unreg_ids,
                format_func=lambda x: f"{x} — {all_students_map[x]}"
            )
            
            c1, c2 = st.columns(2)
            with c1:
                stu_skills = st.multiselect("Your Technical Skills *", ALL_SKILLS, default=["Frontend"])
                stu_interests = st.multiselect("Project Domain Interests *", ALL_INTERESTS, default=["Web"])
            with c2:
                stu_avail = st.multiselect("Your Available Days for Team Meetings *", ALL_DAYS, default=["Mon", "Wed"])

            st.markdown("#### 🤝 Optional: Partner Preferences (From Class Roster)")
            p1, p2 = st.columns(2)
            with p1:
                pref_friend = st.selectbox(
                    "💚 Preferred Teammate (+1 Graph Edge)",
                    ["None"] + all_roster_ids,
                    format_func=lambda x: f"{x} — {all_students_map[x]}" if x != "None" else "None (No Preference)"
                )
            with p2:
                pref_avoid = st.selectbox(
                    "🚫 Conflict / Prefer Not to Work With (-1 Graph Edge)",
                    ["None"] + all_roster_ids,
                    format_func=lambda x: f"{x} — {all_students_map[x]}" if x != "None" else "None (No Conflict)"
                )

            submit_btn = st.form_submit_button("✅ Lock & Submit My Profile", type="primary", use_container_width=True)
            if submit_btn:
                if not stu_skills or not stu_avail:
                    st.error("Please select at least one **Technical Skill** and at least one **Available Day**.")
                elif pref_friend != "None" and pref_friend == pref_avoid:
                    st.error("You cannot select the same classmate as both a Preferred Partner and a Conflict!")
                else:
                    register_student_submission(selected_sid, stu_skills, stu_interests, stu_avail, pref_friend, pref_avoid)
                    st.success(f"🔒 Profile locked for **{all_students_map[selected_sid]} ({selected_sid})**!")
                    st.rerun()


# ------------------------------------------
# TAB 2: PROFESSOR DASHBOARD & TEAM BUILDER
# ------------------------------------------
with tab_prof:
    if total_roster_count == 0:
        st.info("👈 Upload a **Class Roll-Call CSV** (`roll_no, name`) in the left sidebar to initialize your class.")
    else:
        # Registration Progress Bar & Roster Status Expander
        reg_ratio = len(registered_list) / total_roster_count
        st.progress(reg_ratio, text=f"📋 Class Registration Progress: {len(registered_list)} of {total_roster_count} Students Submitted ({reg_ratio*100:.0f}%)")
        
        with st.expander("👀 View Registered vs. Pending Students"):
            rc1, rc2 = st.columns(2)
            with rc1:
                st.markdown(f"**✅ Registered & Locked ({len(registered_list)})**")
                for sid, name, skills, _, avail in registered_list:
                    st.caption(f"• `{sid}` **{name}** — Skills: {', '.join(skills)} | Days: {', '.join(avail)}")
            with rc2:
                st.markdown(f"**⏳ Pending Submission ({len(unregistered_list)})**")
                for sid, name in unregistered_list:
                    st.caption(f"• `{sid}` {name}")

        if len(registered_list) < 2:
            st.warning("⏳ Waiting for at least **2 students** to complete their registration in Step 2 before teams can be formed.")
        else:
            required_skills = ["Frontend", "Backend", "AI/ML", "Database"]
            builder = TeamBuilder(required_skills, team_size=team_sz, skill_weight=skill_w, friend_weight=friend_w, schedule_weight=sched_w)

            for sid, name, skills, interests, avail in registered_list:
                builder.add_student(sid, name, skills, interests, avail)
            for u, v, w in edges_data:
                builder.add_preference(u, v, w)

            teams = builder.form_teams()

            # Top Metrics + CSV Export Button
            coverage_scores = []
            total_conflicts = 0
            for team in teams:
                t_skills = {s for sid in team for s in builder.students[sid]["skills"] if s in required_skills}
                coverage_scores.append((len(t_skills) / len(required_skills)) * 100)
                if any(builder.has_conflict(sid, team) for sid in team):
                    total_conflicts += 1

            avg_coverage = sum(coverage_scores) / max(1, len(coverage_scores))
            fairness = max(0.0, 100.0 - (max(coverage_scores) - min(coverage_scores))) if coverage_scores else 100.0

            k1, k2, k3, k4, k5 = st.columns([1.2, 1, 1, 1, 1.1])
            k1.metric("👥 Active Roster → Teams", f"{len(builder.students)} Students → {len(teams)} Teams")
            k2.metric("📊 Avg Skill Coverage", f"{avg_coverage:.1f}%")
            k3.metric("⚖️ Fairness Score", f"{fairness:.1f} / 100")
            k4.metric("🛡️ Conflict Status", "0 Conflicts" if total_conflicts == 0 else f"{total_conflicts} Conflict(s)!", delta="Optimal" if total_conflicts == 0 else "Action Needed", delta_color="normal" if total_conflicts == 0 else "inverse")

            # Generate Export CSV of Final Teams
            export_buffer = io.StringIO()
            writer = csv.writer(export_buffer)
            writer.writerow(["Team_Number", "Roll_No", "Student_Name", "Skills", "Interests", "Available_Days"])
            for idx, team in enumerate(teams, 1):
                for sid in team:
                    s = builder.students[sid]
                    writer.writerow([f"Team {idx}", sid, s["name"], ";".join(s["skills"]), ";".join(s["interests"]), ";".join(s["availability"])])
            
            with k5:
                st.write("")
                st.download_button(
                    label="📥 Export Final Teams CSV",
                    data=export_buffer.getvalue(),
                    file_name="final_formed_teams.csv",
                    mime="text/csv",
                    type="primary",
                    use_container_width=True
                )

            # Interactive Network Graph
            st.plotly_chart(plot_network_graph(builder, teams), use_container_width=True)

            # 2-Column Team Breakdown Cards
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
                            days_str = ", ".join(s_obj["availability"])
                            member_badges += f"<div style='margin:4px 0;'>• <b>{s_obj['name']}</b> (<code>{sid}</code>) — <span class='skill-badge'>{skills_str}</span> <span style='font-size:12px;color:gray;'>({days_str})</span></div>"

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

            # DSA Inspector at Bottom
            with st.expander("🔍 Inspect Underlying Data Structures & Execution Logs (DSA Viva Panel)"):
                tab1, tab2, tab3 = st.tabs(["📜 Draft & Swap Logs (Array)", "🕸️ Adjacency List (Graph)", "🗂️ Registered Profiles (Hash Map)"])
                with tab1:
                    st.code("\n".join(builder.logs), language="text")
                with tab2:
                    st.json(builder.preference_graph)
                with tab3:
                    st.json(builder.students)
