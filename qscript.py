import json
import math
import os
import random
import time
from playwright.sync_api import sync_playwright

PATH_TO_VIDEO_FOLDER = "./video"

OVERLAY_JS = r"""
(() => {
  if (window.__pwOverlayInstalled) return;
  window.__pwOverlayInstalled = true;

  const ARROW_SVG = `
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
      <path d="M3 2 L3 25 L9 19.5 L13.5 29 L17.5 27.2 L13 18 L21 18 Z"
            fill="white" stroke="black" stroke-width="2" stroke-linejoin="round"/>
    </svg>`;

  function init() {
    // --- Стили ---
    const style = document.createElement('style');
    style.textContent = `
      #__pw_cursor, #__pw_halo, .__pw_ripple {
        position: fixed; left: 0; top: 0;
        pointer-events: none;
      }
      #__pw_cursor { width: 32px; height: 32px; z-index: 2147483647; }  /* поверх всего */
      #__pw_halo {
        width: 64px; height: 64px; margin: -32px 0 0 -32px;
        border-radius: 50%;
        background: rgba(255, 230, 0, 0.45);
        z-index: 2147483646;
      }
      .__pw_ripple {
        width: 64px; height: 64px; margin: -32px 0 0 -32px;
        border-radius: 50%;
        border: 3px solid rgba(255, 170, 0, 0.9);
        box-sizing: border-box;
        z-index: 2147483646;
        animation: __pw_ripple 0.6s ease-out forwards;
      }
      @keyframes __pw_ripple {
        from { transform: scale(0); opacity: 1; }
        to   { transform: scale(1); opacity: 0; }
      }`;
    document.head.appendChild(style);

    const halo = document.createElement('div');
    halo.id = '__pw_halo';
    const cursor = document.createElement('div');
    cursor.id = '__pw_cursor';
    cursor.innerHTML = ARROW_SVG;
    document.body.appendChild(halo);
    document.body.appendChild(cursor);

    function moveTo(x, y) {
      halo.style.transform = `translate(${x}px, ${y}px)`;
      cursor.style.transform = `translate(${x - 3}px, ${y - 2}px)`;  // острие стрелки = точка мыши
      try { sessionStorage.setItem('__pw_pos', JSON.stringify([x, y])); } catch (e) {}
    }

    let start = [-100, -100];
    try { start = JSON.parse(sessionStorage.getItem('__pw_pos')) || start; } catch (e) {}
    moveTo(start[0], start[1]);

    window.addEventListener('mousemove', e => moveTo(e.clientX, e.clientY), true);

    window.addEventListener('mousedown', e => {
      const r = document.createElement('div');
      r.className = '__pw_ripple';
      r.style.left = e.clientX + 'px';
      r.style.top = e.clientY + 'px';
      document.body.appendChild(r);
      setTimeout(() => r.remove(), 700);
    }, true);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
"""

ZOOM_JS = r"""
(() => {
  if (window.__pwZoomInstalled) return;
  window.__pwZoomInstalled = true;

  // Last mouse position in viewport pixels (= video pixels): F5 zooms around it.
  let mouse = [0, 0];
  try { mouse = JSON.parse(sessionStorage.getItem('__pw_pos')) || mouse; } catch (e) {}
  window.addEventListener('mousemove', e => { mouse = [e.clientX, e.clientY]; }, true);

  function ensureStyle() {
    if (document.getElementById('__pw_zoom_style') || !document.head) return;
    const style = document.createElement('style');
    style.id = '__pw_zoom_style';
    style.textContent = `
      .__pw_zoom_ring {
        position: fixed; left: 0; top: 0; pointer-events: none;
        width: 120px; height: 120px; margin: -60px 0 0 -60px;
        border-radius: 50%; box-sizing: border-box;
        border: 5px solid; z-index: 2147483647;
        animation: __pw_zoom_ring 0.7s ease-out forwards;
      }
      .__pw_zoom_ring.in  { border-color: rgba(0, 200, 80, 0.95); animation-name: __pw_zoom_in; }
      .__pw_zoom_ring.out { border-color: rgba(230, 40, 40, 0.95); animation-name: __pw_zoom_out; }
      @keyframes __pw_zoom_in  { from { transform: scale(1.6); opacity: 1; } to { transform: scale(0.4); opacity: 0; } }
      @keyframes __pw_zoom_out { from { transform: scale(0.4); opacity: 1; } to { transform: scale(1.6); opacity: 0; } }
      #__pw_halo.__pw_zoomed { box-shadow: 0 0 0 4px rgba(0, 200, 80, 0.95); }`;
    document.head.appendChild(style);
  }

  // Brief ring at the zoom point (green = zoom-in, red = zoom-out)
  // and a green outline around the cursor halo while zoomed.
  function showState(state, x, y) {
    if (!document.body) return;
    ensureStyle();
    const halo = document.getElementById('__pw_halo');
    if (halo) halo.classList.toggle('__pw_zoomed', state === 'in');
    if (x === undefined) return;
    const ring = document.createElement('div');
    ring.className = '__pw_zoom_ring ' + state;
    ring.style.left = x + 'px';
    ring.style.top = y + 'px';
    document.body.appendChild(ring);
    setTimeout(() => ring.remove(), 800);
  }

  // Programmatic hook: toggles zoom in/out at (x, y). The state lives in Python
  // (__pwZoomToggle), so it survives navigation. Resolves to "in" or "out".
  window.__zoomAt = (x, y) =>
    window.__pwZoomToggle(x, y).then(state => { showState(state, x, y); return state; });

  // F5 toggles the zoom at the current mouse position instead of reloading the page.
  window.addEventListener('keydown', e => {
    if (e.key !== 'F5') return;
    e.preventDefault();
    e.stopPropagation();
    if (!e.repeat) window.__zoomAt(mouse[0], mouse[1]);
  }, true);

  // After navigation restore the "zoomed" outline.
  function restore() {
    window.__pwZoomState().then(state => showState(state)).catch(() => {});
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', restore);
  } else {
    restore();
  }
})();
"""

