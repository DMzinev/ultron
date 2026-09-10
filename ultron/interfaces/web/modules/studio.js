/**
 * Ultron Web SPA — Pillar 3: AI Agent Studio Module
 * Layer 2 Feature Module: Mission envelope synthesis, format switching, clipboard export.
 */

import { state } from "./state.js";
import { $, api, showToast } from "./api.js";

export async function compileAgentMission() {
  const repo = state.repo || $("repo-input").value.trim() || ".";
  const targetFile = $("studio-target-file").value.trim();
  const intent = $("studio-intent").value.trim();
  const btn = $("studio-compile-btn");
  const output = $("studio-output");

  if (btn) {
    btn.disabled = true;
    btn.textContent = "Compiling grounded briefing…";
  }
  if (output) {
    output.textContent = "// Synthesizing AST boundaries, complexity limits, and verification requirements…";
  }

  try {
    if (state.studioFormat === "contract") {
      const res = await api("/api/generate", { repo, intent: intent || "Implement requested changes with zero revision debt", target_files: targetFile ? [targetFile] : [] });
      if (output) output.textContent = res.prompt || JSON.stringify(res, null, 2);
      if ($("studio-output-title")) $("studio-output-title").textContent = "Ultron Pre-Execution Zero-Revision Contract";
    } else {
      const res = await api("/api/v1/context-brief", { repo, target_file: targetFile, intent });
      const handoff = res.handoff || {};
      const rendered = handoff[state.studioFormat] || JSON.stringify(res, null, 2);
      if (output) output.textContent = rendered;
      const titles = {
        claude: "Claude Code CLI Handoff",
        codex: "OpenAI Codex System Markdown Brief",
        antigravity: "Google Antigravity / Gemini Architectural Brief"
      };
      if ($("studio-output-title")) $("studio-output-title").textContent = titles[state.studioFormat] || "Agent Mission Package";
    }

    if (output) {
      const lines = output.textContent.split("\n").length;
      const chars = output.textContent.length;
      if ($("studio-output-stats")) $("studio-output-stats").textContent = `${lines} lines · ~${Math.round(chars / 4)} tokens · Grounded in AST`;
    }
    showToast("Mission package compiled successfully");
  } catch (err) {
    if (output) output.textContent = `// Compilation failed: ${err.message}`;
    if ($("studio-output-stats")) $("studio-output-stats").textContent = "Error";
    showToast(`Error: ${err.message}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Compile Agent Mission Package";
    }
  }
}

export async function copyStudioOutput() {
  const output = $("studio-output");
  const text = output ? output.textContent : "";
  try {
    await navigator.clipboard.writeText(text);
    showToast("Mission copied to clipboard!");
  } catch (_) {
    showToast("Please copy directly from the view.");
  }
}

export function downloadStudioOutput() {
  const output = $("studio-output");
  const text = output ? output.textContent : "";
  const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `ultron-mission-${Date.now()}.md`;
  a.click();
  showToast("Saved mission file");
}
