from datetime import date, timedelta
import pandas as pd
import streamlit as st
from supabase import create_client, Client
import httpx
import time

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Vaibhav's Habit, Fitness & Spaced Learning Hub",
    page_icon="⚡",
    layout="wide",
)

# ---------------------------------------------------------
# Validate & Initialize Supabase Connection
# ---------------------------------------------------------
if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
    st.error("⚠️ Credentials missing! Add SUPABASE_URL and SUPABASE_KEY to Streamlit Secrets.")
    st.stop()

@st.cache_resource
def get_supabase_client() -> Client:
    url = str(st.secrets["SUPABASE_URL"]).strip().rstrip("/")
    key = str(st.secrets["SUPABASE_KEY"]).strip()
    return create_client(url, key)

try:
    supabase = get_supabase_client()
except Exception as e:
    st.error(f"Failed to initialize Supabase client: {e}")
    st.stop()

# Helper for network resilience with automatic retry
def run_query(query_func, retries=2, delay=1):
    for attempt in range(retries + 1):
        try:
            return query_func()
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as net_err:
            if attempt < retries:
                time.sleep(delay)
                continue
            st.warning(f"Connection hiccup: {net_err}. Please refresh the page.")
            return None
        except Exception as e:
            st.error(f"Database error: {e}")
            return None

def fetch_table(table_name):
    res = run_query(lambda: supabase.table(table_name).select("*").execute())
    if res and res.data:
        return pd.DataFrame(res.data)
    return pd.DataFrame()

# ---------------------------------------------------------
# Global Constants & Schedules
# ---------------------------------------------------------
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

today_str = date.today().strftime("%Y-%m-%d")

st.title("⚡ Personal Habit, Fitness & Spaced Learning Hub")

main_tabs = st.tabs([
    "✅ Daily Checklist",
    "🥗 Food & Nutrition",
    "🏋️ Exercise & Burned Calories",
    "📚 CA Final & SPOM",
    "💡 Non-CA Learning",
    "📈 History & Stats"
])

# =========================================================
# TAB 1: DAILY RECURRING CHECKLIST
# =========================================================
with main_tabs[0]:
    st.subheader("Daily Recurring Task Checklist")
    selected_date = st.date_input("Checklist Date", value=date.today(), key="c_date")
    sel_date_str = selected_date.strftime("%Y-%m-%d")

    res = run_query(lambda: supabase.table("daily_tasks").select("*").eq("date", sel_date_str).execute())
    curr_tasks = pd.DataFrame(res.data) if res and res.data else pd.DataFrame()

    if curr_tasks.empty:
        new_entries = [{"date": sel_date_str, "task_name": t, "completed": False} for t in DEFAULT_RECURRING_TASKS]
        run_query(lambda: supabase.table("daily_tasks").insert(new_entries).execute())
        st.rerun()

    curr_tasks["completed"] = curr_tasks["completed"].fillna(False).astype(bool)

    edited_tasks = st.data_editor(
        curr_tasks,
        column_config={
            "task_id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
            "date": st.column_config.TextColumn("Date", disabled=True, width="small"),
            "task_name": st.column_config.TextColumn("Task Name (Click to edit)", required=True),
            "completed": st.column_config.CheckboxColumn("Done?"),
        },
        use_container_width=True,
        hide_index=True,
    )

    c_btn, c_stat = st.columns([1, 2])
    with c_btn:
        if st.button("Save Checklist Progress", type="primary", key="save_c_btn"):
            for _, row in edited_tasks.iterrows():
                run_query(lambda: supabase.table("daily_tasks").update({
                    "task_name": str(row["task_name"]).strip(),
                    "completed": bool(row["completed"])
                }).eq("task_id", int(row["task_id"])).execute())
            st.success("Checklist Updated!")
            st.rerun()

    with c_stat:
        tot_cnt = len(edited_tasks)
        fin_cnt = edited_tasks["completed"].sum() if tot_cnt > 0 else 0
        ratio = (fin_cnt / tot_cnt) if tot_cnt > 0 else 0.0
        st.progress(ratio, text=f"Progress: {fin_cnt}/{tot_cnt} completed ({int(ratio * 100)}%)")

