import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from ai_evaluator import evaluate_prompt
from database import (
    clear_all_data,
    get_all_submissions,
    get_leaderboard,
    get_or_create_student,
    get_student_by_id,
    get_student_submissions,
    init_db,
    save_submission,
)
from utils import (
    CHALLENGES,
    count_words,
    get_admin_password,
    inject_css,
    leaderboard_to_csv,
    resolve_api_key,
)

load_dotenv()
init_db()

st.set_page_config(
    page_title="Token Limit Prompt Challenge",
    page_icon="🎯",
    layout="wide",
)

inject_css()


def initialize_session() -> None:
    st.session_state.setdefault("student_id", None)
    st.session_state.setdefault("student_name", "")
    st.session_state.setdefault("roll_number", "")
    st.session_state.setdefault("class_section", "")
    st.session_state.setdefault("admin_authenticated", False)


def render_header() -> None:
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">Token Limit Prompt Challenge</div>
            <p class="hero-subtitle">
                Practice writing stronger prompts under strict word limits, get AI-based feedback,
                and compare results on the classroom leaderboard.
            </p>
            <div>
                <span class="badge">4 Rounds</span>
                <span class="badge">AI Scoring</span>
                <span class="badge">SQLite Leaderboard</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def current_student():
    student_id = st.session_state.get("student_id")
    if not student_id:
        return None
    return get_student_by_id(student_id)


def render_sidebar():
    with st.sidebar:
        st.header("Evaluation Settings")
        provider = st.selectbox("Select AI provider", ["OpenAI", "Google Gemini", "Groq"])
        student_api_key = st.text_input(
            "Your API key (optional)",
            type="password",
            help="If left blank, the app will use the instructor fallback key from .env if available.",
        )

        key_info = resolve_api_key(provider, student_api_key)
        if key_info["source"] == "student":
            st.success("Using student-provided API key.")
        elif key_info["source"] == "instructor":
            st.info("Using instructor fallback API key from .env.")
        else:
            st.warning(f"No API key available for {provider}.")

        st.divider()
        st.caption("API keys are never saved to the database.")
        return provider, student_api_key, key_info


