const state = {
  tools: [],
  generatedTools: [],
  filteredTools: [],
  filteredGeneratedTools: [],
  promptTemplates: [],
  selectedTool: null,
  selectedGeneratedTool: null,
  lastPlan: null,
  pendingRunArgs: {},
};

const STORAGE_KEYS = {
  leftCollapsed: "deepseek.demo.sidebar.leftCollapsed",
  rightCollapsed: "deepseek.demo.sidebar.rightCollapsed",
  compactDensity: "deepseek.demo.ui.compactDensity",
  promptTemplates: "deepseek.demo.promptTemplates",
};

const DEFAULT_TEMPLATES = [
  {
    id: "normal-summary",
    name: "Summarize Context",
    text: "Summarize the current project context and list the top 3 next actions.",
  },
  {
    id: "tool-use-plan",
    name: "Tool Use Plan",
    text: "Plan which tool to use, expected arguments, and safety checks before running.",
  },
  {
    id: "tool-builder-spec",
    name: "Build Tool Spec",
    text: "Create a tool plan with goal, inputs, outputs, files, safety risks, and test plan.",
  },
];

const memoryStore = new Map();

function safeGet(key) {
  try {
    const value = window.localStorage.getItem(key);
    if (value !== null) {
      return value;
    }
  } catch {
    // Ignore storage access errors and fall back to memory.
  }
  return memoryStore.has(key) ? memoryStore.get(key) : null;
}

function safeSet(key, value) {
  memoryStore.set(key, value);
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Ignore storage access errors and keep in-memory fallback.
  }
}

