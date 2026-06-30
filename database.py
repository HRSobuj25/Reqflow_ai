# database.py
import os
import urllib
import json
from datetime import datetime
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import bcrypt

# Load environment variables
load_dotenv()

# Database Configuration
DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_DATABASE = os.getenv("DB_DATABASE", "ReqFlowAI")
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
DB_TRUSTED = os.getenv("DB_TRUSTED", "yes").lower() == "yes"
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_CONN_STR_OVERRIDE = os.getenv("DB_CONNECTION_STRING")

# Construct Connection String
if DB_CONN_STR_OVERRIDE:
    odbc_str = DB_CONN_STR_OVERRIDE
else:
    if DB_TRUSTED:
        odbc_str = f"Driver={{{DB_DRIVER}}};Server={DB_SERVER};Database={DB_DATABASE};Trusted_Connection=yes;"
        if "18" in DB_DRIVER:
            odbc_str += "TrustServerCertificate=yes;"
    else:
        odbc_str = f"Driver={{{DB_DRIVER}}};Server={DB_SERVER};Database={DB_DATABASE};Uid={DB_USER};Pwd={DB_PASSWORD};"

# URL-encode the connection parameters for SQLAlchemy
params = urllib.parse.quote_plus(odbc_str)
DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={params}"

# Global connection flag and engine
DB_AVAILABLE = False
engine = None
SessionLocal = None
Base = declarative_base()

try:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
        pool_pre_ping=True
    )
    # Test connection immediately
    with engine.connect() as conn:
        DB_AVAILABLE = True
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    print(f"[Database Warn] Could not establish connection to SQL Server: {str(e)}")
    print("[Database Warn] ReqFlow AI will fall back to in-memory Session State storage.")
    DB_AVAILABLE = False


# =====================================================================
# Database Schema Models
# =====================================================================

class Project(Base):
    """
    SaaS Workspace Project metadata details.
    """
    __tablename__ = "Projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    industry = Column(String(100), nullable=True)
    scope_details = Column(Text, nullable=True)
    features = Column(Text, nullable=True)  # Stored as JSON string list of modules
    creativity_level = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    requirements = relationship("Requirement", back_populates="project", cascade="all, delete-orphan", uselist=False)
    documents = relationship("GeneratedDocument", back_populates="project", cascade="all, delete-orphan")


class Requirement(Base):
    """
    ERP Requirements documents mapping the 8 generated tabs.
    """
    __tablename__ = "Requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("Projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    brd = Column(Text, nullable=True)
    srs = Column(Text, nullable=True)
    use_cases = Column(Text, nullable=True)
    user_stories = Column(Text, nullable=True)
    db_suggestions = Column(Text, nullable=True)
    kpis = Column(Text, nullable=True)
    workflow = Column(Text, nullable=True)
    reports = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="requirements")


class GeneratedDocument(Base):
    """
    Export log tracking output suites downloaded by users.
    """
    __tablename__ = "GeneratedDocuments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("Projects.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = Column(String(50), nullable=False)  # 'BRD', 'SRS', 'FullSuite' etc.
    file_format = Column(String(10), nullable=False)    # 'md', 'pdf'
    file_path = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="documents")


class Role(Base):
    """User roles for access control."""
    __tablename__ = "Roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(50), unique=True, nullable=False)

    users = relationship("User", back_populates="role")


class User(Base):
    """User accounts."""
    __tablename__ = "Users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("Roles.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    role = relationship("Role", back_populates="users")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    """Log of user sessions."""
    __tablename__ = "UserSessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("Users.id", ondelete="CASCADE"), nullable=False)
    login_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    logout_time = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="sessions")


# =====================================================================
# Helper context and CRUD services
# =====================================================================