def render_student_login() -> None:
    st.subheader("Student Login")
    st.write("Enter your details before starting the challenge.")

    with st.form("student_login_form"):
        name = st.text_input("Student name", value=st.session_state.get("student_name", ""))
        roll_number = st.text_input("Roll number", value=st.session_state.get("roll_number", ""))
        class_section = st.text_input(
            "Class / Section (optional)",
            value=st.session_state.get("class_section", ""),
        )
        submitted = st.form_submit_button("Save and Continue", use_container_width=True)

    if submitted:
        if not name.strip() or not roll_number.strip():
            st.error("Student name and roll number are required.")
            return

        student = get_or_create_student(name, roll_number, class_section)
        st.session_state["student_id"] = student["id"]
        st.session_state["student_name"] = student["name"]
        st.session_state["roll_number"] = student["roll_number"]
        st.session_state["class_section"] = student.get("class_section", "")
        st.success("Student profile saved. You can now start the challenge.")

    student = current_student()
    if student:
        st.markdown(
            f"""
            <div class="metric-card">
                <strong>Active student:</strong> {student["name"]}<br>
                <strong>Roll number:</strong> {student["roll_number"]}<br>
                <strong>Class / Section:</strong> {student.get("class_section") or "Not provided"}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_challenge(provider: str, student_api_key: str) -> None:
    st.subheader("Challenge")
    student = current_student()

    if not student:
        st.warning("Please complete the Student Login tab first.")
        return

    submissions = get_student_submissions(student["id"])
    completed_rounds = {item["round_number"] for item in submissions}
    # Students progress through the challenge in order, one round at a time.
    next_challenge = next((item for item in CHALLENGES if item["round"] not in completed_rounds), None)

    progress = len(completed_rounds) / len(CHALLENGES)
    st.progress(progress, text=f"Round progress: {len(completed_rounds)} of {len(CHALLENGES)} completed")

    cols = st.columns(len(CHALLENGES))
    for idx, challenge in enumerate(CHALLENGES):
        status = "Completed" if challenge["round"] in completed_rounds else "Pending"
        cols[idx].metric(f"Round {challenge['round']}", f"{challenge['word_limit']} words", status)

    if not next_challenge:
        st.success("You have completed all rounds.")
        return

    st.markdown(
        f"""
        <div class="round-card">
            <h4>Round {next_challenge["round"]}: {next_challenge["title"]}</h4>
            <p><strong>Task:</strong> {next_challenge["task"]}</p>
            <p class="small-muted"><strong>Maximum words:</strong> {next_challenge["word_limit"]}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    prompt_key = f"prompt_round_{next_challenge['round']}"
    prompt_text = st.text_area(
        "Write your prompt",
        key=prompt_key,
        height=180,
        placeholder="Type your prompt here...",
    )
    word_count = count_words(prompt_text)
    word_limit = next_challenge["word_limit"]

    counter_col1, counter_col2 = st.columns([1, 2])
    counter_col1.metric("Word count", word_count)
    if word_count > word_limit:
        counter_col2.error("Word limit exceeded. Reduce your prompt before submitting.")
    else:
        counter_col2.success("Within the allowed limit.")

    if st.button("Submit Round", type="primary", use_container_width=True):
        if not prompt_text.strip():
            st.error("Please write a prompt before submitting.")
            return
        if word_count > word_limit:
            st.error("Submission blocked because the word limit was exceeded.")
            return

        api_config = resolve_api_key(provider, student_api_key)
        if not api_config["api_key"]:
            st.error(
                f"No API key found for {provider}. Add your own key in the sidebar or set {api_config['env_name']} in .env."
            )
            return

        with st.spinner("Evaluating your prompt..."):
            result = evaluate_prompt(
                provider=provider,
                student_prompt=prompt_text,
                challenge=next_challenge,
                api_key=api_config["api_key"],
            )

        if result.get("error"):
            st.error(result["error"])
            st.info("The app handled the error safely. You can retry after fixing the issue.")
            return

        save_submission(
            student_id=student["id"],
            round_number=next_challenge["round"],
            task_title=next_challenge["title"],
            word_limit=word_limit,
            student_prompt=prompt_text.strip(),
            word_count=word_count,
            score=result["score"],
            feedback=result["feedback"],
            improved_prompt=result["improved_prompt"],
        )
        st.balloons()
        st.success(f"Round {next_challenge['round']} submitted successfully. Score: {result['score']}/10")
        st.rerun()


def render_my_results() -> None:
    st.subheader("My Results")
    student = current_student()

    if not student:
        st.warning("Please complete the Student Login tab first.")
        return

    submissions = get_student_submissions(student["id"])
    if not submissions:
        st.info("No submissions yet. Complete a round to see your results.")
        return

    total_score = round(sum(item["score"] for item in submissions), 2)
    average_score = round(total_score / len(submissions), 2)
    metric_cols = st.columns(3)
    metric_cols[0].metric("Total score", total_score)
    metric_cols[1].metric("Average score", average_score)
    metric_cols[2].metric("Rounds attempted", len(submissions))

    for submission in submissions:
        with st.container(border=True):
            st.markdown(
                f"### Round {submission['round_number']}: {submission['task_title']}"
            )
            detail_cols = st.columns(3)
            detail_cols[0].metric("Score", submission["score"])
            detail_cols[1].metric("Word limit", submission["word_limit"])
            detail_cols[2].metric("Your word count", submission["word_count"])

            st.write("**Your prompt**")
            st.code(submission["student_prompt"], language="text")
            st.write("**Feedback**")
            st.write(submission["feedback"] or "No feedback available.")
            st.write("**Improved prompt**")
            st.code(submission["improved_prompt"] or "No improved prompt provided.", language="text")


def render_leaderboard() -> None:
    st.subheader("Leaderboard")
    rows = get_leaderboard()
    if not rows:
        st.info("No leaderboard data yet.")
        return

    frame = pd.DataFrame(rows)[
        ["rank", "name", "roll_number", "total_score", "average_score", "rounds_attempted"]
    ]
    st.dataframe(frame, use_container_width=True, hide_index=True)


def render_admin() -> None:
    st.subheader("Admin / Reset")
    stored_password = get_admin_password()

    if not stored_password:
        st.warning("ADMIN_PASSWORD is missing in .env. Admin actions are disabled.")
        return

    password = st.text_input("Admin password", type="password")
    if st.button("Unlock Admin"):
        st.session_state["admin_authenticated"] = password == stored_password
        if st.session_state["admin_authenticated"]:
            st.success("Admin access granted.")
        else:
            st.error("Incorrect admin password.")

    if not st.session_state.get("admin_authenticated"):
        st.info("Enter the admin password to access reset and export tools.")
        return

    leaderboard_rows = get_leaderboard()
    submissions = get_all_submissions()

    action_cols = st.columns(2)
    with action_cols[0]:
        if leaderboard_rows:
            st.download_button(
                "Export Leaderboard CSV",
                data=leaderboard_to_csv(leaderboard_rows),
                file_name="leaderboard.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.button("Export Leaderboard CSV", disabled=True, use_container_width=True)

    with action_cols[1]:
        if st.button("Clear All Leaderboard Data", type="secondary", use_container_width=True):
            clear_all_data()
            st.success("All student and submission data has been cleared.")
            st.rerun()

    st.write("### All Submissions")
    if submissions:
        st.dataframe(pd.DataFrame(submissions), use_container_width=True, hide_index=True)
    else:
        st.info("No submissions available.")


def main() -> None:
    initialize_session()
    render_header()
    provider, student_api_key, _ = render_sidebar()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Student Login", "Challenge", "My Results", "Leaderboard", "Admin / Reset"]
    )

    with tab1:
        render_student_login()
    with tab2:
        render_challenge(provider, student_api_key)
    with tab3:
        render_my_results()
    with tab4:
        render_leaderboard()
    with tab5:
        render_admin()


if __name__ == "__main__":
    main()