function makeId() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  return `tpl-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
}

const chatMessages = document.getElementById("chatMessages");
const toolList = document.getElementById("toolList");
const permissionPreview = document.getElementById("permissionPreview");
const execLogs = document.getElementById("execLogs");
const outputViewer = document.getElementById("outputViewer");
const modelSelect = document.getElementById("modelSelect");
const customModel = document.getElementById("customModel");
const chatMode = document.getElementById("chatMode");
const chatInput = document.getElementById("chatInput");
const apiKeyStatus = document.getElementById("apiKeyStatus");
const apiKeyInput = document.getElementById("apiKeyInput");
const toggleApiKeyBtn = document.getElementById("toggleApiKey");
const tabChat = document.getElementById("tabChat");
const tabGeneratedTools = document.getElementById("tabGeneratedTools");
const chatView = document.getElementById("chatView");
const generatedToolsView = document.getElementById("generatedToolsView");
const generatedToolList = document.getElementById("generatedToolList");
const generatedToolDetails = document.getElementById("generatedToolDetails");
const toolSearch = document.getElementById("toolSearch");
const generatedToolSearch = document.getElementById("generatedToolSearch");
const activeModeBadge = document.getElementById("activeModeBadge");
const toolCountBadge = document.getElementById("toolCountBadge");
const generatedCountBadge = document.getElementById("generatedCountBadge");
const chatHint = document.getElementById("chatHint");
const bodyEl = document.body;
const toggleLeftSidebar = document.getElementById("toggleLeftSidebar");
const toggleRightSidebar = document.getElementById("toggleRightSidebar");
const densityToggle = document.getElementById("densityToggle");
const templateSelect = document.getElementById("templateSelect");
const applyTemplateBtn = document.getElementById("applyTemplate");
const saveTemplateBtn = document.getElementById("saveTemplate");
const deleteTemplateBtn = document.getElementById("deleteTemplate");

function nowStamp() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function prettyType(type) {
  return String(type || "assistant").replaceAll("_", " ");
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || JSON.stringify(data));
  }
  return data;
}

function addMessage(type, text, extra = null) {
  const el = document.createElement("div");
  el.className = `message ${type}`;
  el.innerHTML = `
    <div class="message-header">
      <strong>${escapeHtml(prettyType(type))}</strong>
      <span class="message-time">${escapeHtml(nowStamp())}</span>
    </div>
    <div>${escapeHtml(text)}</div>
  `;
  if (extra) {
    const pre = document.createElement("pre");
    pre.className = "pre";
    pre.textContent = JSON.stringify(extra, null, 2);
    el.appendChild(pre);
  }
  chatMessages.appendChild(el);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function loadHealth() {
  const health = await request("/api/health");
  apiKeyStatus.textContent = health.deepseek_key_configured
    ? "API key configured"
    : "API key missing";
  apiKeyStatus.style.background = health.deepseek_key_configured ? "#daf4e5" : "#fde7e7";
}

async function saveApiKey() {
  const apiKey = apiKeyInput.value.trim();
  try {
    const result = await request("/api/config/api-key", {
      method: "POST",
      body: JSON.stringify({ api_key: apiKey }),
    });
    if (result.configured) {
      addMessage("tool_result", `API key saved (${result.masked_key})`);
    } else {
      addMessage("tool_result", "API key cleared");
    }

    // Always return to hidden mode after save/clear for shoulder-surfing safety.
    apiKeyInput.type = "password";
    toggleApiKeyBtn.textContent = "Show";
    toggleApiKeyBtn.setAttribute("aria-pressed", "false");

    await loadHealth();
  } catch (error) {
    addMessage("validation_error", error.message);
  }
}

function toggleApiKeyVisibility() {
  if (apiKeyInput.type === "password") {
    apiKeyInput.type = "text";
    toggleApiKeyBtn.textContent = "Hide";
    toggleApiKeyBtn.setAttribute("aria-pressed", "true");
  } else {
    apiKeyInput.type = "password";
    toggleApiKeyBtn.textContent = "Show";
    toggleApiKeyBtn.setAttribute("aria-pressed", "false");
  }
}

async function loadModels() {
  const payload = await request("/api/models");
  modelSelect.innerHTML = "";
  payload.presets.forEach((m) => {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = m;
    if (m === payload.configured_model) {
      opt.selected = true;
    }
    modelSelect.appendChild(opt);
  });
}

async function loadTools() {
  const payload = await request("/api/tools");
  state.tools = payload.tools || [];
  applyToolFilter();
  renderTools();
  syncCounters();
}

async function loadGeneratedTools() {
  const payload = await request("/api/generated-tools");
  state.generatedTools = payload.tools || [];
  applyGeneratedToolFilter();
  renderGeneratedTools();
  syncCounters();
}

function applyToolFilter() {
  const query = (toolSearch.value || "").trim().toLowerCase();
  state.filteredTools = state.tools.filter((tool) => {
    if (!query) return true;
    const blob = [tool.name, tool.description, tool.risk_level].join(" ").toLowerCase();
    return blob.includes(query);
  });
}

function applyGeneratedToolFilter() {
  const query = (generatedToolSearch.value || "").trim().toLowerCase();
  state.filteredGeneratedTools = state.generatedTools.filter((tool) => {
    if (!query) return true;
    const blob = [tool.name, tool.path, tool.description, tool.risk_level].join(" ").toLowerCase();
    return blob.includes(query);
  });
}

function syncCounters() {
  toolCountBadge.textContent = `Tools: ${state.tools.length}`;
  generatedCountBadge.textContent = `Generated: ${state.generatedTools.length}`;
}

function readBool(key) {
  return safeGet(key) === "1";
}

function writeBool(key, value) {
  safeSet(key, value ? "1" : "0");
}

function applySidebarState() {
  const leftCollapsed = readBool(STORAGE_KEYS.leftCollapsed);
  const rightCollapsed = readBool(STORAGE_KEYS.rightCollapsed);
  bodyEl.classList.toggle("sidebar-left-collapsed", leftCollapsed);
  bodyEl.classList.toggle("sidebar-right-collapsed", rightCollapsed);
  toggleLeftSidebar.textContent = leftCollapsed ? "Show Settings" : "Hide Settings";
  toggleRightSidebar.textContent = rightCollapsed ? "Show Registry" : "Hide Registry";
}

function setCompactDensity(enabled) {
  bodyEl.classList.toggle("density-compact", enabled);
  writeBool(STORAGE_KEYS.compactDensity, enabled);
  densityToggle.textContent = `Compact: ${enabled ? "On" : "Off"}`;
}

function loadPromptTemplates() {
  const raw = safeGet(STORAGE_KEYS.promptTemplates);
  if (!raw) {
    state.promptTemplates = [...DEFAULT_TEMPLATES];
    return;
  }

  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      state.promptTemplates = [...DEFAULT_TEMPLATES];
      return;
    }
    state.promptTemplates = parsed
      .filter((item) => item && typeof item.name === "string" && typeof item.text === "string")
      .map((item) => ({
        id: String(item.id || makeId()),
        name: item.name.trim() || "Untitled",
        text: item.text,
      }));
    if (!state.promptTemplates.length) {
      state.promptTemplates = [...DEFAULT_TEMPLATES];
    }
  } catch {
    state.promptTemplates = [...DEFAULT_TEMPLATES];
  }
}

function persistPromptTemplates() {
  safeSet(STORAGE_KEYS.promptTemplates, JSON.stringify(state.promptTemplates));
}

function renderPromptTemplates() {
  templateSelect.innerHTML = "";
  state.promptTemplates.forEach((tpl) => {
    const opt = document.createElement("option");
    opt.value = tpl.id;
    opt.textContent = tpl.name;
    templateSelect.appendChild(opt);
  });
}

function selectedTemplate() {
  const id = templateSelect.value;
  return state.promptTemplates.find((tpl) => tpl.id === id) || null;
}

function renderTools() {
  toolList.innerHTML = "";
  if (!state.filteredTools.length) {
    toolList.innerHTML = '<div class="muted-note">No tools match this filter.</div>';
    return;
  }

  state.filteredTools.forEach((tool) => {
    const card = document.createElement("div");
    card.className = "tool-item" + (state.selectedTool === tool.name ? " active" : "");
    card.innerHTML = `
      <strong>${escapeHtml(tool.name || "unnamed")}</strong>
      <div>${escapeHtml(tool.description || "")}</div>
      <small>risk=${escapeHtml(tool.risk_level || "low")} validated=${tool.validated}</small>
    `;
    card.addEventListener("click", () => {
      state.selectedTool = tool.name;
      state.pendingRunArgs = {};
      renderTools();
      permissionPreview.textContent = JSON.stringify(
        {
          selected_tool: tool.name,
          permissions: tool.permissions || [],
          entrypoint: tool.entrypoint,
          working_dir: tool.working_dir,
        },
        null,
        2,
      );
    });
    toolList.appendChild(card);
  });
}

function renderGeneratedTools() {
  generatedToolList.innerHTML = "";
  if (!state.filteredGeneratedTools.length) {
    generatedToolList.innerHTML = '<div class="muted-note">No generated tools match this filter.</div>';
    return;
  }

  state.filteredGeneratedTools.forEach((tool) => {
    const card = document.createElement("div");
    card.className = "tool-item" + (state.selectedGeneratedTool === tool.name ? " active" : "");
    card.innerHTML = `
      <strong>${escapeHtml(tool.name || "unnamed")}</strong>
      <div>${escapeHtml(tool.path || "")}</div>
      <small>registered=${Boolean(tool.registered)} validated=${Boolean(tool.validated)} risk=${escapeHtml(tool.risk_level || "unknown")}</small>
    `;
    card.addEventListener("click", () => {
      state.selectedGeneratedTool = tool.name;
      generatedToolDetails.textContent = JSON.stringify(tool, null, 2);
      if (tool.registered) {
        state.selectedTool = tool.name;
        renderTools();
      }
      renderGeneratedTools();
    });
    generatedToolList.appendChild(card);
  });
}

function activateTab(tabName) {
  const isChat = tabName === "chat";
  tabChat.classList.toggle("active", isChat);
  tabGeneratedTools.classList.toggle("active", !isChat);
  tabChat.setAttribute("aria-selected", isChat ? "true" : "false");
  tabGeneratedTools.setAttribute("aria-selected", isChat ? "false" : "true");
  chatView.classList.toggle("active", isChat);
  generatedToolsView.classList.toggle("active", !isChat);
}

function updateModeUi() {
  const selectedText = chatMode.options[chatMode.selectedIndex]?.text || "Normal Chat";
  activeModeBadge.textContent = `Mode: ${selectedText}`;
  if (chatMode.value === "normal") {
    chatHint.textContent = "Chat with model-aware, mode-specific instructions.";
  } else if (chatMode.value === "tool_use") {
    chatHint.textContent = "Get safer tool suggestions with explicit arguments and preview flow.";
  } else {
    chatHint.textContent = "Design new tools with structured planning and safety constraints.";
  }
}

function selectedModel() {
  const custom = customModel.value.trim();
  if (custom) return custom;
  return modelSelect.value || "deepseek-chat";
}

async function sendChat() {
  const text = chatInput.value.trim();
  if (!text) return;
  addMessage("user", text);
  chatInput.value = "";

  const payload = {
    messages: [{ role: "user", content: text }],
    selected_model: selectedModel(),
    mode: chatMode.value,
    tool_mode: chatMode.value !== "normal",
  };

  try {
    const response = await request("/api/chat", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    addMessage(response.message_type || "assistant", response.assistant || "", {
      tool_suggestions: response.tool_suggestions || [],
    });

    if (response.message_type === "tool_plan" && response.raw) {
      state.lastPlan = response.raw;
    }
  } catch (error) {
    addMessage("validation_error", error.message);
  }
}

async function planTool() {
  const prompt = chatInput.value.trim();
  if (!prompt) {
    addMessage("validation_error", "Enter a prompt in chat box first.");
    return;
  }
  try {
    const response = await request("/api/tools/plan", {
      method: "POST",
      body: JSON.stringify({ prompt, selected_model: selectedModel() }),
    });
    state.lastPlan = response.plan;
    addMessage("tool_plan", "Tool creation plan ready", response.plan);
  } catch (error) {
    addMessage("validation_error", error.message);
  }
}

async function createTool() {
  if (!state.lastPlan) {
    addMessage("validation_error", "No plan available. Use Create Tool after planning.");
    return;
  }
  try {
    const response = await request("/api/tools/create", {
      method: "POST",
      body: JSON.stringify({ plan: state.lastPlan, allow_overwrite: false }),
    });
    addMessage("tool_result", "Tool generated", response.result);
    await loadTools();
  } catch (error) {
    addMessage("validation_error", error.message);
  }
}

async function validateTool() {
  if (!state.selectedTool) {
    addMessage("validation_error", "Select a generated tool from the registry first.");
    return;
  }
  const path = `generated_tools/${state.selectedTool}`;
  try {
    const response = await request("/api/tools/validate", {
      method: "POST",
      body: JSON.stringify({ path }),
    });
    addMessage(response.message_type, "Validation complete", response.result);
  } catch (error) {
    addMessage("validation_error", error.message);
  }
}

async function useTool() {
  if (!state.selectedTool) {
    addMessage("validation_error", "Select a tool in registry first.");
    return;
  }

  let args = {};
  const raw = prompt("Arguments as JSON object", "{}") || "{}";
  try {
    args = JSON.parse(raw);
  } catch {
    addMessage("validation_error", "Invalid JSON args.");
    return;
  }
  state.pendingRunArgs = args;

  try {
    const response = await request("/api/tools/run", {
      method: "POST",
      body: JSON.stringify({ tool_name: state.selectedTool, args, approve: false }),
    });
    permissionPreview.textContent = JSON.stringify(response.validation, null, 2);
    addMessage(response.message_type, "Safety preview ready", response.validation);
  } catch (error) {
    addMessage("validation_error", error.message);
  }
}

async function runTool() {
  if (!state.selectedTool) {
    addMessage("validation_error", "Select a tool first.");
    return;
  }
  try {
    const response = await request("/api/tools/run", {
      method: "POST",
      body: JSON.stringify({
        tool_name: state.selectedTool,
        args: state.pendingRunArgs || {},
        approve: true,
      }),
    });
    execLogs.textContent = JSON.stringify(response.result, null, 2);
    addMessage("tool_result", "Tool execution complete", response.result);

    const artifacts = response.result?.artifacts || [];
    if (artifacts.length) {
      const first = artifacts[0];
      const output = await request(`/api/output?path=${encodeURIComponent(first)}`);
      outputViewer.textContent = JSON.stringify(output, null, 2);
    }
  } catch (error) {
    addMessage("validation_error", error.message);
  }
}

async function openOutputFolder() {
  try {
    const result = await request("/api/open-output-folder");
    outputViewer.textContent = JSON.stringify(result, null, 2);
  } catch (error) {
    addMessage("validation_error", error.message);
  }
}

function clearChat() {
  chatMessages.innerHTML = "";
  execLogs.textContent = "";
  outputViewer.textContent = "";
  permissionPreview.textContent = "";
}

document.getElementById("sendBtn").addEventListener("click", sendChat);
document.getElementById("refreshTools").addEventListener("click", loadTools);
document.getElementById("clearChat").addEventListener("click", clearChat);
document.getElementById("useTool").addEventListener("click", useTool);
document.getElementById("createTool").addEventListener("click", createTool);
document.getElementById("validateTool").addEventListener("click", validateTool);
document.getElementById("runTool").addEventListener("click", runTool);
document.getElementById("openOutput").addEventListener("click", openOutputFolder);
document.getElementById("saveApiKey").addEventListener("click", saveApiKey);
document.getElementById("toggleApiKey").addEventListener("click", toggleApiKeyVisibility);

chatMode.addEventListener("change", () => {
  if (chatMode.value === "normal") {
    chatInput.placeholder = "Ask a direct question or request help with a tool...";
  } else if (chatMode.value === "tool_use") {
    chatInput.placeholder = "Describe the task and desired arguments. The assistant will suggest/use tools.";
  } else {
    chatInput.placeholder = "Describe the tool you want to generate, including inputs, outputs, and safety constraints.";
  }
  if (chatMode.value === "tool_builder") {
    planTool();
  }
  updateModeUi();
});

toolSearch.addEventListener("input", () => {
  applyToolFilter();
  renderTools();
});

generatedToolSearch.addEventListener("input", () => {
  applyGeneratedToolFilter();
  renderGeneratedTools();
});

chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendChat();
  }
});

tabChat.addEventListener("click", () => activateTab("chat"));
tabGeneratedTools.addEventListener("click", () => {
  activateTab("generated_tools");
  loadGeneratedTools().catch((error) => addMessage("validation_error", error.message));
});

document.getElementById("refreshGeneratedTools").addEventListener("click", () => {
  loadGeneratedTools().catch((error) => addMessage("validation_error", error.message));
});

document.getElementById("refreshGeneratedToolsFromSettings").addEventListener("click", () => {
  Promise.all([loadTools(), loadGeneratedTools()]).catch((error) => addMessage("validation_error", error.message));
});

toggleLeftSidebar.addEventListener("click", () => {
  const next = !readBool(STORAGE_KEYS.leftCollapsed);
  writeBool(STORAGE_KEYS.leftCollapsed, next);
  applySidebarState();
});

toggleRightSidebar.addEventListener("click", () => {
  const next = !readBool(STORAGE_KEYS.rightCollapsed);
  writeBool(STORAGE_KEYS.rightCollapsed, next);
  applySidebarState();
});

densityToggle.addEventListener("click", () => {
  const next = !bodyEl.classList.contains("density-compact");
  setCompactDensity(next);
});

applyTemplateBtn.addEventListener("click", () => {
  const tpl = selectedTemplate();
  if (!tpl) {
    addMessage("validation_error", "Select a template to apply.");
    return;
  }
  chatInput.value = tpl.text;
  chatInput.focus();
});

saveTemplateBtn.addEventListener("click", () => {
  const text = chatInput.value.trim();
  if (!text) {
    addMessage("validation_error", "Enter a prompt in chat input before saving a template.");
    return;
  }
  const name = (prompt("Template name", "New Template") || "").trim();
  if (!name) {
    return;
  }

  let nextSelectedId = "";
  const existing = state.promptTemplates.find(
    (tpl) => tpl.name.toLowerCase() === name.toLowerCase(),
  );
  if (existing) {
    existing.text = text;
    nextSelectedId = existing.id;
  } else {
    const entry = { id: makeId(), name, text };
    state.promptTemplates.push(entry);
    nextSelectedId = entry.id;
  }
  persistPromptTemplates();
  renderPromptTemplates();
  if (nextSelectedId) {
    templateSelect.value = nextSelectedId;
  }
  addMessage("tool_result", `Saved template: ${name}`);
});

deleteTemplateBtn.addEventListener("click", () => {
  const tpl = selectedTemplate();
  if (!tpl) {
    addMessage("validation_error", "Select a template to delete.");
    return;
  }
  if (!confirm(`Delete template "${tpl.name}"?`)) {
    return;
  }
  state.promptTemplates = state.promptTemplates.filter((item) => item.id !== tpl.id);
  if (!state.promptTemplates.length) {
    state.promptTemplates = [...DEFAULT_TEMPLATES];
  }
  persistPromptTemplates();
  renderPromptTemplates();
});

(async () => {
  try {
    await loadHealth();
    await loadModels();
    await loadTools();
    await loadGeneratedTools();
    activateTab("chat");
    updateModeUi();
    loadPromptTemplates();
    renderPromptTemplates();
    applySidebarState();
    setCompactDensity(readBool(STORAGE_KEYS.compactDensity));
  } catch (error) {
    addMessage("validation_error", error.message);
  }
})();
