from datetime import date, timedelta
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(
    page_title="Vaibhav's Life & Revision Hub",
    page_icon="⚡",
    layout="wide",
)

# Connect to Google Sheets via Streamlit Connector
conn = st.connection("gsheets", type=GSheetsConnection)

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

SHEET_CONFIGS = {
    "Daily_Tasks": ["Task_ID", "Date", "Task_Name", "Completed"],
    "Food_Log": ["Entry_ID", "Date", "Time", "Meal_Item", "Calories_kcal", "Protein_g", "Carbs_g", "Fat_g", "Water_Liters", "Micronutrients_Notes"],
    "Exercise_Log": ["Log_ID", "Date", "Exercise_Name", "Muscle_Group", "Sets", "Reps_Per_Set", "Weight_kg", "Calories_Burned_kcal", "Notes"],
    "CA_SPOM_Tracker": ["Item_ID", "Date_Studied", "Category", "Topic_Chapter", "R1_Due_3d", "R1_Done", "R2_Due_7d", "R2_Done", "R3_Due_15d", "R3_Done", "R4_Due_30d", "R4_Done", "R5_Due_90d", "R5_Done", "R6_Due_180d", "R6_Done", "Confidence_Score", "Notes_Difficult_Points"],
    "Other_Learning": ["Item_ID", "Date_Studied", "Domain_Topic", "Concepts_Covered", "R1_Due_3d", "R1_Done", "R2_Due_7d", "R2_Done", "R3_Due_15d", "R3_Done", "R4_Due_30d", "R4_Done", "R5_Due_90d", "R5_Done", "R6_Due_180d", "R6_Done", "Application_Notes"],
}

def load_sheet(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl="0s")
        if df is None or df.empty:
            return pd.DataFrame(columns=SHEET_CONFIGS[sheet_name])
        for c in SHEET_CONFIGS[sheet_name]:
            if c not in df.columns:
                df[c] = None
        return df.dropna(how="all")
    except Exception:
        return pd.DataFrame(columns=SHEET_CONFIGS[sheet_name])

def save_sheet(df, sheet_name):
    conn.update(worksheet=sheet_name, data=df)

st.title("⚡ Personal Habit, Fitness & Spaced Learning Hub")

main_tabs = st.tabs([
    "✅ Daily Checklist",
    "🥗 Food & Nutrition",
    "🏋️ Exercise & Calories Burned",
    "📚 CA Final & SPOM",
    "💡 Non-CA Learning",
    "📈 History & Aggregations"
])

today_str = date.today().strftime("%Y-%m-%d")

