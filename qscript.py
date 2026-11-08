import math
import os
import random
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

_mouse_pos = [0.0, 0.0]

def smooth_move(page, x, y, duration=0.8):
  sx, sy = _mouse_pos
  steps = max(20, int(duration * 60))
  for i in range(1, steps + 1):
    t = i / steps
    k = (1 - math.cos(math.pi * t)) / 2
    page.mouse.move(sx + (x - sx) * k, sy + (y - sy) * k)
    page.wait_for_timeout(duration * 1000 / steps)
  _mouse_pos[:] = [x, y]


def human_click(page, locator):
  box = locator.bounding_box()
  x = box["x"] + box["width"] / 2
  y = box["y"] + box["height"] / 2
  smooth_move(page, x, y, duration=random.uniform(0.6, 1.0))
  page.wait_for_timeout(150)
  page.mouse.click(x, y)

def CaptureVideo_Magento(url, company_name, language, country, postcode, city, street, house_no):
  _mouse_pos[:] = [0.0, 0.0]

  try:
    with sync_playwright() as p:
      browser = p.chromium.launch(headless=False)

      context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        record_video_dir=PATH_TO_VIDEO_FOLDER,
        record_video_size={"width": 1280, "height": 720},
      )

      context.add_init_script(OVERLAY_JS)

      page = context.new_page()

      page.goto(url)

      human_click(page, page.locator('textarea[name="q"]'))

      page.keyboard.type(f"Magento developer in {city}", delay=120)

      human_click(page, page.locator('form button[type="submit"]:visible').first)

      first = page.locator('a[data-testid="result-title-a"]').first
      first.wait_for(timeout=30000)
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
      return dst

  except Exception as e:
    print(f"[{company_name}] Ошибка: {e}")
    return None