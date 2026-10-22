class TeamBuilder:
    def __init__(self, required_skills, team_size, friend_weight=6, debug=True):
        # ARRAY: List of skills every team needs
        self.required_skills = required_skills
        self.team_size = team_size
        self.friend_weight = friend_weight  # Controls how strongly friends pull together
        self.debug = debug                  # Turns troubleshooting logs ON or OFF
        
        # HASH MAP: student_id -> student profile dict
        self.students = {}
        
        # GRAPH (Adjacency List): student_id -> {other_student_id: +1 or -1}
        self.preference_graph = {}

    def log(self, message):
        """Helper to print debug steps only when self.debug is True."""
        if self.debug:
            print(f"[DEBUG] {message}")

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
        """weight: +1 (want to work together) or -1 (conflict/avoid)"""
        self.preference_graph[student_a][student_b] = weight

    def has_conflict(self, candidate_id, team):
        """Checks the Graph to see if candidate has a -1 edge with anyone in the team."""
        for member_id in team:
            if member_id == candidate_id:
                continue
            edge_a_to_b = self.preference_graph[candidate_id].get(member_id, 0)
            edge_b_to_a = self.preference_graph[member_id].get(candidate_id, 0)
            if edge_a_to_b == -1 or edge_b_to_a == -1:
                return True
        return False

    def calculate_fit_score(self, candidate_id, current_team):
        """Scores how well a candidate fits into a team."""
        candidate = self.students[candidate_id]
        
        # ROUND 1 (Empty Team): Pick strong 'anchor' students first.
        # BUG FIX 2: If a student has a +1 friend waiting in the pool, slightly 
        # delay picking them as a Round 1 captain so they stay free to join their friend!
        if not current_team:
            useful_skills = [s for s in candidate["skills"] if s in self.required_skills]
            has_friends = any(w == 1 for w in self.preference_graph[candidate_id].values())
            friend_holdback = -2 if has_friends else 0
            return (len(useful_skills) * 10) + friend_holdback

        # Check hard conflict first using our helper
        if self.has_conflict(candidate_id, current_team):
            return -999

        team_skills = set()
        for member_id in current_team:
            team_skills.update(self.students[member_id]["skills"])

        score = 0

        # 1. Graph Preferences (Friends bonus)
        for member_id in current_team:
            edge_a_to_b = self.preference_graph[candidate_id].get(member_id, 0)
            edge_b_to_a = self.preference_graph[member_id].get(candidate_id, 0)
            score += (edge_a_to_b + edge_b_to_a) * self.friend_weight

        # 2. Skill Gaps (+10 for new required skill, -3 penalty for overlapping skill)
        for skill in candidate["skills"]:
            if skill in self.required_skills:
                if skill not in team_skills:
                    score += 10
                else:
                    score -= 3  # Stronger overlap penalty keeps same-skill friends apart

        # 3. Schedule & Interest Match
        for member_id in current_team:
            member = self.students[member_id]
            shared_time = set(candidate["availability"]).intersection(member["availability"])
            shared_interest = set(candidate["interests"]).intersection(member["interests"])
            score += len(shared_time) * 2
            score += len(shared_interest) * 3

        return score

    def resolve_conflicts(self, teams):
        """BUG FIX 1: Post-draft swap step to fix any forced -999 conflicts."""
        for t1_idx, team1 in enumerate(teams):
            for s1 in list(team1):
                if self.has_conflict(s1, team1):
                    self.log(f"⚠️ Conflict detected! {self.students[s1]['name']} ({s1}) has a conflict in Team {t1_idx + 1}.")
                    
                    # Look for a safe swap partner in another team
                    swapped = False
                    for t2_idx, team2 in enumerate(teams):
                        if t1_idx == t2_idx:
                            continue
                        for s2 in list(team2):
                            # Simulate swapping s1 and s2
                            temp_team1 = [m for m in team1 if m != s1]
                            temp_team2 = [m for m in team2 if m != s2]
                            
                            # Check if BOTH teams are conflict-free after the swap
                            if not self.has_conflict(s2, temp_team1) and not self.has_conflict(s1, temp_team2):
                                team1.remove(s1)
                                team2.remove(s2)
                                team1.append(s2)
                                team2.append(s1)
                                self.log(f"✅ Fixed! Swapped {self.students[s1]['name']} (Team {t1_idx+1}) with {self.students[s2]['name']} (Team {t2_idx+1}).")
                                swapped = True
                                break
                        if swapped:
                            break
                    if not swapped:
                        self.log(f"❌ Could not find a valid swap for {self.students[s1]['name']}. Constraints are too tight!")

    def form_teams(self):
        """Drafts students round-by-round, then runs conflict resolution."""
        unassigned = set(self.students.keys())
        num_teams = (len(self.students) + self.team_size - 1) // self.team_size
        teams = [[] for _ in range(num_teams)]

        for round_num in range(1, self.team_size + 1):
            self.log(f"--- Starting Draft Round {round_num} ---")
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
                    if best_score == -999:
                        self.log(f"⚠️ Forced to place {self.students[best_candidate]['name']} into Team {team_idx+1} despite conflict (last option left).")
                    else:
                        self.log(f"Team {team_idx+1} drafted {self.students[best_candidate]['name']} (Fit Score: {best_score})")
                    
                    team.append(best_candidate)
                    unassigned.remove(best_candidate)

        # Run our bug-fix swap step after initial teams are formed
        self.resolve_conflicts(teams)
        return teams

    def evaluate_teams(self, teams):
        """Prints the final report."""
        coverage_scores = []
        print("\n=== FINAL TEAM FORMATION REPORT ===\n")

        for i, team in enumerate(teams, 1):
            names = [self.students[sid]["name"] for sid in team]
            skill_counts = {}
            for sid in team:
                for skill in self.students[sid]["skills"]:
                    skill_counts[skill] = skill_counts.get(skill, 0) + 1

            missing = [s for s in self.required_skills if s not in skill_counts]
            overlaps = [s for s, count in skill_counts.items() if count > 1]
            
            coverage_pct = ((len(self.required_skills) - len(missing)) / len(self.required_skills)) * 100
            coverage_scores.append(coverage_pct)

            # Verify no conflicts remain
            team_conflict = any(self.has_conflict(sid, team) for sid in team)

            print(f"Team {i}: {names}")
            print(f"  - Covered Skills:     {list(skill_counts.keys())}")
            print(f"  - Missing Skills:     {missing if missing else 'None (100% Covered!)'}")
            print(f"  - Overlapping Skills: {overlaps if overlaps else 'None'}")
            print(f"  - Conflict Status:    {'⚠️ CONFLICT PRESENT' if team_conflict else 'Clean (No Conflicts)'}")
            print(f"  - Skill Coverage:     {coverage_pct:.1f}%\n")

        avg_coverage = sum(coverage_scores) / len(coverage_scores)
        fairness = max(0.0, 100.0 - (max(coverage_scores) - min(coverage_scores)))
        print(f"Overall Average Coverage: {avg_coverage:.1f}% | Fairness Score: {fairness:.1f}/100")