@contextmanager
def get_db():
    """Scoped session generator."""
    if not DB_AVAILABLE or SessionLocal is None:
        raise RuntimeError("Database connection is not available.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Initializes tables in Microsoft SQL Server."""
    if not DB_AVAILABLE:
        print("[Database Info] Connection not established. Skipping table creation.")
        return False
    try:
        Base.metadata.create_all(bind=engine)
        print("[Database Info] ReqFlowAI database tables initialized successfully.")
        
        # Seed initial data (Roles and Admin user)
        with get_db() as db:
            roles_to_add = ["Admin", "Business Analyst", "Viewer"]
            for r_name in roles_to_add:
                if not db.query(Role).filter(Role.role_name == r_name).first():
                    db.add(Role(role_name=r_name))
            db.commit()
            
            admin_role = db.query(Role).filter(Role.role_name == "Admin").first()
            if admin_role and not db.query(User).filter(User.username == "admin").first():
                # Default admin password: admin123
                hashed_pw = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                admin_user = User(
                    full_name="System Administrator",
                    username="admin",
                    email="admin@reqflow.ai",
                    password_hash=hashed_pw,
                    role_id=admin_role.id
                )
                db.add(admin_user)
                db.commit()
        return True
    except Exception as e:
        print(f"[Database Error] Error initializing database tables: {str(e)}")
        return False


def get_user_by_username(username):
    if not DB_AVAILABLE: return None
    with get_db() as db:
        return db.query(User).filter(User.username == username).first()

def get_user_by_id(user_id):
    if not DB_AVAILABLE: return None
    with get_db() as db:
        return db.query(User).filter(User.id == user_id).first()

def get_role_by_id(role_id):
    if not DB_AVAILABLE: return None
    with get_db() as db:
        return db.query(Role).filter(Role.id == role_id).first()

def get_role_by_name(role_name):
    if not DB_AVAILABLE: return None
    with get_db() as db:
        return db.query(Role).filter(Role.role_name == role_name).first()

def get_all_roles():
    if not DB_AVAILABLE: return []
    with get_db() as db:
        return db.query(Role).all()

def create_user(full_name, username, email, password_hash, role_id):
    if not DB_AVAILABLE: return False, "Database not available"
    with get_db() as db:
        try:
            new_user = User(
                full_name=full_name,
                username=username,
                email=email,
                password_hash=password_hash,
                role_id=role_id
            )
            db.add(new_user)
            db.commit()
            return True, "User created successfully"
        except Exception as e:
            db.rollback()
            return False, str(e)

def log_session_login(user_id):
    if not DB_AVAILABLE: return None
    with get_db() as db:
        try:
            session = UserSession(user_id=user_id)
            db.add(session)
            db.commit()
            db.refresh(session)
            return session.id
        except:
            db.rollback()
            return None

def log_session_logout(session_id):
    if not DB_AVAILABLE: return
    with get_db() as db:
        try:
            session = db.query(UserSession).filter(UserSession.id == session_id).first()
            if session:
                session.logout_time = datetime.utcnow()
                db.commit()
        except:
            db.rollback()


def save_project(name, industry=None, scope_details=None, features=None, creativity_level=None):
    """Creates a new Project metadata record or updates it and returns its id."""
    if isinstance(features, list):
        features_str = json.dumps(features)
    else:
        features_str = features

    with get_db() as db:
        try:
            existing = db.query(Project).filter(Project.name == name).first()
            if existing:
                existing.industry = industry
                existing.scope_details = scope_details
                existing.features = features_str
                existing.creativity_level = creativity_level
                db.commit()
                return existing.id

            proj = Project(
                name=name,
                industry=industry,
                scope_details=scope_details,
                features=features_str,
                creativity_level=creativity_level
            )
            db.add(proj)
            db.commit()
            db.refresh(proj)
            return proj.id
        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Failed to save project: {str(e)}")


def save_requirements(project_id, brd, srs, use_cases, user_stories, db_suggestions, kpis, workflow, reports):
    """Saves or updates the 8-tab specification documents suite for a Project."""
    with get_db() as db:
        try:
            req = db.query(Requirement).filter(Requirement.project_id == project_id).first()
            if not req:
                req = Requirement(project_id=project_id)
                db.add(req)

            req.brd = brd
            req.srs = srs
            req.use_cases = use_cases
            req.user_stories = user_stories
            req.db_suggestions = db_suggestions
            req.kpis = kpis
            req.workflow = workflow
            req.reports = reports

            db.commit()
            return req.id
        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Failed to save requirements: {str(e)}")


def log_document_export(project_id, document_type, file_format, content, file_path=None):
    """Logs a generated requirement suite/document download activity."""
    with get_db() as db:
        try:
            doc = GeneratedDocument(
                project_id=project_id,
                document_type=document_type,
                file_format=file_format,
                content=content,
                file_path=file_path
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            return doc.id
        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Failed to log document export: {str(e)}")


def save_full_generation(project_name, industry, scope_details, features, creativity_level, requirements):
    """
    Saves project, requirements, and logs all generated documents under a single database transaction.
    """
    if isinstance(features, list):
        features_str = json.dumps(features)
    else:
        features_str = features

    with get_db() as db:
        try:
            # 1. Save or Update Project
            proj = db.query(Project).filter(Project.name == project_name).first()
            if proj:
                proj.industry = industry
                proj.scope_details = scope_details
                proj.features = features_str
                proj.creativity_level = creativity_level
                proj.updated_at = datetime.utcnow()
            else:
                proj = Project(
                    name=project_name,
                    industry=industry,
                    scope_details=scope_details,
                    features=features_str,
                    creativity_level=creativity_level,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(proj)
            
            # Flush session to generate ID for child tables
            db.flush()
            project_id = proj.id

            # 2. Save or Update Requirements
            req = db.query(Requirement).filter(Requirement.project_id == project_id).first()
            if not req:
                req = Requirement(project_id=project_id, created_at=datetime.utcnow())
                db.add(req)
            
            req.brd = requirements.get("brd")
            req.srs = requirements.get("srs")
            req.use_cases = requirements.get("use_cases")
            req.user_stories = requirements.get("user_stories")
            # Handle database suggestions vs database_design keys
            req.db_suggestions = requirements.get("database_design") or requirements.get("db_suggestions")
            req.kpis = requirements.get("kpis")
            req.workflow = requirements.get("workflow")
            req.reports = requirements.get("reports")
            req.updated_at = datetime.utcnow()

            # 3. Log Generated Documents (individual sections)
            doc_types = {
                "BRD": requirements.get("brd"),
                "SRS": requirements.get("srs"),
                "Use Cases": requirements.get("use_cases"),
                "User Stories": requirements.get("user_stories"),
                "Database Suggestions": requirements.get("database_design") or requirements.get("db_suggestions"),
                "KPIs": requirements.get("kpis"),
                "Workflow": requirements.get("workflow"),
                "Reports": requirements.get("reports")
            }

            for doc_type, content in doc_types.items():
                if content:
                    doc = GeneratedDocument(
                        project_id=project_id,
                        document_type=doc_type,
                        file_format="md",
                        content=content,
                        created_at=datetime.utcnow()
                    )
                    db.add(doc)

            db.commit()
            return project_id
        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Database transaction failed: {str(e)}")


def get_project_by_name(name):
    """Retrieves full project details and nested requirements as a dictionary."""
    with get_db() as db:
        try:
            proj = db.query(Project).filter(Project.name == name).first()
            if not proj:
                return None

            try:
                features_list = json.loads(proj.features) if proj.features else []
            except Exception:
                features_list = proj.features.split(",") if proj.features else []

            result = {
                "id": proj.id,
                "name": proj.name,
                "industry": proj.industry,
                "scope": proj.scope_details,
                "features": features_list,
                "creativity_level": proj.creativity_level,
                "timestamp": proj.updated_at.strftime("%b %d, %H:%M")
            }

            if proj.requirements:
                req = proj.requirements
                result.update({
                    "brd": req.brd,
                    "srs": req.srs,
                    "use_cases": req.use_cases,
                    "user_stories": req.user_stories,
                    "db_suggestions": req.db_suggestions,
                    "kpis": req.kpis,
                    "workflow": req.workflow,
                    "reports": req.reports
                })
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve project by name: {str(e)}")


def list_projects():
    """Lists basic project metadata to populate sidebar history dropdowns."""
    with get_db() as db:
        try:
            projects = db.query(Project).order_by(Project.updated_at.desc()).all()
            return [
                {
                    "name": p.name,
                    "industry": p.industry,
                    "date": p.updated_at.strftime("%b %d, %Y")
                } for p in projects
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to list projects: {str(e)}")


def delete_project_by_id(project_id):
    """Deletes a project record and cascades to requirements & document logs."""
    with get_db() as db:
        try:
            proj = db.query(Project).filter(Project.id == project_id).first()
            if proj:
                db.delete(proj)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Failed to delete project: {str(e)}")


def list_projects_full():
    """
    Returns an enriched project list for the Project History page.
    Each entry includes scope preview, feature count, document availability, and timestamps.
    Falls back gracefully for projects with missing fields.
    """
    with get_db() as db:
        try:
            projects = db.query(Project).order_by(Project.updated_at.desc()).all()
            result = []
            for p in projects:
                try:
                    features_list = json.loads(p.features) if p.features else []
                except Exception:
                    features_list = [f.strip() for f in p.features.split(",")] if p.features else []

                scope = p.scope_details or ""
                scope_preview = (scope[:155] + "…") if len(scope) > 155 else (scope or "No scope details provided.")

                result.append({
                    "id":             p.id,
                    "name":           p.name,
                    "industry":       p.industry or "General",
                    "scope_preview":  scope_preview,
                    "feature_count":  len(features_list),
                    "features":       features_list,
                    "creativity_level": p.creativity_level,
                    "has_requirements": p.requirements is not None,
                    "created_at":     p.created_at.strftime("%b %d, %Y") if p.created_at else "Unknown",
                    "updated_date":   p.updated_at.strftime("%b %d, %Y") if p.updated_at else "Unknown",
                    "updated_at_full": p.updated_at.strftime("%b %d, %Y %H:%M") if p.updated_at else "Unknown",
                })
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to list full projects: {str(e)}")


def get_project_with_requirements(project_id):
    """
    Fetches a project and its full 8-document requirement suite by numeric ID.
    Returns a dict fully compatible with the session state projects format used by
    the dashboard tab renderer. Falls back to placeholder text for missing documents.
    """
    with get_db() as db:
        try:
            proj = db.query(Project).filter(Project.id == project_id).first()
            if not proj:
                return None

            try:
                features_list = json.loads(proj.features) if proj.features else []
            except Exception:
                features_list = [f.strip() for f in proj.features.split(",")] if proj.features else []

            result = {
                "id":               proj.id,
                "name":             proj.name,
                "industry":         proj.industry or "General",
                "scope":            proj.scope_details,
                "features":         features_list,
                "creativity_level": proj.creativity_level,
                "timestamp":        proj.updated_at.strftime("%b %d, %H:%M") if proj.updated_at else "Unknown",
            }

            _placeholder = "*No documents were generated for this project. Please regenerate from the Dashboard.*"
            if proj.requirements:
                req = proj.requirements
                result.update({
                    "brd":           req.brd            or _placeholder,
                    "srs":           req.srs            or _placeholder,
                    "use_cases":     req.use_cases      or _placeholder,
                    "user_stories":  req.user_stories   or _placeholder,
                    "db_suggestions": req.db_suggestions or _placeholder,
                    "kpis":          req.kpis           or _placeholder,
                    "workflow":      req.workflow        or _placeholder,
                    "reports":       req.reports         or _placeholder,
                })
            else:
                result.update({k: _placeholder for k in [
                    "brd", "srs", "use_cases", "user_stories",
                    "db_suggestions", "kpis", "workflow", "reports"
                ]})

            return result
        except Exception as e:
            raise RuntimeError(f"Failed to fetch project with requirements (id={project_id}): {str(e)}")


# =====================================================================
# CLI Verification & Setup Suite
# =====================================================================

if __name__ == "__main__":

    print("Initializing local SQL Server connection setup...")
    print(f"Server: {DB_SERVER}")
    print(f"Database: {DB_DATABASE}")
    print(f"ODBC Driver: {DB_DRIVER}")
    print(f"Trusted Connection: {DB_TRUSTED}")
    
    if DB_AVAILABLE:
        print("\nCreating tables...")
        created = create_tables()
        if created:
            print("\nInserting sample test project...")
            try:
                proj_id = save_project(
                    name="Test Local DB ERP",
                    industry="FinTech",
                    scope_details="A ledger processing system for microloans.",
                    features=["Ledger Core", "Audit Tracking"],
                    creativity_level=0.7
                )
                print(f"Project created successfully with ID: {proj_id}")
                
                req_id = save_requirements(
                    project_id=proj_id,
                    brd="# BRD Draft",
                    srs="# SRS Draft",
                    use_cases="# Use Cases Table",
                    user_stories="# User Stories",
                    db_suggestions="PostgreSQL",
                    kpis="MTBF",
                    workflow="Mermaid Diagram",
                    reports="Operational Reports"
                )
                print(f"Requirements saved successfully with ID: {req_id}")
                
                print("\nFetching project back...")
                data = get_project_by_name("Test Local DB ERP")
                print("Project Name:", data["name"])
                print("Industry:", data["industry"])
                print("BRD Preview:", data["brd"])
                
                print("\nListing projects...")
                all_projects = list_projects()
                print("All Projects:", all_projects)
            except Exception as ex:
                print(f"CRUD execution error: {str(ex)}")
    else:
        print("\n[Database Offline] Cannot run CLI verification. Connection could not be established.")