# 1. DAILY CHECKLIST
with main_tabs[0]:
    st.subheader("Daily Recurring Task Checklist")
    selected_date = st.date_input("Checklist Date", value=date.today(), key="c_date")
    sel_date_str = selected_date.strftime("%Y-%m-%d")

    df_tasks = load_sheet("Daily_Tasks")
    if not df_tasks.empty:
        df_tasks["Completed"] = df_tasks["Completed"].fillna(False).astype(bool)

    curr_tasks = df_tasks[df_tasks["Date"] == sel_date_str].copy() if not df_tasks.empty else pd.DataFrame(columns=SHEET_CONFIGS["Daily_Tasks"])

    if curr_tasks.empty:
        st.info(f"Populating recurring habits for {sel_date_str}...")
        start_id = int(df_tasks["Task_ID"].max() + 1) if not df_tasks.empty and pd.notnull(df_tasks["Task_ID"].max()) else 1
        new_entries = [{"Task_ID": start_id + i, "Date": sel_date_str, "Task_Name": t, "Completed": False} for i, t in enumerate(DEFAULT_RECURRING_TASKS)]
        curr_tasks = pd.DataFrame(new_entries)
        df_tasks = pd.concat([df_tasks, curr_tasks], ignore_index=True)
        save_sheet(df_tasks, "Daily_Tasks")

    edited_tasks = st.data_editor(
        curr_tasks,
        column_config={
            "Task_ID": st.column_config.NumberColumn("ID", disabled=True, width="small"),
            "Date": st.column_config.TextColumn("Date", disabled=True, width="small"),
            "Task_Name": st.column_config.TextColumn("Task Name (Editable)", required=True),
            "Completed": st.column_config.CheckboxColumn("Done?"),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
    )

    if st.button("Save Checklist to Cloud", type="primary", key="save_c_btn"):
        max_id = int(df_tasks["Task_ID"].max()) if not df_tasks.empty and pd.notnull(df_tasks["Task_ID"].max()) else 0
        for idx, row in edited_tasks.iterrows():
            if pd.isnull(row.get("Task_ID")) or row.get("Task_ID") == "":
                max_id += 1
                edited_tasks.at[idx, "Task_ID"] = max_id
            if pd.isnull(row.get("Date")) or row.get("Date") == "":
                edited_tasks.at[idx, "Date"] = sel_date_str

        all_other = df_tasks[df_tasks["Date"] != sel_date_str]
        save_sheet(pd.concat([all_other, edited_tasks], ignore_index=True), "Daily_Tasks")
        st.success("Cloud Updated!")
        st.rerun()

# 2. FOOD TRACKER
with main_tabs[1]:
    st.subheader("Food, Caloric Intake & Micronutrients")
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("#### 🍽️ Log Meal")
        with st.form("food_cloud_form", clear_on_submit=True):
            f_date = st.date_input("Date", value=date.today())
            f_time = st.text_input("Meal Type", value="Lunch")
            f_item = st.text_input("Food Item", placeholder="e.g. 2 Roti, Dhal, Paneer")
            cal = st.number_input("Calories (kcal)", min_value=0.0, step=10.0)
            prot = st.number_input("Protein (g)", min_value=0.0, step=1.0)
            carbs = st.number_input("Carbs (g)", min_value=0.0, step=1.0)
            fat = st.number_input("Fat (g)", min_value=0.0, step=1.0)
            water = st.number_input("Water (Liters)", min_value=0.0, max_value=10.0, step=0.25)
            micros = st.text_area("Micros / Notes", placeholder="e.g. Vitamins, Fiber")

            if st.form_submit_button("Save Meal", use_container_width=True):
                if f_item.strip():
                    df_food = load_sheet("Food_Log")
                    new_id = int(df_food["Entry_ID"].max() + 1) if not df_food.empty and pd.notnull(df_food["Entry_ID"].max()) else 1
                    new_row = pd.DataFrame([{
                        "Entry_ID": new_id, "Date": f_date.strftime("%Y-%m-%d"), "Time": f_time, "Meal_Item": f_item,
                        "Calories_kcal": cal, "Protein_g": prot, "Carbs_g": carbs, "Fat_g": fat, "Water_Liters": water, "Micronutrients_Notes": micros
                    }])
                    save_sheet(pd.concat([df_food, new_row], ignore_index=True), "Food_Log")
                    st.success("Meal Saved!")
                    st.rerun()

    with c2:
        st.markdown("#### 📋 Meals Logged Today")
        df_food = load_sheet("Food_Log")
        today_f = df_food[df_food["Date"] == today_str] if not df_food.empty else pd.DataFrame()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Calories", f"{today_f['Calories_kcal'].sum():.0f} kcal" if not today_f.empty else "0")
        m2.metric("Protein", f"{today_f['Protein_g'].sum():.1f} g" if not today_f.empty else "0")
        m3.metric("Carbs", f"{today_f['Carbs_g'].sum():.1f} g" if not today_f.empty else "0")
        m4.metric("Fat", f"{today_f['Fat_g'].sum():.1f} g" if not today_f.empty else "0")
        if not today_f.empty:
            st.dataframe(today_f, use_container_width=True, hide_index=True)

# 3. EXERCISE TRACKER
with main_tabs[2]:
    st.subheader("Exercise & Burned Calories")
    e1, e2 = st.columns([1, 2])
    with e1:
        with st.form("ex_cloud_form", clear_on_submit=True):
            ex_date = st.date_input("Date", value=date.today())
            ex_name = st.text_input("Exercise Name", placeholder="e.g. Squats, Pushups")
            muscle = st.selectbox("Muscle Group", ["Chest", "Abs", "Arms", "Legs", "Shoulder", "Back", "Full Body / Cardio"])
            sets = st.number_input("Sets", min_value=1, value=3)
            reps = st.text_input("Reps", value="10-12")
            weight = st.number_input("Weight (kg)", min_value=0.0, step=2.5)
            c_burn = st.number_input("Burned (kcal)", min_value=0.0, step=25.0, value=150.0)
            notes = st.text_area("Notes", placeholder="RPE 8")

            if st.form_submit_button("Log Exercise", use_container_width=True):
                if ex_name.strip():
                    df_ex = load_sheet("Exercise_Log")
                    new_id = int(df_ex["Log_ID"].max() + 1) if not df_ex.empty and pd.notnull(df_ex["Log_ID"].max()) else 1
                    new_row = pd.DataFrame([{
                        "Log_ID": new_id, "Date": ex_date.strftime("%Y-%m-%d"), "Exercise_Name": ex_name.strip(),
                        "Muscle_Group": muscle, "Sets": sets, "Reps_Per_Set": reps, "Weight_kg": weight,
                        "Calories_Burned_kcal": c_burn, "Notes": notes
                    }])
                    save_sheet(pd.concat([df_ex, new_row], ignore_index=True), "Exercise_Log")
                    st.success("Exercise Logged!")
                    st.rerun()

    with e2:
        df_ex = load_sheet("Exercise_Log")
        today_ex = df_ex[df_ex["Date"] == today_str] if not df_ex.empty else pd.DataFrame()
        st.metric("Total Burned Today", f"{today_ex['Calories_Burned_kcal'].sum():.0f} kcal" if not today_ex.empty else "0 kcal")
        if not today_ex.empty:
            st.dataframe(today_ex, use_container_width=True, hide_index=True)

# REVISION SHARED ENGINE
def render_cloud_revision(sheet_name, cat_list, cat_label, top_label):
    df = load_sheet(sheet_name)
    today_s = date.today().strftime("%Y-%m-%d")

    c_in, c_board = st.columns([1, 2])
    with c_in:
        with st.form(f"study_{sheet_name}", clear_on_submit=True):
            s_date = st.date_input("Date Studied", value=date.today(), key=f"s_{sheet_name}")
            cat_val = st.selectbox(cat_label, cat_list)
            top_val = st.text_input(top_label)
            conf = st.select_slider("Confidence", [1, 2, 3, 4, 5], value=3, key=f"cf_{sheet_name}")
            notes = st.text_area("Formulas / Notes")

            calc_dues = {f"{r.split('_')[0]}_Due_{r.split('_')[1]}": (s_date + timedelta(days=d)).strftime("%Y-%m-%d") for r, d in REVISION_INTERVALS.items()}

            if st.form_submit_button("Add Chapter to Schedule", use_container_width=True):
                if top_val.strip():
                    new_id = int(df["Item_ID"].max() + 1) if not df.empty and pd.notnull(df["Item_ID"].max()) else 1
                    row = {
                        "Item_ID": new_id,
                        "Date_Studied": s_date.strftime("%Y-%m-%d"),
                        ("Category" if sheet_name == "CA_SPOM_Tracker" else "Domain_Topic"): cat_val,
                        ("Topic_Chapter" if sheet_name == "CA_SPOM_Tracker" else "Concepts_Covered"): top_val.strip(),
                        "Confidence_Score": conf,
                        ("Notes_Difficult_Points" if sheet_name == "CA_SPOM_Tracker" else "Application_Notes"): notes,
                    }
                    for r in REVISION_INTERVALS:
                        p, s = r.split("_")[0], r.split("_")[1]
                        row[f"{p}_Due_{s}"] = calc_dues[f"{p}_Due_{s}"]
                        row[f"{p}_Done"] = False
                    save_sheet(pd.concat([df, pd.DataFrame([row])], ignore_index=True), sheet_name)
                    st.success("Scheduled across 3d, 7d, 15d, 30d, 90d, 180d!")
                    st.rerun()

    with c_board:
        if not df.empty:
            for r in REVISION_INTERVALS:
                d_col = f"{r.split('_')[0]}_Done"
                df[d_col] = df[d_col].fillna(False).astype(bool)

            cfgs = {
                "Item_ID": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "Date_Studied": st.column_config.DateColumn("Studied", disabled=True),
            }
            for r in REVISION_INTERVALS:
                p, s = r.split("_")[0], r.split("_")[1]
                cfgs[f"{p}_Due_{s}"] = st.column_config.DateColumn(f"{p} (+{s})", disabled=True)
                cfgs[f"{p}_Done"] = st.column_config.CheckboxColumn(f"{p}?")

            edited_df = st.data_editor(df.sort_values(by=["Date_Studied", "Item_ID"], ascending=[False, False]), column_config=cfgs, use_container_width=True, hide_index=True)
            if st.button("Save Revisions to Cloud", type="primary", key=f"btn_r_{sheet_name}"):
                save_sheet(edited_df, sheet_name)
                st.success("Cloud Updated!")
                st.rerun()
        else:
            st.info("No study chapters logged yet.")

# 4. CA & SPOM
with main_tabs[3]:
    st.subheader("CA Final & SPOM Study & Revision Log")
    ca_papers = ["Paper 1: FR", "Paper 2: AFM", "Paper 3: Advanced Auditing", "Paper 4: Direct Tax", "Paper 5: IDT", "Paper 6: IBS", "SPOM Set A: Law", "SPOM Set B: SCPM"]
    render_cloud_revision("CA_SPOM_Tracker", ca_papers, "Paper / SPOM Set", "Chapter / Standard")

# 5. OTHER LEARNING
with main_tabs[4]:
    st.subheader("Non-CA Learning Log")
    skills = ["Python / Automation", "Internal Audit Standards", "SAP ERP", "Financial Modeling", "Soft Skills", "Other"]
    render_cloud_revision("Other_Learning", skills, "Domain", "Skill / Concept")

# 6. HISTORY & AGGREGATIONS
with main_tabs[5]:
    st.subheader("📈 Performance & History Summaries")
    f_df = load_sheet("Food_Log")
    e_df = load_sheet("Exercise_Log")
    t_df = load_sheet("Daily_Tasks")
    s_df = load_sheet("CA_SPOM_Tracker")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Meals Logged", len(f_df))
    k2.metric("Workouts Logged", len(e_df))
    k3.metric("Tasks Handled", len(t_df))
    k4.metric("CA Chapters Scheduled", len(s_df))
