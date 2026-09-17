/**
 * Ultron Web SPA — Folder Picker Module
 * Layer 2 Support Module: Server-side repository directory traversal modal.
 */

import { state } from "./state.js";
import { $, esc, api } from "./api.js";

export async function openPicker(startPath) {
  const box = $("picker");
  if (!box) return;
  box.hidden = false;
  $("picker-list").innerHTML = `<li class="picker-note">Loading…</li>`;
  try {
    const q = startPath ? `?path=${encodeURIComponent(startPath)}` : "";
    const res = await api(`/api/list-dirs${q}`);
    state.pickerPath = res.path;
    $("picker-path").textContent = res.path;
    $("picker-drives").innerHTML = (res.drives || []).map((d) => `<button class="chip-btn" data-path="${esc(d)}">${esc(d)}</button>`).join("");
    const rows = (res.parent ? [`<li class="picker-row" data-path="${esc(res.parent)}">↑ ..</li>`] : [])
      .concat((res.entries || []).map((e) => `<li class="picker-row" data-path="${esc(e.path)}">${esc(e.name)}</li>`));
    $("picker-list").innerHTML = rows.length ? rows.join("") : `<li class="picker-note">No subfolders here.</li>`;
  } catch (err) {
    $("picker-list").innerHTML = `<li class="picker-note">${esc(err.message)}</li>`;
  }
}

export function closePicker() {
  const box = $("picker");
  if (box) box.hidden = true;
}

export function togglePicker(startPath) {
  const box = $("picker");
  if (box && !box.hidden) {
    box.hidden = true;
    return;
  }
  openPicker(startPath);
}

export function setupPickerClickOutside() {
  document.addEventListener("click", (e) => {
    const box = $("picker");
    if (!box || box.hidden) return;
    const browseBtn = $("browse-btn");
    if (browseBtn && (browseBtn === e.target || browseBtn.contains(e.target))) return;
    if (!box.contains(e.target)) {
      box.hidden = true;
    }
  });
}
