"""
Intellectual AI — Streamlit client for the FastAPI backend.
Run API: uvicorn main:app --reload
Run UI:  streamlit run streamlit_app.py
"""

from __future__ import annotations

import html
import os
import uuid
from datetime import datetime
from typing import Any, Iterator

import httpx
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()

DEFAULT_API = os.getenv("INTELLECTUAL_API_URL", "http://127.0.0.1:8000")

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_AVATAR_USER = os.path.join(_APP_DIR, "assets", "chat_avatar_user.png")
_AVATAR_AI = os.path.join(_APP_DIR, "assets", "chat_avatar_ai.png")
# Streamlit may error on missing image paths; fall back to built-in avatars.
_USER_AVATAR: str | None = _AVATAR_USER if os.path.isfile(_AVATAR_USER) else None
_AI_AVATAR: str | None = _AVATAR_AI if os.path.isfile(_AVATAR_AI) else None


def _expand_sidebar_via_browser() -> None:
    """Click Streamlit's native sidebar toggle when the drawer is collapsed (parent DOM)."""
    components.html(
        """
<script>
(function () {
  function clickToggle(doc) {
    if (!doc || !doc.querySelector) return false;
    /* Streamlit ≥1.40: collapsed drawer uses stExpandSidebarButton (>> chevron), not stSidebarCollapseButton */
    var sx = doc.querySelector('[data-testid="stExpandSidebarButton"]');
    if (sx) { sx.click(); return true; }
    var expand = doc.querySelector('button[aria-label="Expand sidebar"]');
    if (expand) { expand.click(); return true; }
    var collapse = doc.querySelector('button[aria-label="Collapse sidebar"]');
    if (collapse) { collapse.click(); return true; }
    var el = doc.querySelector('[data-testid="stSidebarCollapseButton"]');
    if (el) { el.click(); return true; }
    var hdr = doc.querySelectorAll('[data-testid="stHeader"] button');
    for (var i = 0; i < hdr.length; i++) {
      var lab = (hdr[i].getAttribute('aria-label') || '').toLowerCase();
      if (lab.indexOf('sidebar') !== -1) { hdr[i].click(); return true; }
    }
    return false;
  }
  try {
    if (!clickToggle(window.parent.document) && window.parent.parent) {
      clickToggle(window.parent.parent.document);
    }
  } catch (e) {}
})();
</script>
        """,
        height=0,
    )


