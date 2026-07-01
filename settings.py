import streamlit as st
import database
import google.generativeai as genai
import bcrypt

def render_settings_page():
    st.markdown("<h1 class='text-gradient' style='font-size: 2.2rem; margin-bottom: 0.5rem;'>⚙️ System Settings</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #a1a1aa; margin-bottom: 2rem;'>Configure application behavior, AI defaults, and export formats.</p>", unsafe_allow_html=True)
    
    # Restrict to Admin
    user = st.session_state.get("user")
    if not user or st.session_state.get("role") != "Admin":
        st.error("You do not have permission to view this page.")
        return

    tab_general, tab_ai, tab_export, tab_profile = st.tabs(["🌐 General", "🧠 AI Settings", "📄 Export Options", "👤 User Profile"])

    # ---------------------------------------------------------
    # TAB 1: General Settings
    # ---------------------------------------------------------
    with tab_general:
        st.markdown("<div class='saas-card form-container'>", unsafe_allow_html=True)
        st.subheader("General Configuration")
        
        # Load current
        current_company = database.get_setting("COMPANY_NAME", "ReqFlow AI Inc.")
        current_footer = database.get_setting("FOOTER_TEXT", "© 2026 ReqFlow AI. All rights reserved.")
        current_version = database.get_setting("APP_VERSION", "v1.0.0")
        current_theme = database.get_setting("DEFAULT_THEME", "Dark")
        
        with st.form("form_general_settings"):
            company_name = st.text_input("Company Name", value=current_company)
            footer_text = st.text_input("Footer Text", value=current_footer)
            app_version = st.text_input("App Version", value=current_version)
            theme_choice = st.selectbox("Default Theme", ["Light", "Dark", "Auto"], index=["Light", "Dark", "Auto"].index(current_theme))
            
            # File uploader for logo (mock handling logic for base64 storage can be added later)
            logo_upload = st.file_uploader("Upload Company Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])
            
            submitted = st.form_submit_button("Save General Settings")
            if submitted:
                database.update_setting("COMPANY_NAME", company_name, user.get("id"))
                database.update_setting("FOOTER_TEXT", footer_text, user.get("id"))
                database.update_setting("APP_VERSION", app_version, user.get("id"))
                database.update_setting("DEFAULT_THEME", theme_choice, user.get("id"))
                st.success("General settings saved successfully!")
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # TAB 2: AI Settings
    # ---------------------------------------------------------
    with tab_ai:
        st.markdown("<div class='saas-card form-container'>", unsafe_allow_html=True)
        st.subheader("AI Generation Preferences")
        
        current_api_key = database.get_setting("GEMINI_API_KEY", "")
        current_model = database.get_setting("AI_MODEL", "gemini-2.5-flash")
        current_temp = float(database.get_setting("AI_TEMPERATURE", "0.7"))
        current_tokens = int(database.get_setting("AI_MAX_TOKENS", "8192"))
        
        with st.form("form_ai_settings"):
            api_key = st.text_input("Gemini API Key", value=current_api_key, type="password", help="Securely stored in database.")
            model_selection = st.selectbox("Primary Model", ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"], index=["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"].index(current_model) if current_model in ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"] else 0)
            
            col1, col2 = st.columns(2)
            with col1:
                temperature = st.slider("Temperature (Creativity)", 0.0, 1.0, current_temp, step=0.1)
            with col2:
                max_tokens = st.number_input("Max Output Tokens", min_value=1000, max_value=32000, value=current_tokens, step=500)
            
            submitted = st.form_submit_button("Save AI Settings")
            if submitted:
                database.update_setting("GEMINI_API_KEY", api_key, user.get("id"))
                database.update_setting("AI_MODEL", model_selection, user.get("id"))
                database.update_setting("AI_TEMPERATURE", str(temperature), user.get("id"))
                database.update_setting("AI_MAX_TOKENS", str(max_tokens), user.get("id"))
                st.success("AI settings updated successfully!")
        
        st.markdown("---")
        if st.button("Test AI Connection"):
            try:
                test_key = api_key if api_key else current_api_key
                if not test_key:
                    st.error("No API key provided.")
                else:
                    genai.configure(api_key=test_key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content("Respond with a simple 'Connection Successful!'")
                    st.success(f"Response from Gemini: {response.text}")
            except Exception as e:
                st.error(f"Connection Failed: {str(e)}")
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # TAB 3: Export Settings
    # ---------------------------------------------------------
    with tab_export:
        st.markdown("<div class='saas-card form-container'>", unsafe_allow_html=True)
        st.subheader("Document Export Preferences")
        
        current_format = database.get_setting("EXPORT_DEFAULT_FORMAT", "PDF")
        current_watermark = database.get_setting("EXPORT_WATERMARK", "False") == "True"
        current_confidential = database.get_setting("EXPORT_CONFIDENTIAL", "True") == "True"
        current_header = database.get_setting("EXPORT_HEADER", "ReqFlow AI Auto-Generated Document")
        
        with st.form("form_export_settings"):
            export_format = st.selectbox("Default Export Format", ["PDF", "DOCX", "Excel", "Markdown"], index=["PDF", "DOCX", "Excel", "Markdown"].index(current_format) if current_format in ["PDF", "DOCX", "Excel", "Markdown"] else 0)
            watermark_toggle = st.checkbox("Include Watermark on PDF", value=current_watermark)
            confidential_toggle = st.checkbox("Add 'CONFIDENTIAL' label", value=current_confidential)
            header_text = st.text_input("Document Header Text", value=current_header)
            
            submitted = st.form_submit_button("Save Export Settings")
            if submitted:
                database.update_setting("EXPORT_DEFAULT_FORMAT", export_format, user.get("id"))
                database.update_setting("EXPORT_WATERMARK", str(watermark_toggle), user.get("id"))
                database.update_setting("EXPORT_CONFIDENTIAL", str(confidential_toggle), user.get("id"))
                database.update_setting("EXPORT_HEADER", header_text, user.get("id"))
                st.success("Export preferences saved!")
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # TAB 4: User Profile Settings
    # ---------------------------------------------------------
    with tab_profile:
        st.markdown("<div class='saas-card form-container'>", unsafe_allow_html=True)
        st.subheader("My Profile")
        
        with st.form("form_profile_settings"):
            full_name = st.text_input("Full Name", value=user.get("full_name", ""))
            email = st.text_input("Email Address", value=user.get("email", ""))
            
            st.markdown("##### Change Password")
            new_password = st.text_input("New Password", type="password", help="Leave blank if you don't want to change your password.")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            profile_pic = st.file_uploader("Upload Profile Picture", type=["png", "jpg", "jpeg"])
            
            submitted = st.form_submit_button("Update Profile")
            if submitted:
                if new_password and new_password != confirm_password:
                    st.error("Passwords do not match!")
                else:
                    pw_hash = None
                    if new_password:
                        pw_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    success, msg = database.update_user(
                        user_id=user.get("id"),
                        full_name=full_name,
                        email=email,
                        password_hash=pw_hash
                    )
                    if success:
                        st.session_state.user["full_name"] = full_name
                        st.session_state.user["email"] = email
                        st.success("Profile updated successfully!")
                    else:
                        st.error(f"Error updating profile: {msg}")
        st.markdown("</div>", unsafe_allow_html=True)