# ==========================================
# TEST CASE: Triggering and Fixing Both Bugs
# ==========================================
if __name__ == "__main__":
    required = ["Frontend", "Backend", "AI/ML", "Database"]
    builder = TeamBuilder(required_skills=required, team_size=3, friend_weight=6, debug=True)

    # 6 Students
    builder.add_student("S1", "Aarav",  ["Frontend", "UI/UX"],   ["Web", "EdTech"],  ["Mon", "Wed"])
    builder.add_student("S2", "Bhavya", ["Backend", "Database"], ["Web", "FinTech"], ["Mon", "Fri"])
    builder.add_student("S3", "Charan", ["AI/ML"],               ["EdTech", "Health"],["Mon", "Wed"])
    builder.add_student("S4", "Diya",   ["Frontend", "Backend"], ["Health", "AI"],   ["Tue", "Thu"])
    builder.add_student("S5", "Eshan",  ["AI/ML", "Database"],   ["Health", "Web"],  ["Tue", "Thu"])
    builder.add_student("S6", "Farah",  ["Frontend"],            ["Web", "EdTech"],  ["Tue", "Thu"])

    # Case 1 (Overlapping Friends): S1 (Frontend) and S6 (Frontend) are friends.
    # Should STILL be separated because both only do Frontend.
    builder.add_preference("S1", "S6", 1)
    builder.add_preference("S6", "S1", 1)

    # Case 2 (Complementary Friends): S1 (Frontend) and S3 (AI/ML) are friends.
    # Should be put TOGETHER because their skills complement each other!
    builder.add_preference("S1", "S3", 1)
    builder.add_preference("S3", "S1", 1)

    # Case 3 (Hard Conflict Trap): S6 has a conflict with Eshan (S5) AND Diya (S4)
    builder.add_preference("S6", "S5", -1)
    builder.add_preference("S6", "S4", -1)

    formed_teams = builder.form_teams()
    builder.evaluate_teams(formed_teams)