# =========================================================
# TAB 2: FOOD & NUTRITION TRACKER
# =========================================================
with main_tabs[1]:
    st.subheader("Food, Caloric Intake & Micronutrients")
    c_f1, c_f2 = st.columns([1, 2])

    with c_f1:
        st.markdown("#### 🍽️ Log Meal")
        with st.form("food_form", clear_on_submit=True):
            f_date = st.date_input("Date", value=date.today())
            f_time = st.text_input("Meal Type / Time", value="Lunch", placeholder="e.g. Breakfast, Post-workout, 2 PM")
            f_item = st.text_input("Food Item(s)", placeholder="e.g. 2 Roti, Dhal, 100g Paneer")
            cal = st.number_input("Calories (kcal)", min_value=0.0, step=10.0)
            prot = st.number_input("Protein (g)", min_value=0.0, step=1.0)
            carbs = st.number_input("Carbs (g)", min_value=0.0, step=1.0)
            fat = st.number_input("Fat (g)", min_value=0.0, step=1.0)
            water = st.number_input("Water Drank (Liters)", min_value=0.0, max_value=10.0, step=0.25)
            micros = st.text_area("Micros / Supplements / Notes", placeholder="e.g. Multivitamin, 20g Fiber, Spinach")

            if st.form_submit_button("Record Meal", use_container_width=True):
                if f_item.strip():
                    run_query(lambda: supabase.table("food_log").insert({
                        "date": f_date.strftime("%Y-%m-%d"),
                        "time": f_time,
                        "meal_item": f_item.strip(),
                        "calories_kcal": cal,
                        "protein_g": prot,
                        "carbs_g": carbs,
                        "fat_g": fat,
                        "water_liters": water,
                        "micronutrients_notes": micros,
                    }).execute())
                    st.success("Meal Logged!")
                    st.rerun()
                else:
                    st.error("Please enter a food item description.")

    with c_f2:
        st.markdown("#### 📊 Today's Nutrition Overview")
        res_f = run_query(lambda: supabase.table("food_log").select("*").eq("date", today_str).execute())
        today_f = pd.DataFrame(res_f.data) if res_f and res_f.data else pd.DataFrame()

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Calories", f"{today_f['calories_kcal'].sum():.0f} kcal" if not today_f.empty else "0 kcal")
        m2.metric("Protein", f"{today_f['protein_g'].sum():.1f} g" if not today_f.empty else "0 g")
        m3.metric("Carbs", f"{today_f['carbs_g'].sum():.1f} g" if not today_f.empty else "0 g")
        m4.metric("Fat", f"{today_f['fat_g'].sum():.1f} g" if not today_f.empty else "0 g")
        m5.metric("Water", f"{today_f['water_liters'].sum():.2f} L" if not today_f.empty else "0 L")

        st.divider()
        if not today_f.empty:
            st.dataframe(
                today_f[["time", "meal_item", "calories_kcal", "protein_g", "carbs_g", "fat_g", "water_liters"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No meals logged yet for today.")

# =========================================================
# TAB 3: EXERCISE & CALORIES BURNED
# =========================================================
with main_tabs[2]:
    st.subheader("Exercise, Muscle Groups & Burned Calories")
    c_e1, c_e2 = st.columns([1, 2])

    with c_e1:
        st.markdown("#### 🏋️ Log Exercise")
        with st.form("ex_form", clear_on_submit=True):
            ex_date = st.date_input("Date", value=date.today())
            ex_name = st.text_input("Exercise Name", placeholder="e.g. Barbell Bench Press, Pull-ups")
            muscle = st.selectbox("Target Muscle Group", ["Chest", "Abs", "Arms", "Legs", "Shoulder", "Back", "Full Body / Cardio"])
            sets = st.number_input("Sets", min_value=1, max_value=20, value=3)
            reps = st.text_input("Reps", value="10-12")
            weight = st.number_input("Weight (kg)", min_value=0.0, step=2.5, value=0.0)
            c_burn = st.number_input("Estimated Burned (kcal)", min_value=0.0, step=25.0, value=150.0)
            notes = st.text_area("Form Notes / Intensity", placeholder="e.g. Pause reps, RPE 8")

            if st.form_submit_button("Record Exercise", use_container_width=True):
                if ex_name.strip():
                    run_query(lambda: supabase.table("exercise_log").insert({
                        "date": ex_date.strftime("%Y-%m-%d"),
                        "exercise_name": ex_name.strip(),
                        "muscle_group": muscle,
                        "sets": sets,
                        "reps_per_set": reps,
                        "weight_kg": weight,
                        "calories_burned_kcal": c_burn,
                        "notes": notes,
                    }).execute())
                    st.success("Exercise Logged!")
                    st.rerun()
                else:
                    st.error("Please enter an exercise name.")

    with c_e2:
        st.markdown("#### 📋 Workouts Logged Today")
        res_e = run_query(lambda: supabase.table("exercise_log").select("*").eq("date", today_str).execute())
        today_e = pd.DataFrame(res_e.data) if res_e and res_e.data else pd.DataFrame()

        tot_burn = today_e["calories_burned_kcal"].sum() if not today_e.empty else 0.0
        st.metric("Total Burned Today", f"{tot_burn:.0f} kcal")

        if not today_e.empty:
            st.dataframe(
                today_e[["exercise_name", "muscle_group", "sets", "reps_per_set", "weight_kg", "calories_burned_kcal"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No workout sessions logged yet for today.")

# =========================================================
# REVISION ENGINE SHARED COMPONENT (TABS 4 & 5)
# =========================================================
def render_cloud_revision(table_name, cat_options, cat_label, topic_label):
    df = fetch_table(table_name)
    today_dt = date.today()
    today_s = today_dt.strftime("%Y-%m-%d")

    # Due alert banner
    if not df.empty:
        alerts = []
        for r_name in REVISION_INTERVALS:
            pref = r_name.lower().split("_")[0]
            suf = r_name.split("_")[1]
            due_c = f"{pref}_due_{suf}"
            done_c = f"{pref}_done"
            if due_c in df.columns and done_c in df.columns:
                overdue = df[(df[due_c] <= today_s) & (~df[done_c].fillna(False).astype(bool))]
                if not overdue.empty:
                    alerts.append(f"**{r_name.replace('_', ' ')}** ({len(overdue)})")
        if alerts:
            st.warning("🚨 **Revisions Due Today / Overdue:** " + " | ".join(alerts))
        else:
            st.success("✅ All scheduled revisions are caught up!")

    c_s1, c_s2 = st.columns([1, 2])

    with c_s1:
        st.markdown(f"#### 📖 Add New {cat_label}")
        with st.form(f"form_{table_name}", clear_on_submit=True):
            s_date = st.date_input("Date Studied", value=date.today(), key=f"d_{table_name}")
            cat_val = st.selectbox(cat_label, cat_options)
            top_val = st.text_input(topic_label, placeholder="e.g. Chapter / Standard / Module")
            conf = st.select_slider("Confidence (1-5)", [1, 2, 3, 4, 5], value=3, key=f"cf_{table_name}")
            notes = st.text_area("Formulas / Notes / Pitfalls")

            calc_dues = {
                f"{r.lower().split('_')[0]}_due_{r.split('_')[1]}": (s_date + timedelta(days=d)).strftime("%Y-%m-%d")
                for r, d in REVISION_INTERVALS.items()
            }

            if st.form_submit_button("Add to Schedule", use_container_width=True):
                if top_val.strip():
                    new_entry = {
                        "date_studied": s_date.strftime("%Y-%m-%d"),
                        ("category" if table_name == "ca_spom_tracker" else "domain_topic"): cat_val,
                        ("topic_chapter" if table_name == "ca_spom_tracker" else "concepts_covered"): top_val.strip(),
                        "confidence_score": conf,
                        ("notes_difficult_points" if table_name == "ca_spom_tracker" else "application_notes"): notes,
                    }
                    for r in REVISION_INTERVALS:
                        pref = r.lower().split("_")[0]
                        suf = r.split("_")[1]
                        new_entry[f"{pref}_due_{suf}"] = calc_dues[f"{pref}_due_{suf}"]
                        new_entry[f"{pref}_done"] = False

                    run_query(lambda: supabase.table(table_name).insert(new_entry).execute())
                    st.success(f"Added '{top_val}' across all 6 revision intervals!")
                    st.rerun()
                else:
                    st.error("Please enter a topic or chapter name.")

    with c_s2:
        st.markdown("#### 🔄 Spaced Revision Interactive Checklist")
        if not df.empty:
            for r in ["r1", "r2", "r3", "r4", "r5", "r6"]:
                df[f"{r}_done"] = df[f"{r}_done"].fillna(False).astype(bool)

            col_cfgs = {
                "item_id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "date_studied": st.column_config.DateColumn("Studied", disabled=True),
                "category": st.column_config.TextColumn("Subject/Set"),
                "domain_topic": st.column_config.TextColumn("Domain"),
                "topic_chapter": st.column_config.TextColumn("Chapter/Topic"),
                "concepts_covered": st.column_config.TextColumn("Concepts"),
                "confidence_score": st.column_config.NumberColumn("Conf (1-5)", min_value=1, max_value=5),
            }

            for r, d in zip(["r1", "r2", "r3", "r4", "r5", "r6"], ["3d", "7d", "15d", "30d", "90d", "180d"]):
                col_cfgs[f"{r}_due_{d}"] = st.column_config.DateColumn(f"{r.upper()} (+{d})", disabled=True)
                col_cfgs[f"{r}_done"] = st.column_config.CheckboxColumn(f"{r.upper()}?")

            edited_df = st.data_editor(
                df.sort_values(by="item_id", ascending=False),
                column_config=col_cfgs,
                use_container_width=True,
                hide_index=True,
            )

            if st.button("Save Revisions to Cloud", type="primary", key=f"btn_{table_name}"):
                for _, row in edited_df.iterrows():
                    update_dict = {f"{r}_done": bool(row[f"{r}_done"]) for r in ["r1", "r2", "r3", "r4", "r5", "r6"]}
                    update_dict["confidence_score"] = int(row["confidence_score"])
                    run_query(lambda r_id=row["item_id"], u_dict=update_dict: supabase.table(table_name).update(u_dict).eq("item_id", int(r_id)).execute())
                st.success("Revisions Saved!")
                st.rerun()
        else:
            st.info("No study chapters logged yet.")

# =========================================================
# TAB 4: CA FINAL & SPOM TRACKER
# =========================================================
with main_tabs[3]:
    st.subheader("CA Final & SPOM Study & Revision Log")
    ca_papers = [
        "Paper 1: Financial Reporting (FR)",
        "Paper 2: Advanced Financial Management (AFM)",
        "Paper 3: Advanced Auditing & Professional Ethics",
        "Paper 4: Direct Tax Laws & International Taxation",
        "Paper 5: Indirect Tax Laws (IDT)",
        "Paper 6: Integrated Business Solutions (IBS)",
        "SPOM Set A: Corporate and Economic Laws",
        "SPOM Set B: Strategic Cost & Performance Management (SCPM)",
    ]
    render_cloud_revision("ca_spom_tracker", ca_papers, "Paper / SPOM Set", "Chapter / Standard / Case")

# =========================================================
# TAB 5: NON-CA LEARNING TRACKER
# =========================================================
with main_tabs[4]:
    st.subheader("Non-CA Learning & Upskilling Log")
    skills = [
        "Python / Automation / Scripting",
        "Internal Audit Governance & ICAI Standards",
        "SAP T-Codes & Enterprise ERP",
        "Financial Modeling / Excel / Power Query",
        "Communication / Soft Skills",
        "Other",
    ]
    render_cloud_revision("other_learning", skills, "Domain / Field", "Skill, Code Library, or Concept")

# =========================================================
# TAB 6: HISTORY & AGGREGATIONS
# =========================================================
with main_tabs[5]:
    st.subheader("📈 Multi-Domain History & Performance Summaries")

    f_all = fetch_table("food_log")
    e_all = fetch_table("exercise_log")
    t_all = fetch_table("daily_tasks")
    s_all = fetch_table("ca_spom_tracker")
    o_all = fetch_table("other_learning")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Meals Logged", len(f_all))
    c2.metric("Workouts Logged", len(e_all))
    c3.metric("Tasks Completed", len(t_all[t_all["completed"] == True]) if not t_all.empty else 0)
    c4.metric("Study Modules Tracked", len(s_all) + len(o_all))

    sub_h1, sub_h2, sub_h3 = st.tabs(["📅 Daily Log History", "📊 Weekly Summary", "🗓️ Monthly Summary"])

    # Ensure Date parsing for all tables
    for d in [f_all, e_all, t_all, s_all, o_all]:
        if not d.empty and "date" in d.columns:
            d["Date_DT"] = pd.to_datetime(d["date"], errors="coerce")
        elif not d.empty and "date_studied" in d.columns:
            d["Date_DT"] = pd.to_datetime(d["date_studied"], errors="coerce")

    with sub_h1:
        st.markdown("#### Raw Logs by Date")
        h_date = st.date_input("Filter Date", value=date.today(), key="h_raw_date")
        h_s = h_date.strftime("%Y-%m-%d")

        c_l, c_r = st.columns(2)
        with c_l:
            st.markdown("##### 🥗 Nutrition")
            df_f_h = f_all[f_all["date"] == h_s] if not f_all.empty else pd.DataFrame()
            if not df_f_h.empty:
                st.dataframe(df_f_h[["time", "meal_item", "calories_kcal", "protein_g", "water_liters"]], use_container_width=True, hide_index=True)
            else:
                st.caption("No food records.")

            st.markdown("##### 🏋️ Workouts")
            df_e_h = e_all[e_all["date"] == h_s] if not e_all.empty else pd.DataFrame()
            if not df_e_h.empty:
                st.dataframe(df_e_h[["exercise_name", "muscle_group", "sets", "reps_per_set", "calories_burned_kcal"]], use_container_width=True, hide_index=True)
            else:
                st.caption("No workout records.")

        with c_r:
            st.markdown("##### ✅ Tasks Completed")
            df_t_h = t_all[t_all["date"] == h_s] if not t_all.empty else pd.DataFrame()
            if not df_t_h.empty:
                st.dataframe(df_t_h[["task_name", "completed"]], use_container_width=True, hide_index=True)
            else:
                st.caption("No task records.")

            st.markdown("##### 📚 Study Sessions")
            df_s_h = s_all[s_all["date_studied"] == h_s] if not s_all.empty else pd.DataFrame()
            if not df_s_h.empty:
                st.dataframe(df_s_h[["category", "topic_chapter", "confidence_score"]], use_container_width=True, hide_index=True)
            else:
                st.caption("No study records.")

    def aggregate_by_period(period_fmt):
        all_dts = []
        for d in [f_all, e_all, t_all, s_all, o_all]:
            if not d.empty and "Date_DT" in d.columns:
                all_dts.extend(d["Date_DT"].dropna().tolist())
        if not all_dts:
            return pd.DataFrame()

        base = pd.DataFrame({"Date_DT": pd.date_range(min(all_dts), max(all_dts), freq="D")})
        base["Period"] = base["Date_DT"].dt.strftime(period_fmt)

        # Aggregate Food
        if not f_all.empty and "Date_DT" in f_all.columns:
            f_cp = f_all.copy()
            f_cp["Period"] = f_cp["Date_DT"].dt.strftime(period_fmt)
            f_agg = f_cp.groupby("Period")[["calories_kcal", "protein_g", "water_liters"]].sum().reset_index()
        else:
            f_agg = pd.DataFrame(columns=["Period", "calories_kcal", "protein_g", "water_liters"])

        # Aggregate Exercise
        if not e_all.empty and "Date_DT" in e_all.columns:
            e_cp = e_all.copy()
            e_cp["Period"] = e_cp["Date_DT"].dt.strftime(period_fmt)
            e_agg = e_cp.groupby("Period").agg(calories_burned_kcal=("calories_burned_kcal", "sum"), total_workouts=("log_id", "count")).reset_index()
        else:
            e_agg = pd.DataFrame(columns=["Period", "calories_burned_kcal", "total_workouts"])

        # Aggregate Tasks
        if not t_all.empty and "Date_DT" in t_all.columns:
            t_cp = t_all.copy()
            t_cp["Period"] = t_cp["Date_DT"].dt.strftime(period_fmt)
            t_cp["completed"] = t_cp["completed"].fillna(False).astype(bool)
            t_agg = t_cp.groupby("Period").agg(tasks_done=("completed", "sum"), total_tasks=("task_id", "count")).reset_index()
        else:
            t_agg = pd.DataFrame(columns=["Period", "tasks_done", "total_tasks"])

        # Aggregate Study
        if not s_all.empty and "Date_DT" in s_all.columns:
            s_cp = s_all.copy()
            s_cp["Period"] = s_cp["Date_DT"].dt.strftime(period_fmt)
            s_agg = s_cp.groupby("Period")["item_id"].count().reset_index().rename(columns={"item_id": "ca_topics_studied"})
        else:
            s_agg = pd.DataFrame(columns=["Period", "ca_topics_studied"])

        periods = pd.DataFrame({"Period": sorted(base["Period"].unique(), reverse=True)})
        summary = periods.merge(f_agg, on="Period", how="left").merge(e_agg, on="Period", how="left").merge(t_agg, on="Period", how="left").merge(s_agg, on="Period", how="left").fillna(0)
        summary["net_calories"] = summary["calories_kcal"] - summary["calories_burned_kcal"]
        return summary

    with sub_h2:
        st.markdown("#### Weekly Summary (Year-Week)")
        weekly = aggregate_by_period("%Y-W%U")
        if not weekly.empty:
            st.dataframe(
                weekly.style.format({
                    "calories_kcal": "{:.0f}",
                    "calories_burned_kcal": "{:.0f}",
                    "net_calories": "{:.0f}",
                    "protein_g": "{:.1f}",
                    "water_liters": "{:.1f}",
                    "total_workouts": "{:.0f}",
                    "tasks_done": "{:.0f}",
                    "total_tasks": "{:.0f}",
                    "ca_topics_studied": "{:.0f}",
                }),
                use_container_width=True,
                hide_index=True,
            )
            st.line_chart(weekly.set_index("Period")[["calories_kcal", "calories_burned_kcal", "net_calories"]])
        else:
            st.info("No records to aggregate weekly.")

    with sub_h3:
        st.markdown("#### Monthly Summary (Year-Month)")
        monthly = aggregate_by_period("%Y-%m")
        if not monthly.empty:
            st.dataframe(
                monthly.style.format({
                    "calories_kcal": "{:.0f}",
                    "calories_burned_kcal": "{:.0f}",
                    "net_calories": "{:.0f}",
                    "protein_g": "{:.1f}",
                    "water_liters": "{:.1f}",
                    "total_workouts": "{:.0f}",
                    "tasks_done": "{:.0f}",
                    "total_tasks": "{:.0f}",
                    "ca_topics_studied": "{:.0f}",
                }),
                use_container_width=True,
                hide_index=True,
            )
            st.bar_chart(monthly.set_index("Period")[["protein_g", "total_workouts", "ca_topics_studied"]])
        else:
            st.info("No records to aggregate monthly.")
