import streamlit as st
import bcrypt
import database
import time

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def init_session_state():
    """Initialize authentication related session state variables."""
    if "user" not in st.session_state:
        st.session_state.user = None
    if "role" not in st.session_state:
        st.session_state.role = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = None

def authenticate_user(username, password):
    """Authenticate user and initialize session if successful."""
    if not database.DB_AVAILABLE:
        # Fallback to in-memory mock admin when database is offline
        if username == "admin" and password == "admin123":
            st.session_state.user = {
                "id": 0,
                "full_name": "Offline Administrator",
                "username": "admin",
                "email": "offline@reqflow.ai"
            }
            st.session_state.role = "Admin"
            st.session_state.session_id = 0
            return True
        return False

    user = database.get_user_by_username(username)
    if user and user.is_active:
        if verify_password(password, user.password_hash):
            role = database.get_role_by_id(user.role_id)
            st.session_state.user = {
                "id": user.id,
                "full_name": user.full_name,
                "username": user.username,
                "email": user.email
            }
            st.session_state.role = role.role_name if role else "Viewer"
            # Log session
            session_id = database.log_session_login(user.id)
            st.session_state.session_id = session_id
            return True
    return False

def logout():
    """Log out the user and clear session state."""
    if st.session_state.session_id:
        database.log_session_logout(st.session_state.session_id)
    
    st.session_state.user = None
    st.session_state.role = None
    st.session_state.session_id = None

def has_permission(required_roles: list) -> bool:
    """Check if current user has any of the required roles."""
    if st.session_state.role in required_roles:
        return True
    return False

def render_login_page():
    """Render a modern SaaS login page."""
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div class="logo-badge" style="width: 50px; height: 50px; font-size: 1.5rem; margin: 0 auto 1rem auto; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%); color: white; border-radius: 8px; box-shadow: 0 4px 10px rgba(139, 92, 246, 0.3);">⚡</div>
            <h1 class="text-gradient" style="font-size: 2.5rem; margin-bottom: 0.5rem; background: linear-gradient(135deg, #a78bfa 0%, #818cf8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800;">ReqFlow AI</h1>
            <p style="color: #a5b4fc; font-size: 1.1rem;">Enterprise Requirement Generation</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="saas-card form-container">', unsafe_allow_html=True)
            
            st.markdown('<h3 style="margin-bottom: 1.5rem; font-weight: 600;">Sign In</h3>', unsafe_allow_html=True)
            
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Login", use_container_width=True):
                if username and password:
                    if authenticate_user(username, password):
                        st.success("Login successful!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
                else:
                    st.warning("Please enter both username and password.")
            
            st.markdown('</div>', unsafe_allow_html=True)

def render_user_profile():
    """Render user profile in sidebar."""
    if st.session_state.user:
        badge_class = "saas-badge-purple" if st.session_state.role == "Admin" else "saas-badge-green"
        
        st.markdown(f"""
        <div style="padding: 1rem; border-top: 1px solid #271c4c; margin-top: 1rem; text-align: center;">
            <div style="font-weight: 600; font-size: 1.05rem;">{st.session_state.user['full_name']}</div>
            <div style="color: #a5b4fc; font-size: 0.8rem; margin-bottom: 0.5rem;">@{st.session_state.user['username']}</div>
            <span class="saas-badge {badge_class}">{st.session_state.role}</span>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Sign Out", key="logout_btn"):
            logout()
            st.rerun()

def render_registration_page():
    """Render user registration page for admins."""
    if not has_permission(["Admin"]):
        st.error("You do not have permission to access this page.")
        return
        
    st.markdown("### User Management")
    
    with st.expander("Register New User", expanded=True):
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        
        with st.form("register_user_form"):
            full_name = st.text_input("Full Name")
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            
            roles = database.get_all_roles()
            role_options = {r.role_name: r.id for r in roles}
            selected_role = st.selectbox("Role", options=list(role_options.keys()))
            
            submitted = st.form_submit_button("Create User")
            
            if submitted:
                if full_name and username and email and password and selected_role:
                    hashed_pw = hash_password(password)
                    success, msg = database.create_user(
                        full_name=full_name,
                        username=username,
                        email=email,
                        password_hash=hashed_pw,
                        role_id=role_options[selected_role]
                    )
                    if success:
                        st.success(f"User '{username}' created successfully as {selected_role}.")
                    else:
                        st.error(f"Error creating user: {msg}")
                else:
                    st.warning("Please fill out all fields.")
        
        st.markdown('</div>', unsafe_allow_html=True)
