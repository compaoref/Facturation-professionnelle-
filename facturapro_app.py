import streamlit as st
import hashlib
import json
import os
import requests
from datetime import datetime, date
import streamlit.components.v1 as components

st.set_page_config(
    page_title="FacturaPro — Gestion Commerciale",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============================================
# CONFIGURATION BASE DE DONNEES (SUPABASE REST)
# requests est pre-installe sur Streamlit Cloud
# Aucun package externe requis!
# =============================================

class DB:
    """
    Acces Supabase via API REST avec requests.
    Aucune dependance externe - requests est inclus dans Python.
    """
    def __init__(self):
        try:
            self._url  = st.secrets["SUPABASE_URL"].rstrip("/")
            self._key  = st.secrets["SUPABASE_KEY"]
            self._hdrs = {
                "apikey":        self._key,
                "Authorization": f"Bearer {self._key}",
                "Content-Type":  "application/json",
                "Prefer":        "return=representation",
            }
        except Exception:
            self._url  = ""
            self._key  = ""
            self._hdrs = {}

    def _endpoint(self, table):
        return f"{self._url}/rest/v1/{table}"

    def is_connected(self):
        if not self._url or not self._key:
            return False
        try:
            r = requests.get(
                self._endpoint("fp_companies"),
                headers=self._hdrs,
                params={"limit": 1},
                timeout=8
            )
            return r.status_code in (200, 206)
        except Exception:
            return False

    def fa(self, table, filters=None, order=None, limit=None):
        """Retourne une liste de dicts"""
        try:
            params = {"select": "*"}
            if filters:
                for col, val in filters.items():
                    params[col] = f"eq.{val}"
            if order:
                params["order"] = f"{order}.desc"
            if limit:
                params["limit"] = limit
            r = requests.get(
                self._endpoint(table),
                headers=self._hdrs,
                params=params,
                timeout=10
            )
            return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    def f1(self, table, filters=None):
        """Retourne une seule ligne"""
        rows = self.fa(table, filters=filters, limit=1)
        return rows[0] if rows else None

    def insert(self, table, data):
        """INSERT - retourne la ligne inseree"""
        try:
            # Convertir les dates en string
            clean = {}
            for k, v in data.items():
                if isinstance(v, (datetime, date)):
                    clean[k] = v.isoformat()
                else:
                    clean[k] = v
            r = requests.post(
                self._endpoint(table),
                headers=self._hdrs,
                json=clean,
                timeout=10
            )
            if r.status_code in (200, 201):
                result = r.json()
                return result[0] if isinstance(result, list) else result
            return None
        except Exception as e:
            st.warning(f"Erreur insert: {str(e)[:80]}")
            return None

    def update(self, table, data, filters):
        """UPDATE"""
        try:
            params = {}
            for col, val in filters.items():
                params[col] = f"eq.{val}"
            clean = {}
            for k, v in data.items():
                if isinstance(v, (datetime, date)):
                    clean[k] = v.isoformat()
                else:
                    clean[k] = v
            r = requests.patch(
                self._endpoint(table),
                headers=self._hdrs,
                params=params,
                json=clean,
                timeout=10
            )
            return r.status_code in (200, 204)
        except Exception:
            return False

    def delete(self, table, filters):
        """DELETE"""
        try:
            params = {}
            for col, val in filters.items():
                params[col] = f"eq.{val}"
            r = requests.delete(
                self._endpoint(table),
                headers=self._hdrs,
                params=params,
                timeout=10
            )
            return r.status_code in (200, 204)
        except Exception:
            return False

    def fa_filter(self, table, col, op, val):
        """Filtre avec operateur: eq, neq, gt, lt, ilike"""
        try:
            params = {"select": "*", col: f"{op}.{val}"}
            r = requests.get(
                self._endpoint(table),
                headers=self._hdrs,
                params=params,
                timeout=10
            )
            return r.json() if r.status_code == 200 else []
        except Exception:
            return []


db = DB()

# =============================================
# UTILITAIRES
# =============================================

def hash_pwd(p):
    return hashlib.sha256((p + "factura_salt_2025").encode()).hexdigest()

def verify_pwd(p, h):
    return hash_pwd(p) == h

def safe(obj, key, default=""):
    if obj is None:
        return default
    return obj.get(key, default) if isinstance(obj, dict) else default

def format_amount(n, currency="XOF"):
    try:
        n = float(n or 0)
        if currency == "XOF":
            return f"{n:,.0f} FCFA".replace(",", " ")
        return f"{n:,.2f} {currency}"
    except Exception:
        return str(n)

# =============================================
# SESSION STATE
# =============================================

for k, v in {
    "logged_in": False, "user": None, "company": None,
    "page": "login", "dark_mode": False,
    "selected_invoice_id": None, "selected_client_id": None,
    "register_key": 0, "invoice_key": 0,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =============================================
# INIT DB
# =============================================

# BD Supabase: tables créées manuellement via SQL Editor

# =============================================
# CSS GLOBAL PROFESSIONNEL
# =============================================

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
:root {
    --font-sans:'DM Sans',system-ui,sans-serif;
    --font-mono:'DM Mono',monospace;
    --bg-base:#F0F2F5;
    --bg-surface:#FFFFFF;
    --bg-surface-2:#F7F8FA;
    --bg-sidebar:#1A1F2E;
    --border-color:#E2E6ED;
    --text-primary:#1A1F2E;
    --text-secondary:#5B6478;
    --text-muted:#9AA3B2;
    --text-on-dark:#FFFFFF;
    --color-brand:#1455C0;
    --color-brand-2:#0D3F99;
    --color-brand-light:#EBF1FD;
    --color-success:#0D8050;
    --color-success-light:#E6F5EE;
    --color-warning:#B06B00;
    --color-warning-light:#FFF4E0;
    --color-danger:#C0392B;
    --color-danger-light:#FDECEA;
    --shadow-sm:0 1px 3px rgba(0,0,0,0.06);
    --shadow-md:0 4px 12px rgba(0,0,0,0.08);
    --shadow-lg:0 10px 30px rgba(0,0,0,0.10);
    --radius-sm:6px;--radius-md:10px;--radius-lg:14px;--radius-xl:20px;
    --transition:all 0.2s cubic-bezier(0.4,0,0.2,1);
}
* { box-sizing:border-box; margin:0; padding:0; }
html, body, [data-testid="stApp"] {
    font-family:var(--font-sans) !important;
    background:var(--bg-base) !important;
    color:var(--text-primary) !important;
}
[data-testid="stSidebar"] { display:none !important; }
[data-testid="stToolbar"] { display:none !important; }
#MainMenu { display:none !important; }
footer { display:none !important; }
header { display:none !important; }
[data-testid="stMain"] { padding:0 !important; }
[data-testid="block-container"] { padding:0 !important; max-width:100% !important; }

.fp-shell {
    display:grid;
    grid-template-columns:240px 1fr;
    grid-template-rows:60px 1fr;
    height:100vh;
    overflow:hidden;
}

/* SIDEBAR */
.fp-sidebar {
    grid-row:1 / -1;
    background:var(--bg-sidebar);
    display:flex;
    flex-direction:column;
    overflow-y:auto;
    border-right:1px solid rgba(255,255,255,0.04);
    z-index:100;
}

.fp-sidebar::-webkit-scrollbar { width:3px; }
.fp-sidebar::-webkit-scrollbar-thumb { background:rgba(255,255,255,0.1); border-radius:2px; }

.fp-logo {
    padding:0 20px;
    height:60px;
    display:flex;
    align-items:center;
    border-bottom:1px solid rgba(255,255,255,0.05);
    flex-shrink:0;
    gap:12px;
}

.fp-logo-icon {
    width:34px; height:34px;
    background:var(--color-brand);
    border-radius:var(--radius-sm);
    display:flex; align-items:center; justify-content:center;
    font-size:18px;
    box-shadow:0 4px 12px rgba(20,85,192,0.4);
    flex-shrink:0;
}

.fp-logo-name {
    font-size:15px; font-weight:700; color:#fff;
    letter-spacing:-0.3px; line-height:1;
}

.fp-logo-sub {
    font-size:10px; color:#A8B2C8;
    letter-spacing:0.5px; text-transform:uppercase;
    margin-top:2px;
}

.fp-nav-label {
    padding:20px 20px 6px;
    font-size:10px; font-weight:600;
    color:#A8B2C8; letter-spacing:1px;
    text-transform:uppercase; opacity:0.6;
}

.fp-nav-item {
    margin:2px 10px;
    border-radius:var(--radius-sm);
}

.fp-nav-btn {
    display:flex; align-items:center;
    width:100%; padding:9px 12px;
    background:transparent; border:none;
    cursor:pointer; text-align:left;
    color:#A8B2C8; font-size:13px;
    font-family:var(--font-sans);
    border-radius:var(--radius-sm);
    transition:var(--transition);
    gap:10px;
}

.fp-nav-btn:hover { background:rgba(255,255,255,0.05); color:#fff; }
.fp-nav-btn.active { background:rgba(255,255,255,0.1); color:#fff; font-weight:600; }
.fp-nav-icon { width:20px; text-align:center; font-size:15px; flex-shrink:0; }

.fp-sidebar-footer {
    margin-top:auto;
    padding:16px;
    border-top:1px solid rgba(255,255,255,0.05);
}

.fp-avatar {
    width:36px; height:36px;
    border-radius:50%;
    background:var(--color-brand);
    display:flex; align-items:center; justify-content:center;
    color:#fff; font-weight:700; font-size:14px;
    flex-shrink:0;
}

/* TOPBAR */
.fp-topbar {
    background:var(--bg-surface);
    border-bottom:1px solid var(--border-color);
    display:flex; align-items:center;
    padding:0 24px; gap:16px;
    box-shadow:var(--shadow-sm);
    z-index:50;
}

.fp-topbar-title h2 {
    font-size:16px; font-weight:600;
    color:var(--text-primary);
    line-height:1;
}

.fp-topbar-title p {
    font-size:12px; color:var(--text-muted);
    margin-top:2px;
}

.fp-topbar-actions { margin-left:auto; display:flex; gap:8px; }

/* MAIN CONTENT */
.fp-main {
    overflow-y:auto;
    background:var(--bg-base);
    padding:24px;
}

.fp-main::-webkit-scrollbar { width:6px; }
.fp-main::-webkit-scrollbar-thumb { background:var(--border-color); border-radius:3px; }

/* CARDS */
.fp-card {
    background:var(--bg-surface);
    border-radius:var(--radius-lg);
    border:1px solid var(--border-color);
    box-shadow:var(--shadow-sm);
    overflow:hidden;
}

.fp-card-header {
    padding:16px 20px;
    border-bottom:1px solid var(--border-color);
    display:flex; align-items:center; gap:12px;
}

.fp-card-header h3 {
    font-size:14px; font-weight:600;
    color:var(--text-primary); flex:1;
}

.fp-card-body { padding:20px; }

/* KPI */
.fp-kpi {
    background:var(--bg-surface);
    border:1px solid var(--border-color);
    border-radius:var(--radius-lg);
    padding:20px;
    box-shadow:var(--shadow-sm);
}

.fp-kpi-label {
    font-size:11px; font-weight:600;
    color:var(--text-muted);
    text-transform:uppercase; letter-spacing:0.8px;
    margin-bottom:8px;
}

.fp-kpi-value {
    font-size:24px; font-weight:700;
    color:var(--text-primary);
    font-family:var(--font-mono);
    line-height:1;
}

.fp-kpi-sub {
    font-size:12px; color:var(--text-secondary);
    margin-top:6px;
}

.fp-kpi-icon {
    font-size:24px;
    margin-bottom:12px;
}

/* BADGES */
.badge {
    display:inline-flex; align-items:center;
    padding:3px 10px; border-radius:20px;
    font-size:11px; font-weight:600;
    letter-spacing:0.3px;
}
.badge-success { background:var(--color-success-light); color:var(--color-success); }
.badge-warning { background:var(--color-warning-light); color:var(--color-warning); }
.badge-danger  { background:var(--color-danger-light);  color:var(--color-danger); }
.badge-info    { background:var(--color-brand-light);    color:var(--color-brand); }
.badge-muted   { background:#F0F2F5; color:var(--text-muted); }

/* BUTTONS */
.btn-pf {
    display:inline-flex; align-items:center; gap:6px;
    padding:8px 16px; border-radius:var(--radius-sm);
    font-size:13px; font-weight:600;
    font-family:var(--font-sans);
    cursor:pointer; border:none;
    transition:var(--transition); text-decoration:none;
    white-space:nowrap;
}
.btn-primary { background:var(--color-brand); color:#fff; }
.btn-primary:hover { background:var(--color-brand-2); }
.btn-secondary { background:var(--bg-surface-2); color:var(--text-primary); border:1px solid var(--border-color); }
.btn-danger { background:var(--color-danger-light); color:var(--color-danger); }
.btn-success { background:var(--color-success-light); color:var(--color-success); }

/* TABLE */
.fp-table { width:100%; border-collapse:collapse; }
.fp-table th {
    text-align:left; padding:10px 14px;
    font-size:11px; font-weight:600;
    color:var(--text-muted); text-transform:uppercase;
    letter-spacing:0.8px;
    border-bottom:2px solid var(--border-color);
    background:var(--bg-surface-2);
}
.fp-table td {
    padding:12px 14px;
    font-size:13px; color:var(--text-primary);
    border-bottom:1px solid var(--border-color);
    vertical-align:middle;
}
.fp-table tr:hover td { background:var(--bg-surface-2); }

/* FORM */
.fp-label {
    display:block;
    font-size:12px; font-weight:600;
    color:var(--text-secondary); margin-bottom:6px;
    text-transform:uppercase; letter-spacing:0.5px;
}

.fp-input {
    width:100%; padding:9px 12px;
    border:1px solid var(--border-color);
    border-radius:var(--radius-sm);
    font-size:13px; font-family:var(--font-sans);
    background:var(--bg-surface);
    color:var(--text-primary);
    transition:var(--transition); outline:none;
}

.fp-input:focus {
    border-color:var(--color-brand);
    box-shadow:0 0 0 3px var(--color-brand-light);
}

/* LOGIN PAGE */
.fp-login-page {
    min-height:100vh;
    display:flex; align-items:center; justify-content:center;
    background:linear-gradient(135deg, #0D1B4B 0%, #1455C0 50%, #0D3F99 100%);
    padding:20px;
}

.fp-login-box {
    background:rgba(255,255,255,0.97);
    border-radius:var(--radius-xl);
    padding:48px 40px;
    width:100%; max-width:420px;
    box-shadow:0 30px 80px rgba(0,0,0,0.3);
}

.fp-login-logo {
    text-align:center; margin-bottom:32px;
}

.fp-login-logo .icon {
    width:56px; height:56px;
    background:var(--color-brand);
    border-radius:14px;
    display:flex; align-items:center; justify-content:center;
    font-size:28px;
    margin:0 auto 12px;
    box-shadow:0 8px 24px rgba(20,85,192,0.4);
}

.fp-login-logo h1 {
    font-size:22px; font-weight:800;
    color:var(--text-primary);
    letter-spacing:-0.5px;
}

.fp-login-logo p {
    font-size:13px; color:var(--text-secondary);
    margin-top:4px;
}

/* DIVIDER */
.fp-divider {
    height:1px; background:var(--border-color);
    margin:20px 0;
}

/* TOAST */
.fp-toast {
    position:fixed; top:20px; right:20px;
    padding:12px 20px; border-radius:var(--radius-md);
    font-size:13px; font-weight:600;
    box-shadow:var(--shadow-lg);
    z-index:9999; animation:slideIn 0.3s ease;
}

@keyframes slideIn {
    from { transform:translateX(100%); opacity:0; }
    to   { transform:translateX(0);    opacity:1; }
}

/* STATUS COLORS */
.status-paid     { color:var(--color-success); }
.status-unpaid   { color:var(--color-danger); }
.status-partial  { color:var(--color-warning); }
.status-draft    { color:var(--text-muted); }
.status-overdue  { color:var(--color-danger); font-weight:700; }

/* STREAMLIT OVERRIDES */
div[data-testid="stTextInput"] > div > div > input,
div[data-testid="stTextArea"] > div > div > textarea,
div[data-testid="stSelectbox"] > div > div > div {
    font-family:var(--font-sans) !important;
    border:1px solid var(--border-color) !important;
    border-radius:var(--radius-sm) !important;
    font-size:13px !important;
}

div[data-testid="stTextInput"] > div > div > input:focus {
    border-color:var(--color-brand) !important;
    box-shadow:0 0 0 3px var(--color-brand-light) !important;
}

.stButton > button {
    font-family:var(--font-sans) !important;
    font-weight:600 !important;
    border-radius:var(--radius-sm) !important;
    transition:var(--transition) !important;
}

.stButton > button[kind="primary"] {
    background:var(--color-brand) !important;
    border:none !important;
    color:#fff !important;
}

div[data-testid="stTabs"] [data-testid="stTab"] {
    font-family:var(--font-sans) !important;
    font-size:13px !important;
    font-weight:500 !important;
}
</style>
"""

# =============================================
# PAGES
# =============================================

def check_db():
    """Verifie et affiche etat BD"""
    if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
        st.error("SUPABASE_URL et SUPABASE_KEY manquants dans les secrets Streamlit!")
        st.code('''SUPABASE_URL = "https://XXXX.supabase.co"
SUPABASE_KEY = "votre_anon_key_supabase"''', language="toml")
        st.stop()
    if not db.is_connected():
        st.error("Impossible de se connecter a Supabase.")
        st.markdown("Verifiez SUPABASE_URL et SUPABASE_KEY dans Settings → Secrets")
        st.code("""SUPABASE_URL = \"https://XXXX.supabase.co\"
SUPABASE_KEY = \"votre_anon_key\"
""", language="toml")
        if st.button("Reessayer"):
            st.rerun()
        st.stop()


def page_login():
    st.markdown(THEME_CSS, unsafe_allow_html=True)
    st.markdown('''
    <div class="fp-login-page">
      <div class="fp-login-box" id="loginBox">
        <div class="fp-login-logo">
          <div class="icon">📊</div>
          <h1>FacturaPro</h1>
          <p>Systeme de Gestion Commerciale</p>
        </div>
      </div>
    </div>
    ''', unsafe_allow_html=True)

    # Formulaire Streamlit au-dessus du HTML
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br><br><br><br><br><br><br><br>", unsafe_allow_html=True)
        tab_login, tab_register = st.tabs(["🔐 Connexion", "📝 Inscription"])

        with tab_login:
            email = st.text_input("Email", placeholder="votre@email.com", key="login_email")
            pwd   = st.text_input("Mot de passe", type="password", key="login_pwd")

            if st.button("Se connecter", type="primary", use_container_width=True):
                if email and pwd:
                    user = db.f1("fp_users", {"email": email.lower(), "status": "actif"})
                    if user and verify_pwd(pwd, safe(user, "password_hash")):
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        company_id = safe(user, "company_id")
                        if company_id:
                            st.session_state.company = db.f1("fp_companies", {"id": company_id})
                        st.session_state.page = "dashboard"
                        st.rerun()
                    else:
                        st.error("Email ou mot de passe incorrect")
                else:
                    st.warning("Remplissez tous les champs")

        with tab_register:
            with st.form(f"reg_{st.session_state.register_key}", border=False):
                c1, c2 = st.columns(2)
                with c1: nom    = st.text_input("Nom *")
                with c2: prenom = st.text_input("Prenom *")
                reg_email  = st.text_input("Email *", placeholder="votre@email.com")
                company_nm = st.text_input("Nom de la Societe *", placeholder="Ex: Ma Societe SARL")
                reg_pwd    = st.text_input("Mot de passe *", type="password", placeholder="Min. 8 caracteres")
                reg_pwd2   = st.text_input("Confirmer le mot de passe *", type="password")

                if st.form_submit_button("Creer mon compte", use_container_width=True, type="primary"):
                    if not all([nom, prenom, reg_email, company_nm, reg_pwd]):
                        st.error("Tous les champs sont obligatoires")
                    elif len(reg_pwd) < 8:
                        st.error("Mot de passe trop court (minimum 8 caracteres)")
                    elif reg_pwd != reg_pwd2:
                        st.error("Les mots de passe ne correspondent pas")
                    else:
                        # Creer la societe
                        co_id = db.q_id("INSERT INTO fp_companies (name, currency) VALUES (?, ?)", (company_nm, "XOF"))
                        if co_id:
                            # Creer l'utilisateur admin
                            u_id = db.q_id(
                                "INSERT INTO fp_users (nom, prenom, email, password_hash, role, company_id) VALUES (?,?,?,?,?,?)",
                                (nom, prenom, reg_email.lower(), hash_pwd(reg_pwd), "admin", co_id)
                            )
                            if u_id:
                                # Mettre a jour owner
                                db.q("UPDATE fp_companies SET owner_id=? WHERE id=?", (u_id, co_id))
                                st.success("Compte cree! Connectez-vous.")
                                st.session_state.register_key += 1
                                st.rerun()
                            else:
                                st.error("Cet email est deja utilise")
                        else:
                            st.error("Erreur lors de la creation")


def sidebar_nav():
    """Retourne la page selectionnee via la sidebar"""
    company = st.session_state.company
    user = st.session_state.user
    company_name = safe(company, "name", "FacturaPro") if company else "FacturaPro"
    user_name = f"{safe(user,'prenom')} {safe(user,'nom')}" if user else "Utilisateur"
    avatar = user_name[0].upper() if user_name else "U"

    pages = [
        ("📊", "Tableau de Bord", "dashboard"),
        ("✏️", "Nouvelle Facture", "new_invoice"),
        ("📋", "Factures", "invoices"),
        ("💳", "Paiements", "payments"),
        ("👥", "Clients", "clients"),
        ("📦", "Produits/Services", "products"),
        ("📈", "Rapports", "reports"),
        ("⚙️", "Parametres", "settings"),
    ]

    if safe(user, "role") == "admin":
        pages.append(("👨‍💼", "Utilisateurs", "users"))

    nav_html = f'''
    <div class="fp-logo">
      <div class="fp-logo-icon">📊</div>
      <div>
        <div class="fp-logo-name">FacturaPro</div>
        <div class="fp-logo-sub">{company_name[:20]}</div>
      </div>
    </div>
    <div class="fp-nav-label">Navigation</div>
    '''
    for icon, label, pid in pages:
        active = "active" if st.session_state.page == pid else ""
        nav_html += f'<div class="fp-nav-item"><div class="fp-nav-btn {active}" onclick="void(0)"><span class="fp-nav-icon">{icon}</span>{label}</div></div>'

    nav_html += f'''
    <div class="fp-sidebar-footer">
      <div style="display:flex;align-items:center;gap:10px;">
        <div class="fp-avatar">{avatar}</div>
        <div>
          <div style="font-size:13px;font-weight:600;color:#fff;">{user_name[:20]}</div>
          <div style="font-size:11px;color:#A8B2C8;">{safe(user,"role","user").capitalize()}</div>
        </div>
      </div>
    </div>
    '''
    return pages, nav_html


def status_badge(status):
    m = {
        "paid": ("<span class='badge badge-success'>Paye</span>"),
        "partial": ("<span class='badge badge-warning'>Partiel</span>"),
        "unpaid": ("<span class='badge badge-danger'>Impaye</span>"),
        "draft": ("<span class='badge badge-muted'>Brouillon</span>"),
        "overdue": ("<span class='badge badge-danger'>En retard</span>"),
        "cancelled": ("<span class='badge badge-muted'>Annule</span>"),
    }
    return m.get(status, f"<span class='badge badge-muted'>{status}</span>")


def page_dashboard():
    cid = safe(st.session_state.company, "id")
    currency = safe(st.session_state.company, "currency", "XOF")
    if not cid:
        st.error("Aucune societe liee. Reconnectez-vous.")
        return

    # Stats
    invoices = db.fa("fp_invoices", {"company_id": cid})
    clients  = db.fa("fp_clients",  {"company_id": cid})
    payments = db.fa("fp_payments", {"company_id": cid})

    total_ca    = sum(safe(i, "total", 0) for i in invoices)
    total_paid  = sum(safe(i, "amount_paid", 0) for i in invoices)
    total_unpaid= total_ca - total_paid
    nb_clients  = len(clients)
    nb_invoices = len(invoices)

    st.markdown("<h2 style='margin-bottom:24px;font-size:20px;font-weight:700;'>Tableau de Bord</h2>", unsafe_allow_html=True)

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f'''
        <div class="fp-kpi">
          <div class="fp-kpi-icon">💰</div>
          <div class="fp-kpi-label">Chiffre d'Affaires</div>
          <div class="fp-kpi-value">{format_amount(total_ca, currency)}</div>
          <div class="fp-kpi-sub">{nb_invoices} facture(s)</div>
        </div>''', unsafe_allow_html=True)
    with k2:
        st.markdown(f'''
        <div class="fp-kpi">
          <div class="fp-kpi-icon">✅</div>
          <div class="fp-kpi-label">Encaisse</div>
          <div class="fp-kpi-value" style="color:var(--color-success);">{format_amount(total_paid, currency)}</div>
          <div class="fp-kpi-sub">{len([i for i in invoices if safe(i,"status")=="paid"])} facture(s) soldee(s)</div>
        </div>''', unsafe_allow_html=True)
    with k3:
        st.markdown(f'''
        <div class="fp-kpi">
          <div class="fp-kpi-icon">⏳</div>
          <div class="fp-kpi-label">Reste a Encaisser</div>
          <div class="fp-kpi-value" style="color:var(--color-danger);">{format_amount(total_unpaid, currency)}</div>
          <div class="fp-kpi-sub">{len([i for i in invoices if safe(i,"status") in ["unpaid","partial","overdue"]])} facture(s) en cours</div>
        </div>''', unsafe_allow_html=True)
    with k4:
        st.markdown(f'''
        <div class="fp-kpi">
          <div class="fp-kpi-icon">👥</div>
          <div class="fp-kpi-label">Clients</div>
          <div class="fp-kpi-value">{nb_clients}</div>
          <div class="fp-kpi-sub">clients actifs</div>
        </div>''', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("#### Dernieres Factures")
        recent = sorted(invoices, key=lambda x: str(safe(x,"created_at","")), reverse=True)[:10]
        if recent:
            table = '<table class="fp-table"><thead><tr><th>N°</th><th>Client</th><th>Date</th><th>Montant</th><th>Statut</th></tr></thead><tbody>'
            for inv in recent:
                table += f'''<tr>
                  <td style="font-family:var(--font-mono);font-weight:600;">{safe(inv,"number")}</td>
                  <td>{safe(inv,"client_name","—")}</td>
                  <td style="color:var(--text-muted);">{str(safe(inv,"date_issue","—"))[:10]}</td>
                  <td style="font-family:var(--font-mono);font-weight:600;">{format_amount(safe(inv,"total",0), currency)}</td>
                  <td>{status_badge(safe(inv,"status","draft"))}</td>
                </tr>'''
            table += "</tbody></table>"
            st.markdown('<div class="fp-card"><div class="fp-card-body">' + table + '</div></div>', unsafe_allow_html=True)
        else:
            st.info("Aucune facture. Creez votre premiere facture!")

        if st.button("+ Nouvelle Facture", type="primary"):
            st.session_state.page = "new_invoice"
            st.rerun()

    with col_right:
        st.markdown("#### Derniers Clients")
        recent_clients = sorted(clients, key=lambda x: safe(x,"created_at",""), reverse=True)[:5]
        if recent_clients:
            for cl in recent_clients:
                st.markdown(f'''
                <div style="padding:12px;border-bottom:1px solid var(--border-color);">
                  <div style="font-weight:600;font-size:13px;">{safe(cl,"name","—")}</div>
                  <div style="font-size:12px;color:var(--text-muted);">{safe(cl,"tel","—")} · {safe(cl,"email","—")}</div>
                </div>''', unsafe_allow_html=True)
        else:
            st.info("Aucun client enregistre.")

        if st.button("+ Nouveau Client"):
            st.session_state.page = "clients"
            st.rerun()


def page_new_invoice():
    cid = safe(st.session_state.company, "id")
    currency = safe(st.session_state.company, "currency", "XOF")
    if not cid:
        return

    st.markdown("#### Nouvelle Facture")

    # Recup numero suivant
    company = db.f1("fp_companies", {"id": cid})
    prefix = safe(company, "numbering_prefix", "FAC")
    seq = safe(company, "numbering_seq", 1)
    invoice_number = f"{prefix}-{str(seq).zfill(4)}"

    clients = db.fa("fp_clients", {"company_id": cid})
    products = db.fa("fp_products", {"company_id": cid, "active": 1})

    if "invoice_lines" not in st.session_state:
        st.session_state.invoice_lines = [{"desc": "", "qty": 1, "price": 0, "tax": 0, "disc": 0}]

    with st.form(f"new_inv_{st.session_state.invoice_key}", border=False):
        st.markdown('<div class="fp-card"><div class="fp-card-header"><h3>Informations Generales</h3></div><div class="fp-card-body">', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            inv_type = st.selectbox("Type", ["Facture", "Bon de Livraison", "Devis", "Avoir"], key="inv_type")
        with col2:
            date_issue = st.date_input("Date d'emission", value=date.today(), key="inv_date")
        with col3:
            date_due = st.date_input("Date d'echeance", key="inv_due")

        # Client
        client_names = ["-- Saisir un client --"] + [safe(c, "name") for c in clients]
        client_sel = st.selectbox("Client", client_names, key="inv_client")

        col_addr1, col_addr2 = st.columns(2)
        with col_addr1:
            client_name_free = st.text_input("Nom client (libre)", placeholder="Si non enregistre", key="inv_cname")
        with col_addr2:
            client_addr_free = st.text_input("Adresse client", key="inv_caddr")

        st.markdown('</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # LIGNES
        st.markdown('<div class="fp-card"><div class="fp-card-header"><h3>Lignes de Facture</h3></div><div class="fp-card-body">', unsafe_allow_html=True)

        lines_data = []
        subtotal = 0
        tax_total = 0

        col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns([5, 1.5, 2, 1.5, 1.5])
        with col_h1: st.markdown("<small><b>DESCRIPTION</b></small>", unsafe_allow_html=True)
        with col_h2: st.markdown("<small><b>QTE</b></small>", unsafe_allow_html=True)
        with col_h3: st.markdown("<small><b>PRIX UNIT.</b></small>", unsafe_allow_html=True)
        with col_h4: st.markdown("<small><b>REMISE %</b></small>", unsafe_allow_html=True)
        with col_h5: st.markdown("<small><b>TOTAL</b></small>", unsafe_allow_html=True)

        for i, line in enumerate(st.session_state.invoice_lines):
            c1, c2, c3, c4, c5 = st.columns([5, 1.5, 2, 1.5, 1.5])
            with c1: desc = st.text_input("", value=line.get("desc",""), key=f"ldesc_{i}", placeholder="Description de la ligne...")
            with c2: qty  = st.number_input("", value=float(line.get("qty",1)), min_value=0.0, key=f"lqty_{i}", step=1.0, format="%.2f")
            with c3: price= st.number_input("", value=float(line.get("price",0)), min_value=0.0, key=f"lprice_{i}", step=100.0, format="%.0f")
            with c4: disc = st.number_input("", value=float(line.get("disc",0)), min_value=0.0, max_value=100.0, key=f"ldisc_{i}", step=0.5, format="%.1f")
            line_total = qty * price * (1 - disc / 100)
            with c5: st.markdown(f"<div style='padding-top:28px;font-weight:700;font-family:var(--font-mono);'>{format_amount(line_total, currency)}</div>", unsafe_allow_html=True)
            lines_data.append({"desc": desc, "qty": qty, "price": price, "disc": disc, "total": line_total})
            subtotal += line_total

        col_actions = st.columns([1, 1, 4])
        with col_actions[0]:
            if st.form_submit_button("+ Ligne"):
                st.session_state.invoice_lines.append({"desc": "", "qty": 1, "price": 0, "disc": 0})
                st.rerun()
        with col_actions[1]:
            if len(st.session_state.invoice_lines) > 1:
                if st.form_submit_button("- Ligne"):
                    st.session_state.invoice_lines.pop()
                    st.rerun()

        st.markdown("---")

        col_tot1, col_tot2 = st.columns([3, 2])
        with col_tot2:
            tva_rate = st.number_input("TVA/Taxe (%)", value=18.0, min_value=0.0, max_value=100.0, step=0.5, key="inv_tva")
            tax_total = subtotal * tva_rate / 100
            total_ttc = subtotal + tax_total
            st.markdown(f'''
            <div style="background:var(--bg-surface-2);padding:16px;border-radius:var(--radius-md);border:1px solid var(--border-color);">
              <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                <span style="color:var(--text-secondary);">Sous-total HT</span>
                <span style="font-family:var(--font-mono);font-weight:600;">{format_amount(subtotal, currency)}</span>
              </div>
              <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                <span style="color:var(--text-secondary);">TVA ({tva_rate:.0f}%)</span>
                <span style="font-family:var(--font-mono);font-weight:600;">{format_amount(tax_total, currency)}</span>
              </div>
              <div style="display:flex;justify-content:space-between;padding-top:8px;border-top:2px solid var(--border-color);">
                <span style="font-weight:700;font-size:15px;">TOTAL TTC</span>
                <span style="font-family:var(--font-mono);font-weight:800;font-size:16px;color:var(--color-brand);">{format_amount(total_ttc, currency)}</span>
              </div>
            </div>
            ''', unsafe_allow_html=True)

        st.markdown('</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        notes = st.text_area("Notes / Conditions", placeholder="Conditions de paiement, mentions legales...", height=80, key="inv_notes")
        payment_terms = st.selectbox("Conditions de paiement", ["Comptant", "30 jours", "60 jours", "90 jours"], key="inv_terms")

        col_save1, col_save2, col_save3 = st.columns([2, 2, 6])
        with col_save1:
            save_btn = st.form_submit_button("💾 Enregistrer", type="primary", use_container_width=True)
        with col_save2:
            draft_btn = st.form_submit_button("📝 Brouillon", use_container_width=True)

        if save_btn or draft_btn:
            status = "unpaid" if save_btn else "draft"
            # Determiner client
            final_client_name = client_name_free
            final_client_addr = client_addr_free
            final_client_id   = None
            if client_sel != "-- Saisir un client --":
                cl = next((c for c in clients if safe(c,"name") == client_sel), None)
                if cl:
                    final_client_id   = safe(cl, "id")
                    final_client_name = safe(cl, "name")
                    final_client_addr = safe(cl, "address", "")

            inv = db.insert("fp_invoices", {
                "company_id": cid, "number": invoice_number, "type": inv_type,
                "client_id": final_client_id, "client_name": final_client_name,
                "client_address": final_client_addr,
                "date_issue": str(date_issue), "date_due": str(date_due),
                "status": status, "subtotal": subtotal, "tax_total": tax_total,
                "total": total_ttc, "notes": notes, "payment_terms": payment_terms,
                "created_by": safe(st.session_state.user, "id")
            })
            inv_id = safe(inv, "id") if inv else None

            if inv_id:
                for pos, line in enumerate(lines_data):
                    db.insert("fp_invoice_lines", {
                        "invoice_id": inv_id, "position": pos,
                        "description": line["desc"], "quantity": line["qty"],
                        "unit_price": line["price"], "discount_pct": line["disc"],
                        "total": line["total"]
                    })
                # Incrementer sequence
                new_seq = int(safe(company, "numbering_seq", 1)) + 1
                db.update("fp_companies", {"numbering_seq": new_seq}, {"id": cid})

                st.success(f"Facture {invoice_number} enregistree!")
                st.session_state.invoice_lines = [{"desc": "", "qty": 1, "price": 0, "disc": 0}]
                st.session_state.invoice_key += 1
                st.session_state.page = "invoices"
                st.rerun()
            else:
                st.error("Erreur lors de l'enregistrement")


def page_invoices():
    cid = safe(st.session_state.company, "id")
    currency = safe(st.session_state.company, "currency", "XOF")

    col_t, col_btn = st.columns([4, 2])
    with col_t:
        st.markdown("#### Factures")
    with col_btn:
        if st.button("+ Nouvelle Facture", type="primary"):
            st.session_state.page = "new_invoice"
            st.rerun()

    # Filtres
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        search = st.text_input("Rechercher", placeholder="N° facture, client...", key="inv_search")
    with col_f2:
        filter_status = st.selectbox("Statut", ["Tous", "draft", "unpaid", "partial", "paid", "overdue"], key="inv_fstatus")
    with col_f3:
        filter_type = st.selectbox("Type", ["Tous", "Facture", "Devis", "Bon de Livraison", "Avoir"], key="inv_ftype")

    invoices = db.fa("fp_invoices", {"company_id": cid})
    invoices = sorted(invoices, key=lambda x: str(safe(x,"created_at","")), reverse=True)

    # Appliquer filtres
    if search:
        invoices = [i for i in invoices if search.lower() in safe(i,"number","").lower() or search.lower() in safe(i,"client_name","").lower()]
    if filter_status != "Tous":
        invoices = [i for i in invoices if safe(i,"status") == filter_status]
    if filter_type != "Tous":
        invoices = [i for i in invoices if safe(i,"type") == filter_type]

    if invoices:
        table_html = '<div class="fp-card"><table class="fp-table"><thead><tr><th>N° FACTURE</th><th>TYPE</th><th>CLIENT</th><th>DATE</th><th>TOTAL TTC</th><th>REGLE</th><th>STATUT</th></tr></thead><tbody>'
        for inv in invoices:
            total = safe(inv, "total", 0)
            paid  = safe(inv, "amount_paid", 0)
            table_html += f'''<tr>
              <td style="font-family:var(--font-mono);font-weight:700;">{safe(inv,"number","—")}</td>
              <td><span class="badge badge-info">{safe(inv,"type","—")}</span></td>
              <td>{safe(inv,"client_name","Client libre")}</td>
              <td style="color:var(--text-muted);">{str(safe(inv,"date_issue","—"))[:10]}</td>
              <td style="font-family:var(--font-mono);font-weight:600;">{format_amount(total, currency)}</td>
              <td style="font-family:var(--font-mono);color:var(--color-success);">{format_amount(paid, currency)}</td>
              <td>{status_badge(safe(inv,"status","draft"))}</td>
            </tr>'''
        table_html += '</tbody></table></div>'
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("Aucune facture trouvee.")

    # Action paiement rapide
    st.markdown("---")
    st.markdown("#### Enregistrer un Paiement")
    all_inv = db.fa("fp_invoices", {"company_id": cid})
    inv_nums = [safe(i, "number") for i in all_inv if safe(i,"status") in ["unpaid","partial"]]
    if inv_nums:
        with st.form("quick_payment", border=False):
            cp1, cp2, cp3 = st.columns(3)
            with cp1: pay_inv  = st.selectbox("Facture", inv_nums)
            with cp2: pay_amt  = st.number_input("Montant", min_value=0.0, step=1000.0)
            with cp3: pay_meth = st.selectbox("Methode", ["Especes","Virement","Cheque","Mobile Money","Carte"])
            pay_ref  = st.text_input("Reference", placeholder="N° cheque, reference virement...")
            pay_date = st.date_input("Date paiement", value=date.today())

            if st.form_submit_button("Valider le Paiement", type="primary"):
                inv_list = [i for i in all_inv if safe(i,"number") == pay_inv]
                inv = inv_list[0] if inv_list else None
                if inv and pay_amt > 0:
                    db.insert("fp_payments", {
                        "invoice_id": safe(inv,"id"), "company_id": cid,
                        "amount": pay_amt, "method": pay_meth,
                        "reference": pay_ref, "date_payment": str(pay_date)
                    })
                    new_paid = float(safe(inv, "amount_paid", 0) or 0) + pay_amt
                    new_status = "paid" if new_paid >= float(safe(inv, "total", 0) or 0) else "partial"
                    db.update("fp_invoices", {"amount_paid": new_paid, "status": new_status}, {"id": safe(inv,"id")})
                    st.success(f"Paiement de {format_amount(pay_amt, currency)} enregistre!")
                    st.rerun()
    else:
        st.info("Aucune facture en attente de paiement.")


def page_clients():
    cid = safe(st.session_state.company, "id")

    col_t, col_btn = st.columns([4, 2])
    with col_t:
        st.markdown("#### Clients")
    with col_btn:
        show_form = st.button("+ Nouveau Client", type="primary")

    if show_form or st.session_state.get("show_client_form"):
        st.session_state.show_client_form = True
        st.markdown("##### Ajouter un Client")
        with st.form("new_client_form", border=False):
            c1, c2 = st.columns(2)
            with c1:
                cl_name  = st.text_input("Nom / Raison Sociale *")
                cl_tel   = st.text_input("Telephone")
                cl_ifu   = st.text_input("IFU")
            with c2:
                cl_email = st.text_input("Email")
                cl_addr  = st.text_input("Adresse")
                cl_rccm  = st.text_input("RCCM")
            cl_notes = st.text_area("Notes", height=60)
            cl_terms = st.selectbox("Conditions de paiement", ["Comptant", "30 jours", "60 jours", "90 jours"])

            col_sb1, col_sb2 = st.columns(2)
            with col_sb1:
                submitted = st.form_submit_button("Enregistrer", type="primary", use_container_width=True)
            with col_sb2:
                if st.form_submit_button("Annuler", use_container_width=True):
                    st.session_state.show_client_form = False
                    st.rerun()

            if submitted:
                if cl_name:
                    row = db.insert("fp_clients", {
                        "company_id": cid, "name": cl_name, "email": cl_email,
                        "tel": cl_tel, "address": cl_addr, "ifu": cl_ifu,
                        "rccm": cl_rccm, "notes": cl_notes, "payment_terms": cl_terms
                    })
                    if row:
                        st.success(f"Client {cl_name} ajoute!")
                        st.session_state.show_client_form = False
                        st.rerun()
                    else:
                        st.error("Erreur lors de l'ajout")
                else:
                    st.error("Le nom est obligatoire")

    # Liste des clients
    search_cl = st.text_input("Rechercher un client", placeholder="Nom, email, telephone...")
    clients = sorted(db.fa("fp_clients", {"company_id": cid}), key=lambda x: safe(x,"name",""))
    if search_cl:
        clients = [c for c in clients if search_cl.lower() in safe(c,"name","").lower() or search_cl.lower() in safe(c,"email","").lower()]

    if clients:
        table_html = '<div class="fp-card"><table class="fp-table"><thead><tr><th>NOM / SOCIETE</th><th>TELEPHONE</th><th>EMAIL</th><th>IFU</th><th>CONDITIONS</th></tr></thead><tbody>'
        for cl in clients:
            table_html += f'''<tr>
              <td style="font-weight:600;">{safe(cl,"name","—")}</td>
              <td style="color:var(--text-muted);">{safe(cl,"tel","—")}</td>
              <td style="color:var(--color-brand);">{safe(cl,"email","—")}</td>
              <td style="font-family:var(--font-mono);">{safe(cl,"ifu","—")}</td>
              <td><span class="badge badge-info">{safe(cl,"payment_terms","—")}</span></td>
            </tr>'''
        table_html += '</tbody></table></div>'
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("Aucun client enregistre. Ajoutez votre premier client!")


def page_products():
    cid = safe(st.session_state.company, "id")
    currency = safe(st.session_state.company, "currency", "XOF")

    col_t, col_btn = st.columns([4, 2])
    with col_t:
        st.markdown("#### Produits & Services")
    with col_btn:
        if st.button("+ Nouveau Produit", type="primary"):
            st.session_state.show_product_form = True

    if st.session_state.get("show_product_form"):
        with st.form("new_product_form", border=False):
            c1, c2 = st.columns(2)
            with c1:
                p_code  = st.text_input("Code")
                p_name  = st.text_input("Designation *")
                p_unit  = st.selectbox("Unite", ["u", "kg", "l", "m", "m2", "m3", "h", "forfait", "lot"])
            with c2:
                p_price = st.number_input("Prix Unitaire", min_value=0.0, step=100.0)
                p_tax   = st.number_input("Taux de Taxe (%)", min_value=0.0, max_value=100.0, value=18.0)
                p_cat   = st.text_input("Categorie")
            p_desc = st.text_area("Description", height=60)

            col_pb1, col_pb2 = st.columns(2)
            with col_pb1:
                if st.form_submit_button("Enregistrer", type="primary", use_container_width=True):
                    if p_name:
                        db.insert("fp_products", {
                            "company_id": cid, "code": p_code, "name": p_name,
                            "description": p_desc, "unit": p_unit, "price": p_price,
                            "tax_rate": p_tax, "category": p_cat
                        })
                        st.success(f"Produit {p_name} ajoute!")
                        st.session_state.show_product_form = False
                        st.rerun()
            with col_pb2:
                if st.form_submit_button("Annuler", use_container_width=True):
                    st.session_state.show_product_form = False
                    st.rerun()

    products = sorted(db.fa("fp_products", {"company_id": cid}), key=lambda x: safe(x,"name",""))
    if products:
        table_html = '<div class="fp-card"><table class="fp-table"><thead><tr><th>CODE</th><th>DESIGNATION</th><th>UNITE</th><th>PRIX HT</th><th>TAXE</th><th>CATEGORIE</th></tr></thead><tbody>'
        for p in products:
            table_html += f'''<tr>
              <td style="font-family:var(--font-mono);">{safe(p,"code","—")}</td>
              <td style="font-weight:600;">{safe(p,"name","—")}</td>
              <td><span class="badge badge-muted">{safe(p,"unit","u")}</span></td>
              <td style="font-family:var(--font-mono);font-weight:600;">{format_amount(safe(p,"price",0), currency)}</td>
              <td style="color:var(--text-secondary);">{safe(p,"tax_rate",0):.0f}%</td>
              <td>{safe(p,"category","—")}</td>
            </tr>'''
        table_html += '</tbody></table></div>'
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("Aucun produit. Ajoutez votre catalogue!")


def page_reports():
    cid = safe(st.session_state.company, "id")
    currency = safe(st.session_state.company, "currency", "XOF")

    st.markdown("#### Rapports & Analyses")

    invoices = db.fa("fp_invoices", {"company_id": cid})
    payments = db.fa("fp_payments", {"company_id": cid})

    # Stats globales
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'''<div class="fp-kpi"><div class="fp-kpi-icon">📋</div>
        <div class="fp-kpi-label">Total Factures</div>
        <div class="fp-kpi-value">{len(invoices)}</div></div>''', unsafe_allow_html=True)
    with col2:
        ca = sum(safe(i,"total",0) for i in invoices)
        st.markdown(f'''<div class="fp-kpi"><div class="fp-kpi-icon">💰</div>
        <div class="fp-kpi-label">CA Total</div>
        <div class="fp-kpi-value">{format_amount(ca, currency)}</div></div>''', unsafe_allow_html=True)
    with col3:
        encaisse = sum(safe(i,"amount_paid",0) for i in invoices)
        st.markdown(f'''<div class="fp-kpi"><div class="fp-kpi-icon">✅</div>
        <div class="fp-kpi-label">Encaisse</div>
        <div class="fp-kpi-value" style="color:var(--color-success);">{format_amount(encaisse, currency)}</div></div>''', unsafe_allow_html=True)
    with col4:
        impaye = ca - encaisse
        st.markdown(f'''<div class="fp-kpi"><div class="fp-kpi-icon">⏳</div>
        <div class="fp-kpi-label">Impaye</div>
        <div class="fp-kpi-value" style="color:var(--color-danger);">{format_amount(impaye, currency)}</div></div>''', unsafe_allow_html=True)

    st.markdown("---")

    # Par statut
    st.markdown("##### Repartition par Statut")
    from collections import Counter
    statuts = Counter(safe(i,"status","draft") for i in invoices)
    for status, count in statuts.items():
        total_s = sum(safe(i,"total",0) for i in invoices if safe(i,"status") == status)
        col_r1, col_r2, col_r3 = st.columns([2,3,2])
        with col_r1: st.markdown(status_badge(status), unsafe_allow_html=True)
        with col_r2: st.progress(count / len(invoices) if invoices else 0)
        with col_r3: st.markdown(f"**{count}** — {format_amount(total_s, currency)}")

    # Paiements recents
    st.markdown("---")
    st.markdown("##### Derniers Reglements")
    if payments:
        table_html = '<div class="fp-card"><table class="fp-table"><thead><tr><th>DATE</th><th>MONTANT</th><th>METHODE</th><th>REFERENCE</th></tr></thead><tbody>'
        for p in sorted(payments, key=lambda x: safe(x,"created_at",""), reverse=True)[:10]:
            table_html += f'''<tr>
              <td>{str(safe(p,"date_payment","—"))[:10]}</td>
              <td style="font-family:var(--font-mono);font-weight:700;color:var(--color-success);">+{format_amount(safe(p,"amount",0), currency)}</td>
              <td><span class="badge badge-info">{safe(p,"method","—")}</span></td>
              <td style="font-family:var(--font-mono);color:var(--text-muted);">{safe(p,"reference","—")}</td>
            </tr>'''
        table_html += '</tbody></table></div>'
        st.markdown(table_html, unsafe_allow_html=True)


def page_settings():
    cid = safe(st.session_state.company, "id")
    company = db.f1("fp_companies", {"id": cid}) if cid else None

    st.markdown("#### Parametres de la Societe")

    with st.form("settings_form", border=False):
        st.markdown("##### Informations Generales")
        c1, c2 = st.columns(2)
        with c1:
            co_name    = st.text_input("Raison Sociale", value=safe(company,"name",""))
            co_tel     = st.text_input("Telephone", value=safe(company,"tel",""))
            co_ifu     = st.text_input("IFU", value=safe(company,"ifu",""))
            co_rccm    = st.text_input("RCCM", value=safe(company,"rccm",""))
        with c2:
            co_email   = st.text_input("Email", value=safe(company,"email",""))
            co_website = st.text_input("Site Web", value=safe(company,"website",""))
            co_bank    = st.text_input("Banque", value=safe(company,"bank",""))
            co_account = st.text_input("N° Compte Bancaire", value=safe(company,"bank_account",""))
        co_address = st.text_area("Adresse", value=safe(company,"address",""), height=80)
        co_currency = st.selectbox("Devise", ["XOF", "EUR", "USD", "GHS", "NGN", "MAD", "TND"],
                                   index=["XOF","EUR","USD","GHS","NGN","MAD","TND"].index(safe(company,"currency","XOF")) if safe(company,"currency","XOF") in ["XOF","EUR","USD","GHS","NGN","MAD","TND"] else 0)

        st.markdown("##### Numerotation")
        c3, c4 = st.columns(2)
        with c3:
            co_prefix = st.text_input("Prefixe Facture", value=safe(company,"numbering_prefix","FAC"))
        with c4:
            co_seq = st.number_input("Sequence actuelle", value=int(safe(company,"numbering_seq",1) or 1), min_value=1)

        if st.form_submit_button("Sauvegarder", type="primary", use_container_width=True):
            if cid:
                db.update("fp_companies", {
                    "name": co_name, "email": co_email, "tel": co_tel,
                    "address": co_address, "website": co_website, "ifu": co_ifu,
                    "rccm": co_rccm, "bank": co_bank, "bank_account": co_account,
                    "currency": co_currency, "numbering_prefix": co_prefix, "numbering_seq": co_seq
                }, {"id": cid})
                st.session_state.company = db.f1("fp_companies", {"id": cid})
                st.success("Parametres sauvegardes!")


def page_users():
    cid = safe(st.session_state.company, "id")
    st.markdown("#### Gestion des Utilisateurs")

    users = sorted(db.fa("fp_users", {"company_id": cid}), key=lambda x: str(safe(x,"created_at","")), reverse=True)

    with st.form("new_user_form", border=False):
        st.markdown("##### Ajouter un Utilisateur")
        c1, c2, c3 = st.columns(3)
        with c1:
            u_nom    = st.text_input("Nom")
            u_prenom = st.text_input("Prenom")
        with c2:
            u_email  = st.text_input("Email")
            u_role   = st.selectbox("Role", ["user", "admin", "viewer"])
        with c3:
            u_pwd    = st.text_input("Mot de passe", type="password", placeholder="Min. 8 car.")

        if st.form_submit_button("Ajouter", type="primary"):
            if u_email and u_pwd and u_nom:
                db.insert("fp_users", {
                    "nom": u_nom, "prenom": u_prenom,
                    "email": u_email.lower(), "password_hash": hash_pwd(u_pwd),
                    "role": u_role, "company_id": cid, "status": "actif"
                })
                st.success("Utilisateur ajoute!")
                st.rerun()

    st.markdown("---")
    if users:
        table_html = '<div class="fp-card"><table class="fp-table"><thead><tr><th>NOM</th><th>EMAIL</th><th>ROLE</th><th>STATUT</th><th>DATE CREATION</th></tr></thead><tbody>'
        for u in users:
            role_badge = {"admin": "badge-danger", "viewer": "badge-muted"}.get(safe(u,"role","user"), "badge-info")
            table_html += f'''<tr>
              <td style="font-weight:600;">{safe(u,"prenom","")} {safe(u,"nom","—")}</td>
              <td style="color:var(--color-brand);">{safe(u,"email","—")}</td>
              <td><span class="badge {role_badge}">{safe(u,"role","user").capitalize()}</span></td>
              <td>{'<span class="badge badge-success">Actif</span>' if safe(u,"status")=="actif" else '<span class="badge badge-danger">Bloque</span>'}</td>
              <td style="color:var(--text-muted);">{str(safe(u,"created_at","—"))[:10]}</td>
            </tr>'''
        table_html += '</tbody></table></div>'
        st.markdown(table_html, unsafe_allow_html=True)


# =============================================
# MAIN ROUTER
# =============================================

def main():
    st.markdown(THEME_CSS, unsafe_allow_html=True)

    # Verifier BD
    check_db()

    if not st.session_state.logged_in:
        page_login()
        return

    # LAYOUT PRINCIPAL
    pages, nav_html = sidebar_nav()

    # Titre de la page courante
    page_titles = {
        "dashboard":   ("Tableau de Bord", "Vue d'ensemble de l'activite"),
        "new_invoice": ("Nouvelle Facture", "Creer un document commercial"),
        "invoices":    ("Factures", "Gestion et suivi des factures"),
        "payments":    ("Paiements", "Suivi des encaissements"),
        "clients":     ("Clients", "Fiches clients et historique"),
        "products":    ("Produits & Services", "Catalogue et tarification"),
        "reports":     ("Rapports", "Analyses et statistiques"),
        "settings":    ("Parametres", "Configuration de votre societe"),
        "users":       ("Utilisateurs", "Gestion des acces"),
    }
    curr_page = st.session_state.page
    page_title, page_sub = page_titles.get(curr_page, ("FacturaPro", ""))

    # HTML SHELL (sidebar + topbar)
    shell_html = f'''
    <div class="fp-shell">
      <div class="fp-sidebar">
        {nav_html}
      </div>
      <div class="fp-topbar">
        <div class="fp-topbar-title">
          <h2>{page_title}</h2>
          <p>{page_sub}</p>
        </div>
      </div>
    </div>
    '''
    st.markdown(shell_html, unsafe_allow_html=True)

    # Navigation par boutons Streamlit (sidebar simulee)
    with st.sidebar:
        st.markdown("### Navigation")
        for icon, label, pid in pages:
            if st.button(f"{icon} {label}", key=f"nav_{pid}", use_container_width=True,
                         type="primary" if st.session_state.page == pid else "secondary"):
                st.session_state.page = pid
                st.rerun()
        st.markdown("---")
        if st.button("🚪 Deconnexion", use_container_width=True):
            for k in ["logged_in","user","company","page"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    # Afficher la sidebar Streamlit
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display:flex !important; }
    </style>
    """, unsafe_allow_html=True)

    # CONTENU PRINCIPAL
    st.markdown('<div class="fp-main" style="padding:24px;">', unsafe_allow_html=True)

    if curr_page == "dashboard":
        page_dashboard()
    elif curr_page == "new_invoice":
        page_new_invoice()
    elif curr_page == "invoices":
        page_invoices()
    elif curr_page == "payments":
        page_invoices()  # Payments integres dans invoices pour simplifier
    elif curr_page == "clients":
        page_clients()
    elif curr_page == "products":
        page_products()
    elif curr_page == "reports":
        page_reports()
    elif curr_page == "settings":
        page_settings()
    elif curr_page == "users":
        if safe(st.session_state.user, "role") == "admin":
            page_users()
        else:
            st.error("Acces refuse")

    st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
