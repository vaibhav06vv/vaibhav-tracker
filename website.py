from datetime import date, timedelta
import pandas as pd
import streamlit as st
from supabase import create_client, Client

st.set_page_config(
    page_title="Vaibhav's Life & Revision Hub",
    page_icon="⚡",
    layout="wide",
)

# Connect to Supabase
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase_client()

DEFAULT_RECURRING_TASKS = [
    "Wake up by 05:30 AM & Hydrate",
    "Morning CA Study / Revision (1.5 hrs)",
    "Exercise / Workout Session (45 mins)",
    "Clean Nutrition & Track All Meals",
    "Articleship / Office Priorities Completed",
    "Evening Learning / Non-CA Skill (30 mins)",
    "Review Pending SRS Revisions for Tomorrow",
    "Screen-off by 10:45 PM & Sleep by 11:00 PM",
]

REVISION_INTERVALS = {
    "R1_3d": 3,
    "R2_7d": 7,
    "R3_15d": 15,
    "R4_30d": 30,
    "R5_90d": 90,
    "R6_180d": 180,
}

# Database Helpers
def fetch_table(table_name):
    res = supabase.table(table_name).select("*").execute()
    df = pd.DataFrame(res.data)
    return df

st.title("⚡ Personal Habit, Fitness & Spaced Learning Hub")

main_tabs = st.tabs([
    "✅ Daily Checklist",
    "🥗 Food & Nutrition",
    "🏋️ Exercise & Burned Calories",
    "📚 CA Final & SPOM",
    "💡 Non-CA Learning",
    "📈 History & Stats"
])

today_str = date.today().strftime("%Y-%m-%d")

# =========================================================
# 1. DAILY CHECKLIST
# =========================================================
with main_tabs[0]:
    st.subheader("Daily Recurring Task Checklist")
    selected_date = st.date_input("Checklist Date", value=date.today(), key="c_date")
    sel_date_str = selected_date.strftime("%Y-%m-%d")

    res = supabase.table("daily_tasks").select("*").eq("date", sel_date_str).execute()
    curr_tasks = pd.DataFrame(res.data)

    if curr_tasks.empty:
        new_entries = [{"date": sel_date_str, "task_name": t, "completed": False} for t in DEFAULT_RECURRING_TASKS]
        supabase.table("daily_tasks").insert(new_entries).execute()
        st.rerun()

    curr_tasks["completed"] = curr_tasks["completed"].fillna(False).astype(bool)

    edited = st.data_editor(
        curr_tasks,
        column_config={
            "task_id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
            "date": st.column_config.TextColumn("Date", disabled=True, width="small"),
            "task_name": st.column_config.TextColumn("Task Name", required=True),
            "completed": st.column_config.CheckboxColumn("Done?"),
        },
        use_container_width=True,
        hide_index=True,
    )

    if st.button("Save Checklist Progress", type="primary"):
        for _, row in edited.iterrows():
            supabase.table("daily_tasks").update({
                "task_name": row["task_name"],
                "completed": bool(row["completed"])
            }).eq("task_id", int(row["task_id"])).execute()
        st.success("Checklist Updated!")
        st.rerun()

