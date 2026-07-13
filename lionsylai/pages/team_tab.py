"""
LionsylAI - Tab 10: Team Collaboration (Enterprise-grade)
Members with live presence - Real invite emails - Shared Reports -
Comments - Notifications - Audit Trail - Role permissions matrix
"""
from __future__ import annotations
from datetime import datetime, timedelta
from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st

from database import (
    TeamRepo, AuditRepo, NotificationRepo, CommentRepo, ReportRepo, UserRepo,
)
from utils.email_service import send_team_invite, email_delivery_configured
from design import section_header, insight_card, badge, kpi_card
from config.settings import PLANS, FREE_PLAN_SEATS

# Roles allowed to invite/remove members and edit roles - mirrors the
# "Invite / remove team members" row in the Roles & Permissions matrix below.
# Owner always has full rights regardless of what's in this set.
_TEAM_MANAGE_ROLES = {"Admin"}


def render():
    st.markdown(section_header(
        "Team Collaboration",
        "Manage your team - invite members - share reports - track activity"
    ), unsafe_allow_html=True)

    if st.session_state.pop("_joined_team_on_signup", False):
        st.success("You've joined a team workspace! Your activity here is now linked to your own account.")

    t1, t2, t3, t4, t5, t6 = st.tabs([
        "Team Members", "Roles & Permissions", "Shared Reports",
        "Comments", "Notifications", "Audit Trail"
    ])
    with t1: _team_members()
    with t2: _roles_permissions()
    with t3: _shared_reports()
    with t4: _comments()
    with t5: _notifications()
    with t6: _audit_trail()


# ---- Workspace helpers ---------------------------------------------

def _workspace_id() -> int:
    """The shared org/team key. For an owner this is their own user_id; for a
    linked team member it's the id of the person who invited them - so both
    see and act on the same roster instead of two separate empty ones."""
    return st.session_state.get("workspace_owner_id") or st.session_state.get("user_id")


def _can_manage_team() -> bool:
    """Owner can always manage. Members can only manage if their role is
    in the permitted set (kept in sync with Roles & Permissions)."""
    if not st.session_state.get("is_team_member"):
        return True
    return st.session_state.get("team_role") in _TEAM_MANAGE_ROLES


# ---- Impersonation ("Log in as", owner-only) -------------------------
#
# Lets the real workspace owner view the whole app - not just this tab -
# as a linked team member, without knowing their password. Deliberately
# narrow: owner-only (a non-owner Admin can't use it, so no one can climb
# to the owner's own privileges this way), one level deep (you can't start
# a second impersonation while already viewing as someone), and every
# start/stop is written to the audit trail against the real account.

def start_impersonation(target_user_id: int, target_role: str) -> bool:
    target = UserRepo.get_by_id(target_user_id)
    if not target:
        return False
    real_uid = st.session_state.get("user_id")
    st.session_state["_real_identity"] = {
        "user_id":        real_uid,
        "user_full_name": st.session_state.get("user_full_name"),
        "username":       st.session_state.get("username"),
        "team_role":      st.session_state.get("team_role"),
        "is_team_member": st.session_state.get("is_team_member"),
    }
    st.session_state["user_id"]        = target.id
    st.session_state["user_full_name"] = target.full_name
    st.session_state["username"]       = target.username
    st.session_state["team_role"]      = target_role
    st.session_state["is_team_member"] = True
    AuditRepo.log(real_uid, "impersonation_started",
                  f"Started viewing as {target.full_name or target.username} ({target_role})")
    return True


def stop_impersonation() -> None:
    real = st.session_state.get("_real_identity")
    if not real:
        return
    AuditRepo.log(real["user_id"], "impersonation_ended",
                  f"Stopped viewing as {st.session_state.get('user_full_name')}")
    st.session_state.update(real)
    del st.session_state["_real_identity"]


# ---- Presence helper ------------------------------------------------