def inject_styles() -> None:
    st.markdown(
        """
        <style>
          /* ChatGPT-like light canvas */
          :root {
            --gpt-bg: #f7f7f8;
            --gpt-user: #f4f4f4;
            --gpt-assistant: #ffffff;
            --gpt-border: #e5e5e5;
            --gpt-text: #0d0d0d;
            --gpt-muted: #8e8ea0;
            --gpt-accent: #10a37f;
            --gpt-sidebar: #202123;
            /* Chat composer — placeholder/icon only (no focus rings) */
            --composer-placeholder: #374151;
            --composer-icon: #1f2937;
            --composer-accent-soft: #0d9488;
          }
          /* Whole app shell — Streamlit dark base was leaving the main pane charcoal */
          [data-testid="stAppViewContainer"],
          [data-testid="stAppViewContainer"] > .main {
            background: var(--gpt-bg) !important;
          }
          section[data-testid="stMain"],
          section[data-testid="stMain"] > div,
          .main .block-container {
            background: var(--gpt-bg) !important;
            color: var(--gpt-text) !important;
          }
          /* Do not use [class*="css"] — Streamlit emotion classes match and layout can collapse. */
          html, body {
            font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
              "Helvetica Neue", Arial, sans-serif !important;
            -webkit-font-smoothing: antialiased;
          }
          section[data-testid="stMain"],
          [data-testid="stSidebar"],
          header[data-testid="stHeader"] {
            font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
              "Helvetica Neue", Arial, sans-serif !important;
          }
          .main {
            background: var(--gpt-bg) !important;
          }
          .block-container {
            max-width: min(768px, 100%) !important;
            width: 100% !important;
            box-sizing: border-box !important;
            padding: 0.35rem clamp(0.75rem, 3vw, 1.25rem) 5rem !important;
          }
          section[data-testid="stMain"] {
            flex: 1 1 auto !important;
            min-width: 0 !important;
          }
          /* Prevent browser dark-mode from styling inputs charcoal */
          section.main {
            color-scheme: light !important;
          }
          header[data-testid="stHeader"] {
            background: var(--gpt-bg) !important;
            border-bottom: 1px solid var(--gpt-border) !important;
          }
          /*
           * Native sidebar toggle (<< / >>) — must beat Base Web + theme; darker chip so it
           * never blends into the light grey header (Streamlit often sets fadedText60 on icons).
           */
          [data-testid="stSidebarCollapseButton"] {
            background-color: #14151c !important;
            border-radius: 10px !important;
            border: 2px solid #3f3f50 !important;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.28) !important;
            opacity: 1 !important;
          }
          [data-testid="stSidebarCollapseButton"] button,
          [data-testid="stSidebarCollapseButton"] [data-baseweb="button"],
          [data-testid="stSidebarCollapseButton"] button[kind="headerNoPadding"] {
            background-color: #14151c !important;
            background-image: none !important;
            border: none !important;
            border-radius: 8px !important;
            box-shadow: none !important;
            min-width: 2.5rem !important;
            min-height: 2.5rem !important;
            opacity: 1 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
          }
          [data-testid="stSidebarCollapseButton"] button:hover,
          [data-testid="stSidebarCollapseButton"] [data-baseweb="button"]:hover {
            background-color: #1f212c !important;
            outline: 2px solid #10a37f !important;
            outline-offset: 0 !important;
          }
          [data-testid="stSidebarCollapseButton"] svg,
          [data-testid="stSidebarCollapseButton"] path,
          [data-testid="stSidebarCollapseButton"] use,
          [data-testid="stSidebarCollapseButton"] circle {
            fill: #ffffff !important;
            stroke: #ffffff !important;
            color: #ffffff !important;
            opacity: 1 !important;
          }
          [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
          [data-testid="stSidebarCollapseButton"] span {
            color: #ffffff !important;
            opacity: 1 !important;
            -webkit-text-fill-color: #ffffff !important;
          }
          /* Same control when Streamlit hoists it beside the main toolbar */
          header[data-testid="stHeader"] [data-testid="stSidebarCollapseButton"],
          header[data-testid="stHeader"] [data-testid="stSidebarCollapseButton"] button {
            background-color: #14151c !important;
            border-color: #3f3f50 !important;
          }
          /*
           * stExpandSidebarButton — ONLY when sidebar is collapsed (Streamlit index bundle).
           * Icon is forced to theme fadedText60 in React; must override wrapper + inner Base Web + SVG.
           */
          [data-testid="stExpandSidebarButton"] {
            background-color: #14151c !important;
            border-radius: 10px !important;
            border: 2px solid #3f3f50 !important;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.28) !important;
            opacity: 1 !important;
          }
          [data-testid="stExpandSidebarButton"] button,
          [data-testid="stExpandSidebarButton"] [data-baseweb="button"],
          [data-testid="stExpandSidebarButton"] button[kind="headerNoPadding"] {
            background-color: #14151c !important;
            background-image: none !important;
            border: none !important;
            border-radius: 8px !important;
            box-shadow: none !important;
            min-width: 2.5rem !important;
            min-height: 2.5rem !important;
            opacity: 1 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
          }
          [data-testid="stExpandSidebarButton"] button:hover,
          [data-testid="stExpandSidebarButton"] [data-baseweb="button"]:hover {
            background-color: #1f212c !important;
            outline: 2px solid #10a37f !important;
            outline-offset: 0 !important;
          }
          [data-testid="stExpandSidebarButton"] svg,
          [data-testid="stExpandSidebarButton"] path,
          [data-testid="stExpandSidebarButton"] use,
          [data-testid="stExpandSidebarButton"] circle {
            fill: #ffffff !important;
            stroke: #ffffff !important;
            color: #ffffff !important;
            opacity: 1 !important;
          }
          [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
          [data-testid="stExpandSidebarButton"] span {
            color: #ffffff !important;
            opacity: 1 !important;
            -webkit-text-fill-color: #ffffff !important;
          }
          header[data-testid="stHeader"] [data-testid="stExpandSidebarButton"],
          header[data-testid="stHeader"] [data-testid="stExpandSidebarButton"] button {
            background-color: #14151c !important;
            border-color: #3f3f50 !important;
          }
          /*
           * Header expand/collapse (when sidebar is hidden the control is ONLY here — Header.tsx).
           * Older Streamlit used weak tokens; these selectors match aria-label from PR #14563.
           */
          header[data-testid="stHeader"] button[aria-label="Expand sidebar"],
          header[data-testid="stHeader"] button[aria-label="Collapse sidebar"],
          section[data-testid="stAppViewContainer"] button[aria-label="Expand sidebar"],
          section[data-testid="stAppViewContainer"] button[aria-label="Collapse sidebar"] {
            background-color: #0a0b10 !important;
            background-image: none !important;
            border: 2px solid #52525b !important;
            border-radius: 10px !important;
            box-shadow: 0 2px 14px rgba(0, 0, 0, 0.4) !important;
            min-width: 2.65rem !important;
            min-height: 2.65rem !important;
            opacity: 1 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
          }
          header[data-testid="stHeader"] button[aria-label="Expand sidebar"]:hover,
          header[data-testid="stHeader"] button[aria-label="Collapse sidebar"]:hover {
            background-color: #171923 !important;
            border-color: #10a37f !important;
            box-shadow: 0 3px 18px rgba(16, 163, 127, 0.35) !important;
          }
          header[data-testid="stHeader"] button[aria-label="Expand sidebar"] svg,
          header[data-testid="stHeader"] button[aria-label="Expand sidebar"] path,
          header[data-testid="stHeader"] button[aria-label="Collapse sidebar"] svg,
          header[data-testid="stHeader"] button[aria-label="Collapse sidebar"] path {
            fill: #ffffff !important;
            stroke: #ffffff !important;
            opacity: 1 !important;
          }
          header[data-testid="stHeader"] button[aria-label="Expand sidebar"] [data-testid="stIconMaterial"],
          header[data-testid="stHeader"] button[aria-label="Collapse sidebar"] [data-testid="stIconMaterial"] {
            color: #ffffff !important;
            opacity: 1 !important;
          }
          /* Sidebar — dark strip like ChatGPT */
          [data-testid="stSidebar"] {
            background: var(--gpt-sidebar) !important;
            border-right: 1px solid #2f2f2f !important;
          }
          [data-testid="stSidebar"] .stMarkdown strong,
          [data-testid="stSidebar"] p,
          [data-testid="stSidebar"] span:not([style*="color"]),
          [data-testid="stSidebar"] label {
            color: #ececf1 !important;
          }
          [data-testid="stSidebar"] .stCaption,
          [data-testid="stSidebar"] [data-testid="stCaption"] {
            color: #8e8ea0 !important;
          }
          [data-testid="stSidebar"] .stExpander,
          [data-testid="stSidebar"] [data-testid="stExpander"] {
            background: #2f2f2f !important;
            border: 1px solid #4a4a4a !important;
            border-radius: 8px !important;
          }
          /* Expander header/toggle — Base Web often paints these white in “light” builds */
          [data-testid="stSidebar"] [data-testid="stExpander"] button,
          [data-testid="stSidebar"] [data-testid="stExpander"] summary,
          [data-testid="stSidebar"] details.streamlit-expander summary,
          [data-testid="stSidebar"] .streamlit-expanderHeader {
            background: #2f2f2f !important;
            background-color: #2f2f2f !important;
            color: #ececf1 !important;
            border: none !important;
            box-shadow: none !important;
          }
          [data-testid="stSidebar"] [data-testid="stExpander"] button:hover,
          [data-testid="stSidebar"] details.streamlit-expander summary:hover {
            background: #3f3f46 !important;
            color: #ffffff !important;
          }
          [data-testid="stSidebar"] [data-testid="stExpander"] svg,
          [data-testid="stSidebar"] details.streamlit-expander summary svg {
            fill: #ececf1 !important;
            color: #ececf1 !important;
          }
          [data-testid="stSidebar"] [data-testid="stExpander"] [role="button"],
          [data-testid="stSidebar"] [data-baseweb="accordion"] button {
            background: #2f2f2f !important;
            color: #ececf1 !important;
          }
          [data-testid="stSidebar"] input {
            background: #40414f !important;
            color: #ececf1 !important;
            border-color: #565869 !important;
          }
          /* Default sidebar buttons = dark surface (fixes white “Untitled chat” rows) */
          [data-testid="stSidebar"] .stButton > button {
            background: #343541 !important;
            background-color: #343541 !important;
            color: #ececf1 !important;
            border: 1px solid #565869 !important;
            border-radius: 6px !important;
            font-weight: 400 !important;
          }
          [data-testid="stSidebar"] .stButton > button:hover {
            background: #40414f !important;
            border-color: #6e6e80 !important;
            color: #ffffff !important;
          }
          [data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background: var(--gpt-accent) !important;
            background-color: var(--gpt-accent) !important;
            color: #ffffff !important;
            border: none !important;
            font-weight: 600 !important;
            border-radius: 6px !important;
          }
          [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
            background: #0d8f6e !important;
            filter: none !important;
          }
          [data-testid="stSidebar"] .stButton > button[kind="secondary"] {
            background: #343541 !important;
            color: #ececf1 !important;
            border: 1px solid #565869 !important;
            border-radius: 6px !important;
          }
          [data-testid="stSidebar"] code {
            background: #40414f !important;
            color: #d1d5db !important;
          }
          /* Conversation row: title column grows, menu column fixed — titles stay visible */
          [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: stretch !important;
            gap: 0.35rem !important;
            width: 100% !important;
          }
          [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div:first-child {
            flex: 1 1 0% !important;
            min-width: 0 !important;
            width: auto !important;
          }
          [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div:nth-child(2) {
            flex: 0 0 2.5rem !important;
            max-width: 2.5rem !important;
            min-width: 2.5rem !important;
          }
          /* Base Web buttons in sidebar — dark fill (runs before conversation overrides below) */
          [data-testid="stSidebar"] [data-baseweb="button"]:not([kind="primary"]) {
            background-color: #343541 !important;
            background-image: none !important;
            color: #ececf1 !important;
            border-color: #565869 !important;
          }
          [data-testid="stSidebar"] [data-baseweb="button"][kind="primary"] {
            background-color: var(--gpt-accent) !important;
            border-color: transparent !important;
            color: #ffffff !important;
          }
          /*
           * Conversation title row — Base Web paints WHITE on inner layers / column.
           * Darken the column shell, keep button transparent so label stays readable.
           */
          [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div:first-child {
            background: #343541 !important;
            background-color: #343541 !important;
            border: 1px solid #565869 !important;
            border-radius: 6px !important;
            overflow: hidden !important;
          }
          [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div:first-child .stButton,
          [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div:first-child .stButton > div {
            background: transparent !important;
            background-color: transparent !important;
          }
          [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div:first-child .stButton > button,
          [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div:first-child [data-baseweb="button"] {
            width: 100% !important;
            max-width: 100% !important;
            justify-content: flex-start !important;
            text-align: left !important;
            background: transparent !important;
            background-color: transparent !important;
            background-image: none !important;
            border: none !important;
            color: #ececf1 !important;
            font-weight: 400 !important;
            font-size: 0.875rem !important;
            padding: 0.45rem 0.6rem !important;
            border-radius: 0 !important;
            min-height: 2.25rem !important;
            box-shadow: none !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: nowrap !important;
          }
          [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div:first-child [data-baseweb="button"] > div {
            background-color: transparent !important;
            background: transparent !important;
          }
          [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div:first-child .stButton > button:hover,
          [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div:first-child [data-baseweb="button"]:hover {
            background: rgba(255, 255, 255, 0.06) !important;
          }
          /*
           * Popover trigger uses data-testid="stPopoverButton" (not a direct child of stPopover).
           * Streamlit always appends expand_more/expand_less beside the label (StyledPopoverExpansionIcon).
           */
          [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) [data-testid="stPopoverButton"] {
            width: 100% !important;
            min-width: 0 !important;
            padding: 0.35rem !important;
            border-radius: 6px !important;
            border: 1px solid #565869 !important;
            color: #ececf1 !important;
            background: #40414f !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
          }
          [data-testid="stSidebar"] [data-testid="stPopoverButton"] > div {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            width: 100% !important;
            gap: 0 !important;
          }
          /*
           * Hide expand_more / expand_less (StyledPopoverExpansionIcon, emotion target emnxg9p1).
           * Class hash is tied to this Streamlit build; if it breaks after upgrade, inspect the button in devtools.
           */
          [data-testid="stSidebar"] [data-testid="stPopoverButton"] [class*="emnxg9p1"],
          [data-testid="stSidebar"] [data-testid="stPopoverButton"] [class*="emnxg9p0"] > :last-child {
            display: none !important;
          }
          [data-testid="stSidebar"] [data-testid="stPopoverButton"] [class*="emnxg9p0"] {
            margin-right: 0 !important;
            justify-content: center !important;
          }
          /* Session search spacing */
          [data-testid="stSidebar"] [data-testid="stTextInput"]:has(input[placeholder="Search sessions…"]) {
            margin-bottom: 0.5rem !important;
          }
          /* Sticky session title — stays on top while scrolling chat */
          .gpt-topbar {
            position: -webkit-sticky;
            position: sticky;
            top: 0;
            z-index: 200;
            padding: 0.65rem clamp(0.5rem, 2vw, 1rem) 0.75rem clamp(0.5rem, 2vw, 1rem);
            margin: -0.35rem calc(-1 * clamp(0.75rem, 3vw, 1.25rem)) 1rem calc(-1 * clamp(0.75rem, 3vw, 1.25rem));
            border-bottom: 1px solid var(--gpt-border);
            background: var(--gpt-bg) !important;
            box-shadow: 0 1px 0 rgba(0, 0, 0, 0.04), 0 8px 24px rgba(0, 0, 0, 0.04);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
          }
          .gpt-topbar-model {
            font-size: 0.65rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--gpt-muted);
            margin: 0;
          }
          h1.gpt-topbar-title {
            font-size: clamp(1rem, 2.5vw, 1.125rem);
            font-weight: 600;
            color: var(--gpt-text);
            margin: 0.2rem 0 0 0;
            padding: 0;
            line-height: 1.25;
            letter-spacing: -0.02em;
            word-break: break-word;
          }
          /* Rename / dialog: force readable light inputs (avoids dark Base Web in modal) */
          [role="dialog"] input,
          [role="dialog"] textarea,
          [role="dialog"] [data-baseweb="input"] input,
          [role="dialog"] [data-baseweb="textarea"] textarea {
            background: #ffffff !important;
            color: #111827 !important;
            border: 1px solid #d1d5db !important;
            color-scheme: light !important;
          }
          /* Dialog: strip Base Web wrapper shadows/borders so focus is a single ring */
          [role="dialog"] [data-baseweb="input"],
          [role="dialog"] [data-baseweb="textarea"],
          [role="dialog"] [data-baseweb="input"]:focus-within,
          [role="dialog"] [data-baseweb="textarea"]:focus-within {
            box-shadow: none !important;
            border: none !important;
            background: transparent !important;
          }
          [role="dialog"] [data-baseweb="input"] input:focus,
          [role="dialog"] [data-baseweb="input"] input:focus-visible,
          [role="dialog"] [data-baseweb="textarea"] textarea:focus,
          [role="dialog"] [data-baseweb="textarea"] textarea:focus-visible {
            outline: none !important;
            box-shadow: none !important;
            border-color: var(--gpt-accent) !important;
          }
          [role="dialog"] label,
          [role="dialog"] [data-testid="stWidgetLabel"] p,
          [role="dialog"] .stMarkdown p {
            color: #111827 !important;
          }
          [role="dialog"] [data-testid="stCaptionContainer"] {
            color: #6b7280 !important;
          }
          /* Base Web modal (Streamlit dialog) — same light inputs if role missing */
          [data-baseweb="modal"] [data-baseweb="input"] input,
          [data-baseweb="modal"] [data-baseweb="textarea"] textarea {
            background: #ffffff !important;
            color: #111827 !important;
            border-color: #d1d5db !important;
            color-scheme: light !important;
          }
          [data-baseweb="modal"] [data-baseweb="input"],
          [data-baseweb="modal"] [data-baseweb="textarea"],
          [data-baseweb="modal"] [data-baseweb="input"]:focus-within,
          [data-baseweb="modal"] [data-baseweb="textarea"]:focus-within {
            box-shadow: none !important;
            border: none !important;
            background: transparent !important;
          }
          [data-baseweb="modal"] [data-baseweb="input"] input:focus,
          [data-baseweb="modal"] [data-baseweb="input"] input:focus-visible,
          [data-baseweb="modal"] [data-baseweb="textarea"] textarea:focus,
          [data-baseweb="modal"] [data-baseweb="textarea"] textarea:focus-visible {
            outline: none !important;
            box-shadow: none !important;
            border-color: var(--gpt-accent) !important;
          }
          .status-dot { font-size: 0.75rem; color: #8e8ea0; }
          /* Chat avatars — circular logos (slightly larger for readability) */
          div[data-testid="stChatMessage"] [data-testid="stImage"],
          div[data-testid="stChatMessage"] picture {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 2.75rem !important;
            min-width: 2.75rem !important;
            height: 2.75rem !important;
            flex-shrink: 0 !important;
          }
          div[data-testid="stChatMessage"] [data-testid="stImage"] img,
          div[data-testid="stChatMessage"] picture img {
            width: 2.75rem !important;
            height: 2.75rem !important;
            border-radius: 50% !important;
            object-fit: cover !important;
            border: 1px solid var(--gpt-border) !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06) !important;
          }
          div[data-testid="stChatMessage"] > div {
            gap: 0.65rem !important;
            align-items: flex-start !important;
          }
          div[data-testid="stChatMessage"] {
            padding: 0 !important;
            margin: 0 0 1.25rem 0 !important;
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
          }
          /* Base bubble */
          div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
            font-size: 1rem !important;
            line-height: 1.65 !important;
            color: var(--gpt-text) !important;
            border-radius: 1.5rem !important;
            padding: 0.65rem 1.1rem !important;
          }
          div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
            margin: 0 0 0.5em 0 !important;
          }
          div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p:last-child {
            margin-bottom: 0 !important;
          }
          div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] pre {
            font-size: 0.875rem !important;
            border-radius: 8px !important;
          }
          /* Assistant: left column — white bubble, max width */
          section.main [data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stChatMessage"] {
            width: fit-content !important;
            max-width: min(100%, 100%) !important;
            margin-right: auto !important;
            margin-left: 0 !important;
          }
          section.main [data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
            background: var(--gpt-assistant) !important;
            border: 1px solid var(--gpt-border) !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
            max-width: min(100%, 42rem) !important;
          }
          /* User: right column — gray bubble, hug right */
          section.main [data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stChatMessage"] {
            width: fit-content !important;
            max-width: min(100%, 85%) !important;
            margin-left: auto !important;
            margin-right: 0 !important;
          }
          section.main [data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
            background: var(--gpt-user) !important;
            border: none !important;
            box-shadow: none !important;
          }
          /* Main pane: ChatGPT-style bottom composer */
          section.main [data-testid="stVerticalBlock"] > div:has([data-testid="stChatInput"]) {
            max-width: min(768px, 100%) !important;
            margin-left: auto !important;
            margin-right: auto !important;
            padding-top: 1rem !important;
            padding-bottom: 0.5rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            box-sizing: border-box !important;
            border-top: 1px solid var(--gpt-border) !important;
            margin-top: 0.75rem !important;
            background: var(--gpt-bg) !important;
          }
          /* Inner layers transparent so the shell background shows (focus tint works) */
          [data-testid="stChatInput"] > div,
          [data-testid="stChatInput"] [data-baseweb="base-input"],
          [data-testid="stChatInput"] [data-baseweb="textarea"] {
            background-color: transparent !important;
            background: transparent !important;
            color-scheme: light !important;
          }
          /* Composer — single calm border; focus = slightly darker fill only (no extra borders/shadows) */
          [data-testid="stChatInput"] {
            border-radius: 1rem !important;
            border: 1px solid #d1d5db !important;
            background: #ffffff !important;
            min-height: 52px !important;
            outline: none !important;
            box-shadow: none !important;
          }
          [data-testid="stChatInput"]:focus-within {
            background: #eef2f7 !important;
            border-color: #d1d5db !important;
            box-shadow: none !important;
          }
          /* Base Web inner focus chrome off — shell handles affordance */
          [data-testid="stChatInput"] [data-baseweb="base-input"],
          [data-testid="stChatInput"] [data-baseweb="textarea"],
          [data-testid="stChatInput"] [data-baseweb="base-input"]:focus-within,
          [data-testid="stChatInput"] [data-baseweb="textarea"]:focus-within {
            box-shadow: none !important;
            border: none !important;
          }
          [data-testid="stChatInput"] textarea,
          [data-testid="stChatInput"] textarea:focus,
          [data-testid="stChatInput"] textarea:focus-visible {
            color: #0d0d0d !important;
            background: transparent !important;
            font-size: 1rem !important;
            min-height: 44px !important;
            padding: 0.5rem 0.75rem !important;
            outline: none !important;
            box-shadow: none !important;
          }
          [data-testid="stChatInput"] textarea::placeholder {
            color: var(--composer-placeholder) !important;
            opacity: 1 !important;
            font-weight: 500 !important;
          }
          /* Send control — readable icon on white */
          [data-testid="stChatInput"] button,
          [data-testid="stChatInput"] [data-baseweb="button"] {
            color: var(--composer-icon) !important;
            opacity: 1 !important;
          }
          [data-testid="stChatInput"] button:hover,
          [data-testid="stChatInput"] [data-baseweb="button"]:hover {
            color: var(--composer-accent-soft) !important;
            background: rgba(13, 148, 136, 0.08) !important;
          }
          [data-testid="stChatInput"] svg,
          [data-testid="stChatInput"] button svg,
          [data-testid="stChatInput"] [data-testid="stIconMaterial"] {
            color: var(--composer-icon) !important;
            fill: currentColor !important;
            opacity: 1 !important;
          }
          [data-testid="stChatInput"] button:hover svg,
          [data-testid="stChatInput"] [data-baseweb="button"]:hover svg {
            color: var(--composer-accent-soft) !important;
            fill: currentColor !important;
          }
          div[data-testid="column"]:has([data-testid="stPopover"]) {
            display: flex;
            align-items: flex-start;
            justify-content: flex-end;
            padding-top: 0.15rem;
          }
          /* Popover panel: dark theme — matches sidebar rows (panel is portaled, not under stSidebar) */
          [data-testid="stPopoverContent"],
          [data-testid="stPopoverBody"],
          [data-baseweb="popover"] > div:last-child {
            background: #343541 !important;
            color: #ececf1 !important;
            border: 1px solid #565869 !important;
            border-radius: 6px !important;
            box-shadow: 0 6px 24px rgba(0, 0, 0, 0.45) !important;
            padding: 4px !important;
            overflow: hidden !important;
          }
          [data-testid="stPopoverContent"] [data-testid="stVerticalBlock"],
          [data-testid="stPopoverBody"] [data-testid="stVerticalBlock"] {
            gap: 0 !important;
          }
          [data-testid="stPopoverContent"] .stButton,
          [data-testid="stPopoverBody"] .stButton {
            margin: 0 !important;
            padding: 0 !important;
          }
          [data-testid="stPopoverContent"] .stButton > button,
          [data-testid="stPopoverBody"] .stButton > button {
            width: 100% !important;
            min-height: 2.25rem !important;
            padding: 0.4rem 0.75rem !important;
            font-size: 0.8125rem !important;
            font-weight: 500 !important;
            border-radius: 4px !important;
            border: none !important;
            background: transparent !important;
            color: #ececf1 !important;
            -webkit-text-fill-color: #ececf1 !important;
            box-shadow: none !important;
            justify-content: flex-start !important;
          }
          [data-testid="stPopoverContent"] .stButton > button:hover,
          [data-testid="stPopoverBody"] .stButton > button:hover {
            background: #40414f !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
          }
          [data-testid="stPopoverContent"] .stButton > button[kind="primary"],
          [data-testid="stPopoverBody"] .stButton > button[kind="primary"] {
            background: transparent !important;
            color: #ececf1 !important;
          }
          /* Last pass: session row chips (after theme / emotion) — force dark fill + readable label */
          [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div:first-child button,
          [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div:first-child [data-baseweb="button"] {
            background-color: #343541 !important;
            background: #343541 !important;
            background-image: none !important;
            color: #ececf1 !important;
            -webkit-text-fill-color: #ececf1 !important;
            border: 1px solid #565869 !important;
          }
          /*
           * Widget `help=` tooltips use Base Web popover + stTooltipContent (portaled to body).
           * Mixed light main / dark sidebar themes often yield white panels + white text.
           */
          [data-testid="stTooltipContent"],
          [data-testid="stTooltipErrorContent"],
          .stTooltipContent,
          .stTooltipErrorContent {
            background-color: #2f2f2f !important;
            background: #2f2f2f !important;
            color: #ececf1 !important;
            border: 1px solid #52525b !important;
            border-radius: 8px !important;
            box-shadow: 0 6px 24px rgba(0, 0, 0, 0.45) !important;
            -webkit-text-fill-color: #ececf1 !important;
          }
          [data-testid="stTooltipContent"] *,
          [data-testid="stTooltipErrorContent"] * {
            color: #ececf1 !important;
            -webkit-text-fill-color: #ececf1 !important;
          }
          [data-testid="stTooltipContent"] div,
          [data-testid="stTooltipErrorContent"] div {
            background-color: transparent !important;
            background: transparent !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "api_base" not in st.session_state:
        st.session_state.api_base = DEFAULT_API
    if "current_session_label" not in st.session_state:
        st.session_state.current_session_label = "New session"


def api_url(path: str) -> str:
    base = st.session_state.api_base.rstrip("/")
    return f"{base}{path}"


def health_check() -> tuple[bool, str]:
    try:
        r = requests.get(api_url("/docs"), timeout=3)
        return r.status_code == 200, "Connected"
    except requests.RequestException as e:
        return False, str(e)[:120]


def fetch_all_chats() -> list[dict[str, Any]]:
    # Slim list is fast; Mongo uses short timeouts server-side (see app/db/mongo.py).
    r = requests.get(api_url("/api/v1/chats"), timeout=15)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


def fetch_chat_session(session_id: str) -> dict[str, Any]:
    r = requests.get(api_url(f"/api/v1/chat/{session_id}"), timeout=60)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, dict) else {}


def iter_chat_stream(message: str) -> Iterator[str]:
    """Stream assistant tokens from the API (lower perceived latency)."""
    url = api_url("/api/v1/chat/stream")
    with httpx.Client(timeout=httpx.Timeout(120.0)) as client:
        with client.stream(
            "POST",
            url,
            json={
                "session_id": st.session_state.session_id,
                "message": message,
            },
        ) as response:
            response.raise_for_status()
            for part in response.iter_text():
                if part:
                    yield part


def delete_remote_session(session_id: str) -> None:
    r = requests.delete(api_url(f"/api/v1/chat/{session_id}"), timeout=30)
    if r.status_code == 404:
        raise ValueError("Session not found on server.")
    r.raise_for_status()


def patch_session_name(session_id: str, name: str) -> None:
    r = requests.patch(
        api_url(f"/api/v1/chat/{session_id}"),
        json={"name": name},
        timeout=30,
    )
    r.raise_for_status()


def ensure_remote_session(session_id: str) -> None:
    """Persist an empty chat so the sidebar list shows this session without Refresh."""
    try:
        r = requests.post(
            api_url(f"/api/v1/chat/{session_id}/ensure"),
            timeout=15,
        )
        r.raise_for_status()
    except requests.RequestException:
        pass


def session_display_title(chat_doc: dict[str, Any]) -> str:
    n = (chat_doc.get("name") or "").strip()
    if n.lower() in (
        "untitled chat",
        "untitled",
        "untilled chat",
        "untilled",
        "new chat",
        "new session",
    ):
        return "Untitled chat"
    if n:
        return n
    sid = chat_doc.get("session_id") or ""
    if len(sid) > 10:
        return f"Session {sid[:8]}…"
    return sid or "Untitled"


@st.dialog("Rename session")
def rename_session_dialog(session_id: str, current_name: str) -> None:
    new_name = st.text_input(
        "Session name",
        value=current_name,
        max_chars=200,
        key=f"dlg_rename_input_{session_id}",
    )
    c1, c2 = st.columns(2)
    if c1.button("Save", type="primary", key=f"dlg_save_{session_id}"):
        label = new_name.strip()
        if not label:
            st.error("Name cannot be empty.")
            return
        try:
            patch_session_name(session_id, label)
            if session_id == st.session_state.session_id:
                st.session_state.current_session_label = label
            st.rerun()
        except requests.RequestException as e:
            st.error(str(e))
    if c2.button("Cancel", key=f"dlg_cancel_{session_id}"):
        st.rerun()


def normalize_messages(raw: Any) -> list[dict[str, str]]:
    if not raw:
        return []
    out = []
    for m in raw:
        if isinstance(m, dict) and "role" in m and "content" in m:
            out.append({"role": m["role"], "content": str(m["content"])})
    return out


def format_ts(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return value[:16]
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return ""


def render_user_message(content: str) -> None:
    # Wide right column so the bubble sits on the right like ChatGPT
    _, right = st.columns([1, 11])
    with right:
        with st.chat_message("user", avatar=_USER_AVATAR, width="content"):
            st.markdown(content)


def render_assistant_message(content: str) -> None:
    left, _ = st.columns([11, 1])
    with left:
        with st.chat_message("assistant", avatar=_AI_AVATAR, width="content"):
            st.markdown(content)


def main() -> None:
    st.set_page_config(
        page_title="Intellectual AI",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_state()
    inject_styles()

    with st.sidebar:
        with st.expander("Connection", expanded=False):
            st.session_state.api_base = st.text_input(
                "API base URL",
                value=st.session_state.api_base,
                help="FastAPI service URL, e.g. http://127.0.0.1:8000",
                label_visibility="visible",
            )
            ok, status = health_check()
            if ok:
                st.markdown(
                    '<p class="status-dot"><span style="color:#3dd68c;">●</span> '
                    + status
                    + "</p>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<p class="status-dot"><span style="color:#f4a261;">●</span> Unavailable</p>',
                    unsafe_allow_html=True,
                )
                st.caption(status[:180])

        st.divider()
        if st.button("New chat", type="primary", use_container_width=True):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.session_state.current_session_label = "New session"
            ensure_remote_session(st.session_state.session_id)
            st.rerun()

        st.markdown("**Conversations**")
        session_search = st.text_input(
            "Search sessions",
            key="sidebar_session_search",
            placeholder="Search sessions…",
            label_visibility="collapsed",
        )

        try:
            chats = fetch_all_chats()
            chats_sorted = sorted(
                chats,
                key=lambda c: c.get("created_at") or "",
                reverse=True,
            )
            q = (session_search or "").strip().lower()

            def _session_matches(chat: dict[str, Any]) -> bool:
                if not q:
                    return True
                title = session_display_title(chat).lower()
                sid = (chat.get("session_id") or "").lower()
                return q in title or q in sid

            visible_chats = [c for c in chats_sorted if _session_matches(c)][:25]
            if not visible_chats and q:
                st.caption("No sessions match your search.")
            for c in visible_chats:
                sid = c.get("session_id") or ""
                title = session_display_title(c)
                ts = format_ts(c.get("created_at"))
                hint = f"{ts}" if ts else None
                col_row, col_menu = st.columns([11, 1])
                with col_row:
                    if st.button(
                        title,
                        key=f"open_{sid}",
                        type="tertiary",
                        use_container_width=True,
                        help=hint,
                    ):
                        try:
                            doc = fetch_chat_session(sid)
                            st.session_state.session_id = sid
                            st.session_state.messages = normalize_messages(
                                doc.get("messages")
                            )
                            st.session_state.current_session_label = session_display_title(
                                doc
                            )
                            st.rerun()
                        except requests.RequestException as e:
                            st.error(f"Could not load conversation: {e}")
                with col_menu:
                    with st.popover(
                        "\u200b",
                        icon=":material/more_vert:",
                        use_container_width=True,
                        help="Conversation actions",
                    ):
                        if st.button(
                            "Rename",
                            key=f"edit_{sid}",
                            use_container_width=True,
                        ):
                            rename_session_dialog(sid, title)
                        if st.button(
                            "Delete",
                            key=f"delete_{sid}",
                            use_container_width=True,
                        ):
                            try:
                                delete_remote_session(sid)
                                if sid == st.session_state.session_id:
                                    st.session_state.session_id = str(uuid.uuid4())
                                    st.session_state.messages = []
                                    st.session_state.current_session_label = "New session"
                                st.rerun()
                            except (requests.RequestException, ValueError) as e:
                                st.error(str(e))
        except requests.HTTPError as e:
            detail = ""
            try:
                detail = (e.response.json() or {}).get("detail", "")
            except (ValueError, requests.RequestException):
                pass
            msg = detail or str(e)
            st.caption(f"Unable to load conversations: {msg}")
        except requests.RequestException as e:
            st.caption(f"Unable to load conversations: {e}")

        st.divider()
        st.caption("Active")
        st.markdown(f"**{st.session_state.current_session_label}**")
        st.caption(st.session_state.session_id[:13] + "…")

    bar_left, bar_right = st.columns([5, 1], vertical_alignment="center")
    with bar_left:
        st.markdown(
            f"""
            <div class="gpt-topbar" role="banner">
              <p class="gpt-topbar-model">Intellectual AI</p>
              <h1 class="gpt-topbar-title">{html.escape(st.session_state.current_session_label)}</h1>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with bar_right:
        if st.button(
            "☰ Menu",
            key="intellectual_show_sidebar",
            help="Open conversations & Connection (sidebar)",
            use_container_width=True,
        ):
            _expand_sidebar_via_browser()

    chat_body = st.container()
    with chat_body:
        if not st.session_state.messages:
            st.markdown(
                """
                <div style="text-align:center;padding:2.5rem 1rem 1.5rem;max-width:28rem;margin:0 auto;">
                  <p style="margin:0 0 0.35rem;font-size:1.05rem;font-weight:600;color:#0d0d0d;">
                    Jeffry the Genius
                  </p>
                  <p style="margin:0;color:#6b7280;font-size:0.95rem;line-height:1.5;">
                    Use the message box at the <strong>bottom</strong> of this chat. Replies stream from
                    <code style="background:#ececf1;padding:0.12rem 0.35rem;border-radius:4px;">/api/v1/chat/stream</code>.
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        for msg in st.session_state.messages:
            role = msg.get("role", "user")
            text = msg.get("content", "")
            if role == "user":
                render_user_message(text)
            else:
                render_assistant_message(text)

    raw_prompt = st.chat_input("Message…", key="intellectual_chat_input")
    if raw_prompt and str(raw_prompt).strip():
        prompt = str(raw_prompt).strip()
        st.session_state.messages.append({"role": "user", "content": prompt})
        render_user_message(prompt)

        left, _ = st.columns([11, 1])
        with left:
            with st.chat_message("assistant", avatar=_AI_AVATAR, width="content"):
                try:
                    full = st.write_stream(iter_chat_stream(prompt))
                    st.session_state.messages.append(
                        {"role": "assistant", "content": full or ""}
                    )
                    prev_label = st.session_state.current_session_label
                    try:
                        doc = fetch_chat_session(st.session_state.session_id)
                        st.session_state.current_session_label = (
                            session_display_title(doc)
                        )
                    except requests.RequestException:
                        if st.session_state.current_session_label == "New session":
                            st.session_state.current_session_label = "Untitled chat"
                    # Sidebar / top bar render before this block; rerun once when title updates
                    # so the active session name and conversation list refresh immediately.
                    if st.session_state.current_session_label != prev_label:
                        st.rerun()
                except httpx.HTTPStatusError as e:
                    st.error(
                        f"HTTP {e.response.status_code}. Confirm the API is running and "
                        "`/api/v1/chat/stream` exists."
                    )
                except (httpx.RequestError, requests.RequestException) as e:
                    st.error(f"Request failed: {e}")


main()
