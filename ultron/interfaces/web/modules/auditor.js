/**
 * Ultron Web SPA — Pillar 4: Code Auditor Module
 * Layer 2 Feature Module: Pre-execution safety gates, anomaly inspection, and policy verification.
 */

import { state } from "./state.js";
import { $, esc, api } from "./api.js";

export async function runCodeAudit() {
  const repo = state.repo || $("repo-input").value.trim() || ".";
  const btn = $("auditor-run-btn");
  const shield = $("auditor-shield");
  const shieldIcon = $("auditor-shield-icon");
  const shieldText = $("auditor-shield-text");
  const verdictTitle = $("auditor-verdict-title");
  const verdictDesc = $("auditor-verdict-desc");
  const list = $("auditor-anomalies-list");

  if (btn) {
    btn.disabled = true;
    btn.textContent = "Auditing against rules & baseline…";
  }
  if (shield) shield.className = "auditor-shield";
  if (shieldIcon) shieldIcon.textContent = "⋯";
  if (shieldText) shieldText.textContent = "Checking";

  const typoSlider = $("auditor-slider-typo");
  const typoThreshold = typoSlider ? (parseFloat(typoSlider.value) / 100) : 0.05;

  const payload = {
    repo,
    typo_threshold: typoThreshold
  };

  const isSandbox = state.auditorSource === "sandbox";
  if (isSandbox) {
    const sandboxCode = $("auditor-sandbox-code");
    payload.code = sandboxCode ? sandboxCode.value : "";
  } else {
    const fileInput = $("auditor-file-input");
    payload.target_file = fileInput ? fileInput.value.trim() : "";
  }

  try {
    const res = await api("/api/audit", payload);
    if (!res.success) {
      throw new Error(res.error || "Audit Incomplete");
    }
    const anomalies = res.anomalies || [];

    const targetPath = payload.target_file || "";
    const fileViolations = (state.violations || []).filter((v) => targetPath && v.filepath && v.filepath.includes(targetPath));

    const totalIssues = anomalies.length + fileViolations.length;

    if (totalIssues === 0) {
      if (shield) shield.className = "auditor-shield clean";
      if (shieldIcon) shieldIcon.textContent = "✓";
      if (shieldText) shieldText.textContent = "Safe";
      if (verdictTitle) verdictTitle.textContent = "Code Safety Gate Passed";
      if (verdictDesc) verdictDesc.textContent = "No typo drift, signature mismatches, or architectural policy violations found.";
      if (list) list.innerHTML = `<div class="pane-note">All identifiers, signatures, and call sequences comply with baseline rules.</div>`;
    } else {
      if (shield) shield.className = "auditor-shield anomaly";
      if (shieldIcon) shieldIcon.textContent = "!";
      if (shieldText) shieldText.textContent = "Alert";
      if (verdictTitle) verdictTitle.textContent = `${totalIssues} Issue${totalIssues === 1 ? "" : "s"} Detected`;
      if (verdictDesc) verdictDesc.textContent = "Anomalies or policy constraints require verification before merge.";

      const items = [];
      anomalies.forEach((a) => {
        const isTypo = a.type && a.type.toLowerCase().includes("typo");
        items.push(`<div class="anomaly-item ${isTypo ? "typo" : "markov"}">
          <div class="anomaly-title">${esc(a.type || "Code Anomaly")} in line ${esc(a.line || "?")}</div>
          <div class="anomaly-desc">${esc(a.description || a.message || "")}</div>
          ${a.suggestion ? `<div class="anomaly-fix">Suggested: ${esc(a.suggestion)}</div>` : ""}
        </div>`);
      });

      fileViolations.forEach((v) => {
        items.push(`<div class="anomaly-item markov">
          <div class="anomaly-title">Architectural Policy: ${esc(v.principle || "Rule")}</div>
          <div class="anomaly-desc">${esc(v.observation || v.reason || "")}</div>
          ${v.consequences ? `<div class="anomaly-fix">Consequence: ${esc(v.consequences)}</div>` : ""}
        </div>`);
      });

      if (list) list.innerHTML = items.join("");
    }
  } catch (err) {
    if (shield) shield.className = "auditor-shield anomaly";
    if (shieldIcon) shieldIcon.textContent = "✕";
    if (shieldText) shieldText.textContent = "Error";
    if (verdictTitle) verdictTitle.textContent = "Audit Failed";
    if (verdictDesc) verdictDesc.textContent = err.message;
    if (list) list.innerHTML = `<div class="pane-note">${esc(err.message)}</div>`;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Run Code Safety Audit";
    }
  }
}