# =========================================================
# 2. FOOD TRACKER
# =========================================================
with main_tabs[1]:
    st.subheader("Food, Caloric Intake & Micronutrients")
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("food_form", clear_on_submit=True):
            f_date = st.date_input("Date", value=date.today())
            f_time = st.text_input("Meal Type", value="Lunch")
            f_item = st.text_input("Food Item", placeholder="e.g. 2 Roti, Dhal, Paneer")
            cal = st.number_input("Calories (kcal)", min_value=0.0, step=10.0)
            prot = st.number_input("Protein (g)", min_value=0.0, step=1.0)
            carbs = st.number_input("Carbs (g)", min_value=0.0, step=1.0)
            fat = st.number_input("Fat (g)", min_value=0.0, step=1.0)
            water = st.number_input("Water (Liters)", min_value=0.0, max_value=10.0, step=0.25)
            micros = st.text_area("Micros / Notes")

            if st.form_submit_button("Save Meal", use_container_width=True):
                if f_item.strip():
                    supabase.table("food_log").insert({
                        "date": f_date.strftime("%Y-%m-%d"), "time": f_time, "meal_item": f_item,
                        "calories_kcal": cal, "protein_g": prot, "carbs_g": carbs, "fat_g": fat,
                        "water_liters": water, "micronutrients_notes": micros
                    }).execute()
                    st.success("Meal Logged!")
                    st.rerun()

    with c2:
        res_f = supabase.table("food_log").select("*").eq("date", today_str).execute()
        today_f = pd.DataFrame(res_f.data)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Calories Today", f"{today_f['calories_kcal'].sum():.0f} kcal" if not today_f.empty else "0")
        m2.metric("Protein", f"{today_f['protein_g'].sum():.1f} g" if not today_f.empty else "0")
        m3.metric("Carbs", f"{today_f['carbs_g'].sum():.1f} g" if not today_f.empty else "0")
        m4.metric("Fat", f"{today_f['fat_g'].sum():.1f} g" if not today_f.empty else "0")
        if not today_f.empty:
            st.dataframe(today_f[["time", "meal_item", "calories_kcal", "protein_g", "water_liters"]], use_container_width=True, hide_index=True)

# =========================================================
# 3. EXERCISE TRACKER
# =========================================================
with main_tabs[2]:
    st.subheader("Exercise & Burned Calories")
    e1, e2 = st.columns([1, 2])
    with e1:
        with st.form("ex_form", clear_on_submit=True):
            ex_date = st.date_input("Date", value=date.today())
            ex_name = st.text_input("Exercise Name")
            muscle = st.selectbox("Muscle Group", ["Chest", "Abs", "Arms", "Legs", "Shoulder", "Back", "Full Body / Cardio"])
            sets = st.number_input("Sets", min_value=1, value=3)
            reps = st.text_input("Reps", value="10-12")
            weight = st.number_input("Weight (kg)", min_value=0.0, step=2.5)
            c_burn = st.number_input("Burned (kcal)", min_value=0.0, step=25.0, value=150.0)
            notes = st.text_area("Notes")

            if st.form_submit_button("Log Exercise", use_container_width=True):
                if ex_name.strip():
                    supabase.table("exercise_log").insert({
                        "date": ex_date.strftime("%Y-%m-%d"), "exercise_name": ex_name.strip(),
                        "muscle_group": muscle, "sets": sets, "reps_per_set": reps, "weight_kg": weight,
                        "calories_burned_kcal": c_burn, "notes": notes
                    }).execute()
                    st.success("Exercise Saved!")
                    st.rerun()

    with e2:
        res_e = supabase.table("exercise_log").select("*").eq("date", today_str).execute()
        today_e = pd.DataFrame(res_e.data)
        st.metric("Burned Today", f"{today_e['calories_burned_kcal'].sum():.0f} kcal" if not today_e.empty else "0 kcal")
        if not today_e.empty:
            st.dataframe(today_e[["exercise_name", "muscle_group", "sets", "reps_per_set", "calories_burned_kcal"]], use_container_width=True, hide_index=True)