def _presence(last_active) -> tuple[str, str, str]:
    """Return (label, color, dot) based on last_active timestamp."""
    if not last_active:
        return "Never active", "#6B7280", "⚫"
    if isinstance(last_active, str):
        try:
            last_active = datetime.fromisoformat(last_active)
        except Exception:
            return "Unknown", "#6B7280", "⚫"
    delta = datetime.utcnow() - last_active.replace(tzinfo=None)
    if delta < timedelta(minutes=5):
        return "Online now", "#10B981", "🟢"
    if delta < timedelta(minutes=30):
        return f"Active {int(delta.total_seconds()//60)}m ago", "#10B981", "🟢"
    if delta < timedelta(hours=24):
        hrs = int(delta.total_seconds() // 3600)
        return f"Active {hrs}h ago", "#F59E0B", "🟡"
    days = delta.days
    return f"Active {days}d ago", "#6B7280", "⚫"


# Manual status: lets a signed-in user override automatic presence, the
# way Slack/Teams-style status pickers work. Stored on User.manual_status;
# None means "Auto" (fall back to real last-seen activity).
MANUAL_STATUSES = {
    "Online":  ("Online",                "#10B981", "🟢"),
    "Away":    ("Away",                  "#F59E0B", "🟡"),
    "Busy":    ("Busy (Do Not Disturb)", "#EF4444", "🔴"),
    "Offline": ("Appears offline",       "#6B7280", "⚫"),
}


def _effective_presence(acct) -> tuple[str, str, str]:
    """A real account's presence: their manually-set status if they've
    chosen one, otherwise inferred from actual last-seen activity."""
    if not acct:
        return "Unknown", "#6B7280", "⚫"
    if getattr(acct, "manual_status", None) in MANUAL_STATUSES:
        return MANUAL_STATUSES[acct.manual_status]
    return _presence(acct.last_seen)


# ---- Team Members ------------------------------------------------

def _team_members():
    st.markdown("### Team Members")
    uid          = st.session_state.get("user_id")
    workspace_id = _workspace_id()
    is_member    = st.session_state.get("is_team_member", False)
    can_manage   = _can_manage_team()

    members    = _load_members()
    seat_limit = PLANS["pro"]["seats"] if st.session_state.get("subscription") == "pro" else FREE_PLAN_SEATS

    def _member_presence(m):
        """Real presence for a linked account (their manual status if set,
        else inferred from actual last login/activity); legacy status-based
        presence for a placeholder that hasn't joined yet."""
        if m.get("member_user_id"):
            acct = UserRepo.get_by_id(m["member_user_id"])
            if acct:
                return _effective_presence(acct)
        if m["status"] == "Invited":
            return "Pending — hasn't joined yet", "#6B7280", "⚪"
        return _presence(m["last_active"])

    presences = {m["id"]: _member_presence(m) for m in members}

    online = sum(1 for lbl, *_ in presences.values() if lbl == "Online now" or ("Active" in lbl and "m ago" in lbl))
    active_today = sum(1 for lbl, *_ in presences.values()
                        if "Online" in lbl or ("Active" in lbl and ("m ago" in lbl or "h ago" in lbl)))

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(kpi_card("Total Seats Used", f"{len(members)+1}/{seat_limit}", icon="👥",
                gradient="linear-gradient(135deg,#6C63FF,#0AEFFF)"), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card("Online Now", str(online), icon="🟢",
                gradient="linear-gradient(135deg,#10B981,#0AEFFF)"), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card("Active Today", str(active_today), icon="⚡",
                gradient="linear-gradient(135deg,#F59E0B,#FF6B6B)"), unsafe_allow_html=True)
    with c4:
        pending = sum(1 for m in members if m["status"] == "Invited" and not m.get("member_user_id"))
        st.markdown(kpi_card("Pending Invites", str(pending), icon="✉️",
                gradient="linear-gradient(135deg,#8B84FF,#6C63FF)"), unsafe_allow_html=True)

    if len(members) + 1 >= seat_limit:
        st.warning(
            f"You've used all {seat_limit} seats on your current plan. "
            f"{'Upgrade to Pro for 5 seats' if st.session_state.get('subscription')!='pro' else 'Contact us to add more seats'} "
            f"in Settings → Billing."
        )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown("#### Current Members")

    my_account = UserRepo.get_by_id(uid)
    my_current = (my_account.manual_status if my_account and my_account.manual_status in MANUAL_STATUSES else "Auto")
    status_opts = ["Auto"] + list(MANUAL_STATUSES.keys())
    if st.session_state.get("_status_widget_uid") != uid:
        st.session_state["tm_my_status"] = my_current
        st.session_state["_status_widget_uid"] = uid
    picked_status = st.selectbox(
        "Your status", status_opts,
        format_func=lambda s: "Auto (based on activity)" if s == "Auto" else MANUAL_STATUSES[s][0],
        key="tm_my_status",
    )
    if picked_status != my_current:
        UserRepo.set_manual_status(uid, None if picked_status == "Auto" else picked_status)
        st.rerun()

    # Owner card - real presence, whether you're the owner viewing your own
    # workspace or a linked member viewing the person who invited you.
    if is_member:
        owner_acct = UserRepo.get_by_id(workspace_id)
        owner_label, owner_color, owner_dot = _effective_presence(owner_acct)
        owner_display = (owner_acct.full_name or owner_acct.username) if owner_acct else "Workspace Owner"
        owner_tag = "OWNER"
    else:
        me = UserRepo.get_by_id(uid)
        owner_label, owner_color, owner_dot = _effective_presence(me) if me else ("Online now", "#10B981", "🟢")
        owner_display = st.session_state.get("user_full_name") or st.session_state.get("username", "You")
        owner_tag = "OWNER (YOU)"

    st.markdown(f"""
    <div style="background:#141720;border:1px solid #6C63FF55;border-radius:12px;
                padding:14px 18px;margin:8px 0;display:flex;justify-content:space-between;
                align-items:center;">
      <div>
        <span style="font-weight:700;color:#F0F2FF;">{owner_dot} {owner_display}</span>
        <span style="background:#6C63FF22;color:#6C63FF;border-radius:12px;padding:2px 10px;
                     font-size:11px;font-weight:700;margin-left:8px;">{owner_tag}</span>
      </div>
      <div style="text-align:right;">
        <span style="color:{owner_color};font-size:12px;font-weight:600;">{owner_label}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if not members:
        st.info("No team members yet. Invite your first colleague below.")
    else:
        for m in members:
            label, color, dot = presences[m["id"]]
            you_tag = " · YOU" if m.get("member_user_id") == uid else ""
            with st.expander(f"{dot} {m['name']} — {m['role']}{you_tag}", expanded=False):
                ca, cb = st.columns(2)
                with ca:
                    st.write(f"**Email:** {m['email']}")
                    st.markdown(f"**Presence:** <span style='color:{color};font-weight:600;'>{label}</span>",
                               unsafe_allow_html=True)
                    if m.get("member_user_id"):
                        st.caption("✅ Linked to a real LionsylAI account")
                    elif m["status"] == "Invited":
                        st.caption("Invitation sent — presence appears once they sign in with this email.")
                with cb:
                    if can_manage:
                        roles = ["Admin","Finance Manager","Analyst","Viewer","Manager","Developer"]
                        new_role = st.selectbox("Role", roles,
                                                index=_role_idx(m["role"], roles),
                                                key=f"tm_role_{m['id']}")
                        status_opts = ["Active","Away","Inactive","Invited"]
                        new_status = st.selectbox("Status", status_opts,
                                                  index=status_opts.index(m["status"]) if m["status"] in status_opts else 0,
                                                  key=f"tm_status_{m['id']}")
                    else:
                        st.write(f"**Role:** {m['role']}")
                        st.write(f"**Status:** {m['status']}")

                if can_manage:
                    is_true_owner = not st.session_state.get("is_team_member")
                    can_impersonate = (is_true_owner and m.get("member_user_id")
                                        and not st.session_state.get("_real_identity"))
                    bcol1, bcol2, bcol3 = st.columns(3) if can_impersonate else (*st.columns(2), None)
                    with bcol1:
                        if st.button("Update", key=f"tm_upd_{m['id']}", use_container_width=True):
                            TeamRepo.update(m["id"], name=m["name"], email=m["email"],
                                            role=new_role, status=new_status)
                            AuditRepo.log(uid, "team_member_updated", f"Updated {m['name']} -> {new_role}/{new_status}")
                            st.success(f"Updated {m['name']}!")
                            st.rerun()
                    with bcol2:
                        if st.button("Remove from team", key=f"tm_del_{m['id']}", use_container_width=True):
                            TeamRepo.delete(m["id"])
                            AuditRepo.log(uid, "team_member_removed", f"Removed {m['name']}")
                            st.success(f"Removed {m['name']}.")
                            st.rerun()
                    if can_impersonate:
                        with bcol3:
                            if st.button("Log in as", key=f"tm_imp_{m['id']}", use_container_width=True,
                                         help=f"View the whole app as {m['name']} - no password needed. "
                                              f"You can switch back any time from the banner at the top."):
                                if start_impersonation(m["member_user_id"], m["role"]):
                                    st.rerun()
                else:
                    st.caption("Only Admins and the workspace owner can edit or remove members.")

    st.markdown("---")
    st.markdown("#### Activity — View by Member")
    st.caption("Pick anyone on the team to see their real presence, recent comments, and recent actions.")

    viewer_rows = [{"key": "me", "label": "Me (You)", "target_id": uid, "linked": True}]
    for m in members:
        if m.get("member_user_id") == uid:
            continue  # that's you, already covered by "Me (You)" above
        pending = not m.get("member_user_id")
        label = m["name"] + (" — pending, hasn't signed in yet" if pending else "")
        viewer_rows.append({"key": str(m["id"]), "label": label,
                             "target_id": m.get("member_user_id"), "linked": not pending})

    valid_keys = {r["key"] for r in viewer_rows}
    if st.session_state.get("tm_activity_pick") not in valid_keys:
        st.session_state["tm_activity_pick"] = "me"

    picked_key = st.selectbox(
        "View activity for", [r["key"] for r in viewer_rows],
        format_func=lambda k: next(r["label"] for r in viewer_rows if r["key"] == k),
        key="tm_activity_pick",
    )
    row = next(r for r in viewer_rows if r["key"] == picked_key)

    if not row["linked"]:
        st.info(f"**{row['label'].split(' — ')[0]}** hasn't signed in yet, so there's no real "
                f"activity to show. Once they register using the invited email, their presence, "
                f"comments, and actions will start appearing here automatically.")
    else:
        target_id = row["target_id"]
        target_name = (st.session_state.get("user_full_name") or st.session_state.get("username", "You")) \
                       if row["key"] == "me" else row["label"]
        target_acct = UserRepo.get_by_id(target_id)
        t_label, t_color, t_dot = _presence(target_acct.last_seen) if target_acct else ("Unknown", "#6B7280", "⚫")
        st.markdown(f"**{t_dot} {target_name}** — <span style='color:{t_color};'>{t_label}</span>",
                    unsafe_allow_html=True)

        acol, ccol = st.columns(2)
        with acol:
            st.markdown("**Recent actions**")
            acts = AuditRepo.list_recent(user_id=target_id, limit=5)
            if acts:
                for a in acts:
                    ts = a.created_at.strftime("%m/%d %H:%M") if a.created_at else ""
                    st.markdown(f"<div style='font-size:12px;color:#9CA3AF;padding:4px 0;'>{ts} — {a.action}</div>",
                                unsafe_allow_html=True)
            else:
                st.caption("No recorded activity yet.")
        with ccol:
            st.markdown("**Recent comments**")
            cmts = CommentRepo.list_recent(user_ids=[target_id], limit=5)
            if cmts:
                for c in cmts:
                    st.markdown(f"<div style='font-size:12px;color:#E0E4F0;padding:4px 0;'>"
                                f"\"{str(c.comment_text)[:80]}\"</div>", unsafe_allow_html=True)
            else:
                st.caption("No comments yet.")

    st.markdown("---")
    st.markdown("#### Invite Team Member")

    if not can_manage:
        st.info("Only Admins and the workspace owner can invite new team members.")
        return

    if not email_delivery_configured():
        st.markdown("""
        <div style="background:#F59E0B15;border:1px solid #F59E0B44;border-radius:10px;
                    padding:10px 14px;margin-bottom:12px;font-size:12px;color:#F59E0B;">
          Email delivery isn't configured yet — invites will be added to your team list
          but the invitation email won't actually reach the person until an administrator
          configures SMTP (see Settings &rarr; Email Setup).
        </div>
        """, unsafe_allow_html=True)

    with st.form("invite_team_member_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            new_name  = st.text_input("Full Name *",  placeholder="Jane Smith",       key="tm_new_name")
            new_email = st.text_input("Email *",       placeholder="jane@company.com", key="tm_new_email")
        with c2:
            new_role  = st.selectbox("Role",   ["Analyst","Viewer","Finance Manager","Manager","Admin","Developer"], key="tm_new_role")
            seats_left = seat_limit - (len(members) + 1)
            st.metric("Seats Remaining", max(0, seats_left))
        submitted = st.form_submit_button("Send Invitation", type="primary", use_container_width=True)

    if submitted:
        if not new_name or not new_email:
            st.warning("Please enter both name and email.")
        elif "@" not in new_email or "." not in new_email:
            st.warning("Please enter a valid email address.")
        elif len(members) + 1 >= seat_limit:
            st.error(f"Seat limit reached ({seat_limit}). Upgrade your plan to add more members.")
        else:
            existing = next((m for m in members if m["email"].lower() == new_email.lower()), None)
            if existing:
                st.warning(f"{new_email} is already on your team.")
            else:
                existing_account = UserRepo.get_by_email(new_email)
                inviter = st.session_state.get("user_full_name") or st.session_state.get("username", "A colleague")
                org     = st.session_state.get("org_name") or f"{inviter}'s Workspace"
                temp_password = None

                if existing_account:
                    member_uid = existing_account.id
                    if not existing_account.account_owner_id:
                        UserRepo.update_fields(existing_account.id, account_owner_id=workspace_id)
                else:
                    new_account, temp_password = UserRepo.create_team_member_account(
                        new_email, new_name, org, account_owner_id=workspace_id)
                    member_uid = new_account.id if new_account else None

                if member_uid is None:
                    st.error("Couldn't create an account for that email. Please try again.")
                else:
                    ok = TeamRepo.add(workspace_id, new_name, new_email, new_role, "Active",
                                      member_user_id=member_uid)
                    if ok:
                        AuditRepo.log(uid, "team_invite_sent", f"Added {new_email} as {new_role}")
                        if existing_account:
                            # They already have full credentials of their own - a login
                            # email would be confusing ("accept" what, exactly?). An
                            # in-app notification is the honest signal here.
                            NotificationRepo.add(existing_account.id, f"{inviter} added you to {org} as {new_role}.")
                            st.success(f"{new_name} already has a LionsylAI account — linked immediately, "
                                      f"no email needed. They'll see it next time they sign in.")
                            st.rerun()
                        else:
                            sent, detail = send_team_invite(new_email, new_name, inviter, org, new_role,
                                                             temp_password=temp_password)
                            if sent:
                                st.success(f"Invitation sent to {new_email} — they can sign in right away "
                                          f"with the credentials in that email.")
                                st.rerun()
                            else:
                                # Email genuinely could not be delivered, and this password
                                # is never shown again after this run - don't let a rerun
                                # race it off the screen before it's copied.
                                st.success(f"{new_name} added to your team — a real, working login now "
                                          f"exists for {new_email}.")
                                st.warning(f"Email delivery isn't configured ({detail}), so copy these "
                                          f"sign-in details now and share them directly — this password "
                                          f"won't be shown again:")
                                st.code(f"Email:    {new_email}\nPassword: {temp_password}", language=None)
                                st.caption("They should change this password from Settings → Security after signing in.")
                    else:
                        st.error("Failed to add team member. Please try again.")


# ---- Roles & Permissions ------------------------------------------

def _roles_permissions():
    st.markdown("### Roles & Permissions")
    st.info("Define what each role can see and do across your LionsylAI workspace.")

    perms = [
        ("View dashboards & reports",      True,  True,  True,  True,  True),
        ("Upload / replace data",          True,  True,  True,  False, False),
        ("Run AI Studio training",         True,  True,  True,  False, False),
        ("Edit budgets & FP&A",            True,  True,  False, False, False),
        ("Approve month-end close",        True,  False, False, False, False),
        ("Manage integrations & API keys", True,  False, False, False, True),
        ("Invite / remove team members",   True,  False, False, False, False),
        ("Manage billing & subscription",  True,  False, False, False, False),
        ("Comment on reports",             True,  True,  True,  True,  True),
        ("Export / download data",         True,  True,  True,  True,  True),
    ]
    roles = ["Admin", "Manager", "Analyst", "Viewer", "Developer"]
    rows = []
    for label, *flags in perms:
        row = {"Permission": label}
        for role, flag in zip(roles, flags):
            row[role] = "✅" if flag else "—"
        rows.append(row)
    perm_df = pd.DataFrame(rows)
    st.dataframe(perm_df, use_container_width=True, hide_index=True)

    st.markdown("#### Role Descriptions")
    descs = [
        ("Admin",           "Full control: billing, team management, all data and settings.", "#6C63FF"),
        ("Manager",         "Runs analytics and FP&A workflows, cannot manage billing or team.", "#0AEFFF"),
        ("Analyst",         "Uploads data, runs models and reports, cannot edit budgets.", "#10B981"),
        ("Viewer",          "Read-only access to dashboards, reports, and comments.", "#F59E0B"),
        ("Finance Manager", "Full FP&A and budget access, limited admin capability.", "#8B84FF"),
        ("Developer",       "API keys and integrations access for technical implementation.", "#FF6B6B"),
    ]
    for role, desc, color in descs:
        st.markdown(insight_card(f"**{role}** — {desc}", color), unsafe_allow_html=True)


# ---- Shared Reports ------------------------------------------------

def _shared_reports():
    st.markdown("### Report Sharing")
    uid     = st.session_state.get("user_id")
    reports = st.session_state.get("report_library", [])
    members = _load_members()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Share a Report")
        if not reports:
            st.info("No reports generated yet. Go to FP&A → Financial Reporting first.")
        else:
            rpt_names  = [r["name"] for r in reports]
            sel_rpt    = st.selectbox("Select Report", rpt_names, key="sr_rpt")
            m_names    = [m["name"] for m in members]
            share_with = st.multiselect("Share with", m_names, key="sr_with")
            perm       = st.selectbox("Permission", ["View Only","Can Comment","Can Edit","Full Access"], key="sr_perm")

            if st.button("Share Report", type="primary", use_container_width=True):
                if share_with:
                    st.success(f"'{sel_rpt}' shared with {', '.join(share_with)}!")
                    if uid:
                        sharer = st.session_state.get("user_full_name") or st.session_state.get("username", "A teammate")
                        for name in share_with:
                            m = next((x for x in members if x["name"] == name), None)
                            if m:
                                if m.get("member_user_id"):
                                    # Real linked account - notify them directly, it'll
                                    # be waiting in their own Notifications when they log in.
                                    NotificationRepo.add(m["member_user_id"],
                                        f"{sharer} shared the report '{sel_rpt}' with you.")
                                else:
                                    NotificationRepo.add(uid, f"Report '{sel_rpt}' shared with {name}")
                        AuditRepo.log(uid, "share_report", f"Shared {sel_rpt} with {', '.join(share_with)}")
                else:
                    st.warning("Select at least one team member.")

    with c2:
        st.markdown("#### Recently Shared")
        st.info("Reports shared with you will appear here once a teammate shares one.")


# ---- Comments --------------------------------------------------------

def _comments():
    st.markdown("### Report Comments & Annotations")
    uid     = st.session_state.get("user_id")
    uname   = st.session_state.get("username", "You")
    reports = st.session_state.get("report_library", [])

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("#### Add Comment")
        if not reports:
            st.info("Generate reports first.")
        else:
            rpt_names = [r["name"] for r in reports]
            sel_rpt   = st.selectbox("Report", rpt_names, key="cmt_rpt")
            cmt_text  = st.text_area("Comment", placeholder="Your insight or question...",
                                     height=120, key="cmt_text")
            c_type    = st.selectbox("Type", ["General","Question","Insight","Issue","Action Item"], key="cmt_type")
            urgency   = st.selectbox("Urgency", ["Low","Medium","High","Critical"], key="cmt_urg")

            if st.button("Post Comment", type="primary", use_container_width=True):
                if cmt_text.strip():
                    if "comments_cache" not in st.session_state:
                        st.session_state["comments_cache"] = []
                    st.session_state["comments_cache"].append({
                        "report": sel_rpt, "user": uname, "text": cmt_text,
                        "type": c_type, "urgency": urgency,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    })
                    if uid:
                        rpt_obj = next((r for r in reports if r["name"] == sel_rpt), None)
                        if rpt_obj:
                            CommentRepo.add(rpt_obj.get("id", 0), uid, cmt_text, c_type, urgency)
                        AuditRepo.log(uid, "add_comment", f"Commented on {sel_rpt}")
                    st.success("Comment posted!")
                    st.rerun()
                else:
                    st.warning("Comment cannot be empty.")

    with c2:
        st.markdown("#### Recent Comments")
        all_cmts = list(st.session_state.get("comments_cache", []))
        if uid:
            workspace_ids = TeamRepo.member_user_ids_for_workspace(_workspace_id())
            db_cmts = CommentRepo.list_recent(limit=10, user_ids=workspace_ids)
            for c in db_cmts:
                ts = c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else ""
                all_cmts.insert(0, {
                    "report": f"Report #{c.report_id}", "user": c.username,
                    "text": c.comment_text, "type": c.ctype, "urgency": c.urgency, "time": ts,
                })

        if all_cmts:
            urg_colors = {"Low":"#6B7280","Medium":"#F59E0B","High":"#FF6B6B","Critical":"#EF4444"}
            for cmt in list(reversed(all_cmts))[:10]:
                uc = urg_colors.get(cmt.get("urgency","Low"),"#6B7280")
                st.markdown(f"""
                <div style="background:#141720;border:1px solid #252836;border-left:3px solid {uc};
                            border-radius:0 12px 12px 0;padding:12px 16px;margin:8px 0;">
                  <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                    <span style="font-weight:700;color:#F0F2FF;">{cmt['user']}</span>
                    <span style="font-size:11px;color:#6B7280;">{cmt.get('time','')}</span>
                  </div>
                  <div style="font-size:13px;color:#E0E4F0;">{str(cmt['text'])[:200]}</div>
                  <div style="margin-top:6px;">
                    <span style="background:#6C63FF22;color:#6C63FF;border:1px solid #6C63FF55;
                                 border-radius:4px;padding:2px 8px;font-size:11px;">
                      {cmt.get('type','General')}
                    </span>
                  </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No comments yet.")


# ---- Notifications -----------------------------------------------------

def _notifications():
    st.markdown("### Notifications")
    uid = st.session_state.get("user_id")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Preferences")
        st.checkbox("Email on report shared",    value=True,  key="np_share")
        st.checkbox("Email on new comment",      value=True,  key="np_comment")
        st.checkbox("Weekly summary digest",     value=True,  key="np_weekly")
        st.checkbox("Budget alerts",             value=True,  key="np_budget")
        st.checkbox("Integration failures",      value=True,  key="np_int")
        st.checkbox("New member notifications",  value=False, key="np_member")
        if st.button("Save Preferences", use_container_width=True):
            st.success("Preferences saved!")

    with c2:
        st.markdown("#### Recent Notifications")
        notifs = []
        if uid:
            notifs = NotificationRepo.list_unread(uid, limit=15)

        sample = [
            {"id":901,"msg":"Monthly report generated","read":False,"time":"Today"},
            {"id":902,"msg":"New team member joined","read":False,"time":"Yesterday"},
            {"id":903,"msg":"Marketing over budget 6%","read":True,"time":"Mon"},
            {"id":904,"msg":"Month-end close completed","read":True,"time":"Last week"},
        ]
        display = ([{"id":n.id,"msg":n.message,"read":n.is_read,
                     "time":n.created_at.strftime("%m/%d %H:%M") if n.created_at else ""}
                    for n in notifs] if notifs else sample)

        unread = sum(1 for n in display if not n["read"])
        st.metric("Unread", unread)

        for n in display:
            bg  = "#1A1F2E" if not n["read"] else "#141720"
            bdr = "#6C63FF" if not n["read"] else "#252836"
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {bdr};border-radius:10px;
                        padding:12px 16px;margin:6px 0;">
              <span style="font-size:13px;color:#F0F2FF;">{n['msg']}</span>
              <span style="font-size:11px;color:#6B7280;float:right;">{n['time']}</span>
            </div>
            """, unsafe_allow_html=True)
            if not n["read"] and uid and n["id"] < 900:
                if st.button("Mark read", key=f"nr_{n['id']}"):
                    NotificationRepo.mark_read(n["id"])
                    st.rerun()

        if st.button("Mark All Read", use_container_width=True):
            if uid:
                NotificationRepo.mark_all_read(uid)
            st.success("All notifications marked as read!")
            st.rerun()


# ---- Audit Trail --------------------------------------------------------

def _audit_trail():
    st.markdown("### Activity Audit Trail")
    uid          = st.session_state.get("user_id")
    workspace_id = _workspace_id()
    members      = _load_members()

    owner_acct = UserRepo.get_by_id(workspace_id)
    owner_name = (owner_acct.full_name or owner_acct.username) if owner_acct else "Owner"
    people = [owner_name] + [m["name"] for m in members]

    c1, c2, c3 = st.columns(3)
    with c1: filt_user   = st.selectbox("User",   ["All"] + people, key="at_user")
    with c2: filt_action = st.selectbox("Action", ["All","login","report","comment","share","data","team"], key="at_action")
    with c3: limit        = st.slider("Max entries", 10, 200, 50, key="at_limit")

    audit = []
    if uid:
        workspace_ids = TeamRepo.member_user_ids_for_workspace(workspace_id)
        raw = AuditRepo.list_recent(user_id=workspace_ids, limit=limit)
        audit = [{"Time":    a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
                  "User":    a.username, "Action": a.action,
                  "Details": (a.details or "")[:80], "IP": a.ip_address or "—"} for a in raw]

    if not audit:
        audit = [
            {"Time":"2026-07-02 09:31","User":"admin","Action":"login","Details":"Successful login","IP":"192.168.1.1"},
            {"Time":"2026-07-02 09:45","User":"admin","Action":"data_upload","Details":"Uploaded sales_q2.csv","IP":"192.168.1.1"},
        ]

    if filt_user   != "All": audit = [a for a in audit if filt_user.lower() in a["User"].lower()]
    if filt_action != "All": audit = [a for a in audit if filt_action.lower() in a["Action"].lower()]

    if audit:
        audit_df = pd.DataFrame(audit)
        st.dataframe(audit_df, use_container_width=True, hide_index=True)
        st.download_button("Export Audit Log", audit_df.to_csv(index=False).encode(),
                           f"audit_log_{datetime.now().strftime('%Y%m%d')}.csv",
                           "text/csv", use_container_width=True)

        st.markdown("#### Activity Summary")
        action_cnt = Counter(a["Action"] for a in audit)
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(x=list(action_cnt.keys()), y=list(action_cnt.values()),
                         color=list(action_cnt.values()), color_continuous_scale="Viridis",
                         title="Actions by Type")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font_color="#F0F2FF", height=280,
                              xaxis_tickangle=-30, margin=dict(t=40,b=30,l=10,r=10))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            user_cnt = Counter(a["User"] for a in audit)
            fig = px.pie(values=list(user_cnt.values()), names=list(user_cnt.keys()),
                         title="Activity by User", hole=0.4,
                         color_discrete_sequence=["#6C63FF","#0AEFFF","#10B981","#F59E0B"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#F0F2FF",
                              height=280, margin=dict(t=40,b=20,l=10,r=10))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No audit entries match the selected filters.")


# ---- Helpers -------------------------------------------------------------

def _load_members():
    workspace_id = _workspace_id()
    if workspace_id:
        rows = TeamRepo.list_for_user(workspace_id)
        if rows:
            return [{"id":m.id,"name":m.name,"email":m.email,
                     "role":m.role,"status":m.status,
                     "last_active":m.last_active,
                     "member_user_id":m.member_user_id}
                    for m in rows]
    return []


def _role_idx(role, roles):
    return roles.index(role) if role in roles else 0