ZOOM_SETTINGS = {
  "fps": 25,
  "zoom_factor": 2.0,
  "ramp_sec": 0.5,
}

_mouse_pos = [0.0, 0.0]

def install_zoom_capture(context, viewport):
  """Collects zoom events {t, x, y, type}; t is seconds since the video start.

  Returns (zoom, start_clock). Call start_clock(page) right after context.new_page():
  the video's first frame is the page's first paint, which comes 0.1-0.5 s after the context
  is created (longer with a visible window), so t=0 is taken once a frame has been painted.
  """
  start = [time.monotonic()]
  zoom = {"viewport": dict(viewport), **ZOOM_SETTINGS, "events": []}
  state = {"zoomed": False}

  def start_clock(page):
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    start[0] = time.monotonic()

  def toggle(source, x, y):
    state["zoomed"] = not state["zoomed"]
    kind = "in" if state["zoomed"] else "out"
    zoom["events"].append({
      "t": round(time.monotonic() - start[0], 3),
      "x": round(float(x), 1),
      "y": round(float(y), 1),
      "type": kind,
    })
    return kind

  context.expose_binding("__pwZoomToggle", toggle)
  context.expose_binding("__pwZoomState", lambda source: "in" if state["zoomed"] else "out")
  context.add_init_script(ZOOM_JS)
  return zoom, start_clock

def write_zoom_sidecar(video_path, zoom):
  """<video>.zoom.json next to the video, only if there is at least one event."""
  path = os.path.splitext(video_path)[0] + ".zoom.json"
  if not zoom["events"]:
    if os.path.exists(path):
      os.remove(path)
    return None
  with open(path, "w", encoding="utf-8") as f:
    json.dump(zoom, f, indent=2)
  return path

def zoom_at_cursor(page):
  """Toggles the zoom from the scenario through the same hook as F5."""
  return page.evaluate("([x, y]) => window.__zoomAt(x, y)", list(_mouse_pos))

def smooth_move(page, x, y, duration=0.8):
  sx, sy = _mouse_pos
  steps = max(20, int(duration * 60))
  for i in range(1, steps + 1):
    t = i / steps
    k = (1 - math.cos(math.pi * t)) / 2
    page.mouse.move(sx + (x - sx) * k, sy + (y - sy) * k)
    page.wait_for_timeout(duration * 1000 / steps)
  _mouse_pos[:] = [x, y]


def human_move(page, locator):
  locator.scroll_into_view_if_needed()
  for _ in range(5):
    box = locator.bounding_box()
    x = box["x"] + box["width"] / 2
    y = box["y"] + box["height"] / 2
    smooth_move(page, x, y, duration=random.uniform(0.6, 1.0))
    page.wait_for_timeout(150)
    now = locator.bounding_box()
    if abs(now["x"] - box["x"]) < 1 and abs(now["y"] - box["y"]) < 1:
      break
  return x, y

def human_click(page, locator):
  x, y = human_move(page, locator)
  page.mouse.click(x, y)

def CaptureVideo_Magento(url, company_name, language, country, postcode, city, street, house_no):
  _mouse_pos[:] = [0.0, 0.0]

  try:
    with sync_playwright() as p:
      browser = p.chromium.launch(headless=False)

      viewport = {"width": 1280, "height": 720}
      context = browser.new_context(
        viewport=viewport,
        record_video_dir=PATH_TO_VIDEO_FOLDER,
        record_video_size=viewport,
      )
      zoom, start_zoom_clock = install_zoom_capture(context, viewport)

      context.add_init_script(OVERLAY_JS)

      page = context.new_page()
      start_zoom_clock(page)

      page.goto(url)

      human_click(page, page.locator('textarea[name="q"]'))
      zoom_at_cursor(page)
      page.wait_for_timeout(600)

      page.keyboard.type(f"Magento developer in {city}", delay=120)

      page.wait_for_timeout(500)
      zoom_at_cursor(page)
      page.wait_for_timeout(600)

      human_click(page, page.locator('form button[type="submit"]:visible').first)

      first = page.locator('a[data-testid="result-title-a"]').first
      first.wait_for(timeout=30000)
      human_move(page, first)
      zoom_at_cursor(page)
      page.wait_for_timeout(1500)
      zoom_at_cursor(page)
      page.wait_for_timeout(600)
      human_click(page, first)

      page.wait_for_url(lambda u: "duckduckgo.com" not in u, timeout=30000)

      try:
        page.wait_for_load_state("load", timeout=30000)
      except Exception:
        pass

      page.wait_for_timeout(3000)

      video = page.video
      context.close()
      browser.close()

      src = video.path()
      safe_name = "".join(c for c in company_name if c not in '\\/:*?"<>|').strip()
      dst = os.path.abspath(os.path.join(PATH_TO_VIDEO_FOLDER, safe_name + ".webm"))
      os.replace(src, dst)
      write_zoom_sidecar(dst, zoom)
      return dst

  except Exception as e:
    print(f"[{company_name}] Ошибка: {e}")
    return None