# =========================================================
# 4 & 5. SPACED REPETITION ENGINE
# =========================================================
def render_study_tab(table_name, cat_list, cat_label, top_label):
    c_in, c_board = st.columns([1, 2])
    with c_in:
        with st.form(f"study_{table_name}", clear_on_submit=True):
            s_date = st.date_input("Date Studied", value=date.today(), key=f"s_{table_name}")
            cat_val = st.selectbox(cat_label, cat_list)
            top_val = st.text_input(top_label)
            conf = st.select_slider("Confidence", [1, 2, 3, 4, 5], value=3, key=f"cf_{table_name}")
            notes = st.text_area("Formulas / Notes")

            calc_dues = {f"{r.lower()}_due_{r.split('_')[1]}": (s_date + timedelta(days=d)).strftime("%Y-%m-%d") for r, d in REVISION_INTERVALS.items()}

            if st.form_submit_button("Add Chapter to Schedule", use_container_width=True):
                if top_val.strip():
                    row = {
                        "date_studied": s_date.strftime("%Y-%m-%d"),
                        ("category" if table_name == "ca_spom_tracker" else "domain_topic"): cat_val,
                        ("topic_chapter" if table_name == "ca_spom_tracker" else "concepts_covered"): top_val.strip(),
                        "confidence_score": conf,
                        ("notes_difficult_points" if table_name == "ca_spom_tracker" else "application_notes"): notes,
                    }
                    for r in REVISION_INTERVALS:
                        pref, suf = r.lower().split("_")[0], r.split("_")[1]
                        row[f"{pref}_due_{suf}"] = calc_dues[f"{pref}_due_{suf}"]
                        row[f"{pref}_done"] = False
                    supabase.table(table_name).insert(row).execute()
                    st.success("Scheduled across 3d, 7d, 15d, 30d, 90d, 180d!")
                    st.rerun()

    with c_board:
        df = fetch_table(table_name)
        if not df.empty:
            for r in ["r1", "r2", "r3", "r4", "r5", "r6"]:
                df[f"{r}_done"] = df[f"{r}_done"].fillna(False).astype(bool)

            cfgs = {
                "item_id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "date_studied": st.column_config.DateColumn("Studied", disabled=True),
            }
            for r, d in zip(["r1", "r2", "r3", "r4", "r5", "r6"], ["3d", "7d", "15d", "30d", "90d", "180d"]):
                cfgs[f"{r}_due_{d}"] = st.column_config.DateColumn(f"{r.upper()} (+{d})", disabled=True)
                cfgs[f"{r}_done"] = st.column_config.CheckboxColumn(f"{r.upper()}?")

            edited = st.data_editor(
                df.sort_values(by="item_id", ascending=False),
                column_config=cfgs,
                use_container_width=True,
                hide_index=True,
            )
            if st.button("Save Revisions Progress", type="primary", key=f"btn_{table_name}"):
                for _, row in edited.iterrows():
                    supabase.table(table_name).update({
                        f"{r}_done": bool(row[f"{r}_done"]) for r in ["r1", "r2", "r3", "r4", "r5", "r6"]
                    }).eq("item_id", int(row["item_id"])).execute()
                st.success("Progress Saved!")
                st.rerun()
        else:
            st.info("No study chapters logged yet.")

with main_tabs[3]:
    st.subheader("CA Final & SPOM Study & Revision Log")
    ca_papers = ["Paper 1: FR", "Paper 2: AFM", "Paper 3: Advanced Auditing", "Paper 4: Direct Tax", "Paper 5: IDT", "Paper 6: IBS", "SPOM Set A: Law", "SPOM Set B: SCPM"]
    render_study_tab("ca_spom_tracker", ca_papers, "Paper / SPOM Set", "Chapter / Standard")

with main_tabs[4]:
    st.subheader("Non-CA Learning Log")
    skills = ["Python / Automation", "Internal Audit Standards", "SAP ERP", "Financial Modeling", "Soft Skills", "Other"]
    render_study_tab("other_learning", skills, "Domain", "Skill / Concept")

# =========================================================
# 6. HISTORY & STATS
# =========================================================
with main_tabs[5]:
    st.subheader("📈 Performance & History Summaries")
    f_all = fetch_table("food_log")
    e_all = fetch_table("exercise_log")
    t_all = fetch_table("daily_tasks")
    s_all = fetch_table("ca_spom_tracker")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Meals Logged", len(f_all))
    k2.metric("Workouts Logged", len(e_all))
    k3.metric("Tasks Completed", len(t_all[t_all["completed"] == True]) if not t_all.empty else 0)
    k4.metric("CA Chapters Scheduled", len(s_all))
