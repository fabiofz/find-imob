"""Centered header controls and accessible feedback during page navigation."""
import time
import streamlit as st

TOP_CONTROLS_CSS = '''<style>
.st-key-top_controls {
    position:fixed !important; top:calc(12px + env(safe-area-inset-top, 0px)) !important;
    left:50% !important; right:auto !important; transform:translateX(-50%);
    z-index:10003; width:224px !important; max-width:calc(100vw - 100px) !important;
    margin:0 !important; padding:0 !important;
}
.st-key-top_controls:has(.st-key-tema_float_open) { width:124px !important; }
.st-key-top_controls > [data-testid="stHorizontalBlock"],
.st-key-top_controls > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
    flex-wrap:nowrap !important; gap:16px !important; align-items:center !important;
}
.st-key-top_controls > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
.st-key-top_controls > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    min-width:0 !important; width:auto !important; flex:0 0 auto !important;
}
.st-key-top_controls [data-testid="stPopover"] { margin:0 !important; }
@media(max-width:760px) {
    .st-key-top_controls { top:calc(10px + env(safe-area-inset-top, 0px)) !important; }
}
</style>'''

NAVIGATION_JS = r'''
export default function() {
  const doc = document;
  const key = '__findimobNavigationFeedback';
  if (!window[key]) {
    const style = doc.createElement('style');
    style.textContent = `
      #findimob-page-loading { position:fixed; inset:0; z-index:2147483000;
        display:none; align-items:center; justify-content:center;
        background:var(--bg,#121212); color:var(--text,#f5f5f5);
        font-family:'DM Sans',sans-serif; }
      #findimob-page-loading[data-visible="true"] { display:flex; }
      #findimob-page-loading .loading-content { display:flex; flex-direction:column;
        align-items:center; gap:18px; padding:24px; text-align:center; }
      #findimob-page-loading .loading-spinner { width:38px; height:38px;
        border:3px solid color-mix(in srgb,#32cb79 22%,transparent);
        border-top-color:#32cb79; border-radius:50%; animation:findimob-nav-spin .8s linear infinite; }
      @keyframes findimob-nav-spin { to { transform:rotate(360deg); } }
      @media(prefers-reduced-motion:reduce) { #findimob-page-loading .loading-spinner { animation:none; } }
    `;
    doc.head.appendChild(style);
    const overlay = doc.createElement('div');
    overlay.id = 'findimob-page-loading';
    overlay.setAttribute('role','status');
    overlay.setAttribute('aria-live','polite');
    overlay.setAttribute('aria-hidden','true');
    overlay.innerHTML = '<div class="loading-content"><span class="loading-spinner" aria-hidden="true"></span><span>Carregando página…</span></div>';
    doc.body.appendChild(overlay);
    let timeout;
    let active = false;
    let sawRunning = false;
    const hide = () => {
      clearTimeout(timeout); active = false; sawRunning = false;
      overlay.dataset.visible = 'false'; overlay.setAttribute('aria-hidden','true');
      doc.body.removeAttribute('aria-busy');
    };
    const show = () => {
      clearTimeout(timeout); active = true; sawRunning = false;
      overlay.dataset.visible = 'true'; overlay.setAttribute('aria-hidden','false');
      doc.body.setAttribute('aria-busy','true');
      // A failed navigation must never leave the page inaccessible.
      timeout = setTimeout(hide,15000);
    };
    doc.addEventListener('click', (event) => {
      const element = event.target instanceof Element ? event.target : event.target?.parentElement;
      if (!element || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      const radio = element.closest('.st-key-pagina label');
      if (radio) {
        if (!radio.querySelector('input')?.checked) show();
        return;
      }
      if (element.closest('.st-key-pagina_mobile button, .st-key-account_menu_edit_profile button')) {
        show(); return;
      }
      const link = element.closest('a[href]');
      if (link && link.target !== '_blank' && !link.hasAttribute('download')) {
        const destination = new URL(link.href, location.href);
        if (destination.origin === location.origin &&
            (destination.pathname !== location.pathname || destination.search !== location.search)) show();
      }
    },true);
    new MutationObserver(() => {
      if (!active) return;
      const state = doc.querySelector('.stApp')?.getAttribute('data-test-script-state');
      if (['running','rerunRequested'].includes(state)) sawRunning = true;
      else if (sawRunning && state === 'notRunning') hide();
    }).observe(doc.documentElement, {subtree:true,attributes:true,attributeFilter:['data-test-script-state']});
    window[key] = { hide };
  }
  // This component is rendered after the destination page's content.
  requestAnimationFrame(() => requestAnimationFrame(() => window[key].hide()));
}
'''

_NAVIGATION = st.components.v2.component('findimob_navigation_feedback', js=NAVIGATION_JS)


def render_navigation_feedback():
    _NAVIGATION(data={'render': time.time_ns()}, key='navigation_feedback')
