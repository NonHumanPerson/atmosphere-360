"""
Atmosphere360: Mumbai — Reusable UI Components
HTML/Streamlit cards, KPI tiles, badges, and dossiers.
Presentation layer with native Material Symbols icons and token-based CSS classes.
"""
from html import escape
import pandas as pd
import streamlit as st
from theme import COLORS, AQI_PALETTE, get_aqi_category_color, get_priority_tier
from icons import ICONS
from config import EVENT_NAME, TEAM_MEMBERS, DISCLAIMER_TEXT


def _accent(value: str) -> str:
    """Binds a semantic accent colour to a component through a CSS custom property."""
    return f'style="--cp-card-accent: {value};"'


def render_compact_banner():
    """Renders a concise, professional regulatory disclaimer banner."""
    st.markdown(
        '<div class="cp-disclaimer">'
        '  <strong>Decision-support prototype</strong>'
        '  <span>Designed for municipal planning and environmental inspection triage (BMC / MPCB). '
        '  This is a research prototype, not an official real-time warning system.</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_header(station_name: str, date_str: str, total_stations: int = 37):
    """Renders the executive command center header with status badges."""
    station = escape(str(station_name))
    date = escape(str(date_str))

    st.markdown(
        '<div class="cp-cmd-header">'
        '  <div class="cp-cmd-branding">'
        '    <div class="cp-cmd-icon">'
        '      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2DD4BF" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M3 21h18M5 21V7l8-4v18M13 21V11l6 3v7M8 10h1M8 14h1M8 18h1M16 16h1M16 19h1"/></svg>'
        '    </div>'
        '    <div class="cp-cmd-titles">'
        '      <h1 class="cp-cmd-name">Atmosphere360: Mumbai</h1>'
        '      <p class="cp-cmd-tagline">Predictive air quality prioritisation and municipal environmental triage</p>'
        '    </div>'
        '  </div>'
        '  <div class="cp-cmd-badges">'
        '    <span class="cp-pill cp-pill-amber">Historical decision replay</span>'
        f'    <span class="cp-pill cp-pill-teal">Focus: {station}</span>'
        f'    <span class="cp-pill">As of {date}</span>'
        f'    <span class="cp-pill">{int(total_stations)} stations monitored</span>'
        '  </div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_data_status_bar(
    decision_date: str,
    target_date: str,
    reliability_label: str = "High",
    total_stations: int = 30,
    observation_range: str = "2021–2023",
    data_source: str = "CPCB / MPCB & ERA5",
):
    """Renders explicit dataset context: status, period, replay window, source, reliability."""
    rel_pill_class = {
        "High": "cp-pill-green",
        "Medium": "cp-pill-amber",
        "Low": "cp-pill-red",
    }.get(reliability_label, "cp-pill-amber")

    items = [
        ("Dataset status", '<span style="color: #FBBF24;">●</span> Historical'),
        ("Observation period", escape(str(observation_range))),
        ("Dashboard mode", f"Decision replay ({escape(str(decision_date))} → {escape(str(target_date))})"),
        ("Data sources", escape(str(data_source))),
        (
            "Station reliability",
            f'<span class="cp-pill {rel_pill_class}" style="padding: 2px 8px; font-size: 0.75rem;">'
            f'{escape(str(reliability_label))}</span>',
        ),
    ]
    items_html = "".join(
        f'<div class="cp-status-item"><span class="cp-status-label">{label}</span>'
        f'<span class="cp-status-value">{value}</span></div>'
        for label, value in items
    )

    st.markdown(
        '<div class="cp-status-bar">'
        f'  <div class="cp-status-items">{items_html}</div>'
        f'  <div class="cp-status-note">Coverage: <strong>{int(total_stations)} stations</strong> quality-screened</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_navigation_guide():
    """Navigation overview guide."""
    steps = [
        ("Overview", "Executive KPIs, map & action queue"),
        ("Decision Center", "Rankings, what-if, routing & export"),
        ("Air Quality Insights", "Longitudinal patterns & weather"),
        ("Model Intelligence", "Forecast error, diagnostics & backtest"),
        ("Citizen & Reports", "Public guide, live demo & audit"),
    ]
    cards = "".join(
        f'<div class="cp-detail-card">'
        f'<strong style="color: {COLORS["accent"]}; font-size: 0.875rem; display: block;">{escape(title)}</strong>'
        f'<span style="color: {COLORS["text_muted"]}; font-size: 0.8125rem;">{escape(desc)}</span>'
        f'</div>'
        for title, desc in steps
    )
    st.markdown(
        f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); '
        f'gap: var(--cp-space-3); margin: var(--cp-space-3) 0 var(--cp-space-4);">{cards}</div>',
        unsafe_allow_html=True,
    )


def render_takeaway(text: str, highlight: str = "Key Decision Takeaway:"):
    """Renders a prominent, plain-language takeaway box at the top of a page."""
    st.info(f"**{highlight}** {text}", icon=":material/lightbulb:")


def render_kpi_card(
    label: str,
    value: str,
    subtext: str = "",
    color_accent: str | None = None,
    badge: str | None = None,
):
    """Renders a high-contrast command center KPI metric tile."""
    accent = color_accent or COLORS["accent"]
    badge_html = (
        f"<span class='cp-pill' style='font-size: 0.75rem; padding: 2px 8px;'>{escape(str(badge))}</span>"
        if badge else ""
    )
    html = (
        f'<div class="cp-kpi-card" {_accent(accent)}>'
        f'<div class="cp-kpi-label"><span>{escape(str(label))}</span>{badge_html}</div>'
        f'<div class="cp-kpi-val" style="color: {accent};">{escape(str(value))}</div>'
        f'<div class="cp-kpi-sub">{escape(str(subtext))}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_action_strip(priority_df: pd.DataFrame, top_n: int = 5):
    """Renders readable inspection action cards for top priority zones."""
    st.markdown(f"##### {ICONS['action_queue']} Immediate municipal action queue")
    top_rows = priority_df.head(top_n)
    if top_rows.empty:
        st.info("No priority zones are available for this replay date.")
        return

    cols = st.columns(min(3, len(top_rows)), gap="medium")
    for i, (_, row) in enumerate(top_rows.iterrows()):
        _, aqi_col = get_aqi_category_color(row["latest_aqi"])
        rank = int(row["rank"])
        tier_label, tier_col = get_priority_tier(rank, capacity_n=top_n)
        station = escape(str(row["station"]))
        latest_aqi = float(row["latest_aqi"])
        prio_score = float(row["priority_score"])
        zone = escape(str(row["zone"]))
        action = escape(str(row["recommended_action"]))

        with cols[i % len(cols)]:
            card_html = (
                f'<div class="cp-queue-card" {_accent(tier_col)}>'
                '  <div class="cp-queue-top">'
                f'    <span class="cp-queue-rank">Priority #{rank} · {escape(tier_label)}</span>'
                f'    <span class="cp-pill" style="border-color: {aqi_col}; color: {aqi_col}; font-weight: 700;">'
                f'AQI {latest_aqi:.0f}</span>'
                '  </div>'
                f'  <div class="cp-queue-station">{station}</div>'
                f'  <div class="cp-queue-meta">{zone} · Priority score {prio_score:.1f}/100</div>'
                '  <div class="cp-queue-action">'
                '    <strong style="color: #ffffff; font-size: 0.75rem; text-transform: uppercase;">Field directive</strong>'
                f'    <div style="margin-top: 4px;">{action}</div>'
                '  </div>'
                '</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)


def render_ranked_summary(priority_df: pd.DataFrame, top_n: int = 5):
    """Renders a ranked zone summary explaining why each top zone was prioritized."""
    top_rows = priority_df.head(top_n)
    if top_rows.empty:
        return

    st.markdown(f"##### :material/summarize: Top {top_n} priority zones and evidence")

    cards = []
    for _, row in top_rows.iterrows():
        rank = int(row["rank"])
        station = escape(str(row["station"]))
        zone = escape(str(row["zone"]))
        score = float(row["priority_score"])
        latest_aqi = float(row["latest_aqi"])
        prob_unhealthy = float(row.get("forecast_prob_unhealthy", 0.0)) * 100
        _, aqi_color = get_aqi_category_color(latest_aqi)
        _, tier_color = get_priority_tier(rank, capacity_n=top_n)

        reasons = []
        if latest_aqi >= 200:
            reasons.append(f"Elevated AQI ({latest_aqi:.0f})")
        if prob_unhealthy >= 50:
            reasons.append(f"High next-day risk ({prob_unhealthy:.0f}%)")
        if row.get("score_persistence", 0) > 40:
            reasons.append("Multi-day persistence shock")
        if row.get("score_vulnerability", 0) > 40:
            reasons.append("Corridor / industrial proximity")
        if not reasons:
            reasons.append("Cumulative multi-criteria exposure")
        reason_badges = "".join(
            f"<span class='cp-pill'>{escape(reason)}</span>" for reason in reasons
        )

        cards.append(
            f'<div class="cp-rank-row" {_accent(tier_color)}>'
            '  <div>'
            '    <div style="display: flex; align-items: center; flex-wrap: wrap; gap: var(--cp-space-2);">'
            f'      <span class="cp-rank-chip">#{rank}</span>'
            f'      <strong style="color: #ffffff; font-size: 0.9375rem;">{station}</strong>'
            f'      <span style="color: var(--cp-text-muted); font-size: 0.875rem;">{zone}</span>'
            '    </div>'
            f'    <div class="cp-reason-badges">{reason_badges}</div>'
            '  </div>'
            '  <div class="cp-rank-stats">'
            '    <div style="text-align: right;">'
            '      <div class="cp-stat-label">Priority score</div>'
            f'      <div class="cp-stat-value" style="color: {tier_color};">{score:.1f}</div>'
            '    </div>'
            '    <div style="text-align: right;">'
            '      <div class="cp-stat-label">Latest AQI</div>'
            f'      <div class="cp-stat-value" style="color: {aqi_color};">{latest_aqi:.0f}</div>'
            '    </div>'
            '  </div>'
            '</div>'
        )

    st.markdown("".join(cards), unsafe_allow_html=True)


def render_action_dossier(st_data: dict, allocated: bool = True):
    """Renders the comprehensive action dossier for the selected zone."""
    cat_col = get_aqi_category_color(st_data["latest_aqi"])[1]
    status_pill = (
        f"<span class='cp-pill cp-pill-red'>Priority allocated · Rank #{int(st_data['rank'])}</span>"
        if allocated
        else f"<span class='cp-pill'>Routine monitoring · Rank #{int(st_data['rank'])}</span>"
    )
    station = escape(str(st_data["station"]))
    action = escape(str(st_data["recommended_action"]))
    evidence = escape(str(st_data["evidence_basis"]))
    caveats = escape(str(st_data["action_caveats"]))

    dossier_html = (
        f'<div class="cp-action-dossier" {_accent(cat_col)}>'
        '  <div style="display: flex; justify-content: space-between; align-items: center; '
        'margin-bottom: var(--cp-space-3); flex-wrap: wrap; gap: var(--cp-space-2);">'
        f'    <h3 class="cp-action-title">Action protocol: {station}</h3>'
        f'    <div>{status_pill}</div>'
        '  </div>'
        '  <div class="cp-action-text">'
        '    <span class="cp-action-lead">Recommended municipal intervention</span>'
        f'    <div class="cp-action-body">{action}</div>'
        '  </div>'
        '  <div class="cp-evidence-grid">'
        f'    <div><strong>Verifiable evidence basis</strong>{evidence}</div>'
        f'    <div><strong>Operational caveats</strong>{caveats}</div>'
        '  </div>'
        '</div>'
    )
    st.markdown(dossier_html, unsafe_allow_html=True)


def render_source_card(
    name: str,
    provider: str,
    licence: str,
    access_date: str,
    status: str,
    fields: str,
    details: str,
):
    """Renders a data provenance card."""
    status_col = {"USED": "#10B981", "SUPPLEMENTARY": "#F59E0B"}.get(status, "#EF4444")
    card_html = (
        '<div class="cp-source-card">'
        '  <div style="display: flex; justify-content: space-between; align-items: center; '
        'margin-bottom: var(--cp-space-2); flex-wrap: wrap; gap: var(--cp-space-2);">'
        f'    <h4 class="cp-source-title">{escape(name)}</h4>'
        '    <div style="display: flex; gap: var(--cp-space-2);">'
        f'      <span class="cp-pill">{escape(licence)}</span>'
        f'      <span class="cp-pill" style="border-color: {status_col}; color: {status_col};">{escape(status)}</span>'
        '    </div>'
        '  </div>'
        f'  <div class="cp-source-meta"><strong>Provider:</strong> {escape(provider)} · '
        f'<strong>Accessed:</strong> {escape(access_date)}</div>'
        f'  <div class="cp-source-body"><strong>Fields / usage:</strong> {escape(fields)}<br>'
        f'    <span style="color: var(--cp-text-muted);">{escape(details)}</span></div>'
        '</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_footer():
    """Renders the persistent Buildathon credit and data provenance footer."""
    footer_html = (
        '<div class="cp-footer">'
        f'  <div class="cp-footer-primary">Built for <strong>{EVENT_NAME}</strong> by <strong>{TEAM_MEMBERS}</strong></div>'
        f'  <div class="cp-footer-secondary">{DISCLAIMER_TEXT}</div>'
        '</div>'
    )
    st.markdown(footer_html, unsafe_allow_html=True)
