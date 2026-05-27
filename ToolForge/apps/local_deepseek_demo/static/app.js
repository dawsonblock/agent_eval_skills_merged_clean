const state = {
  tools: [],
  generatedTools: [],
  selectedTool: null,
  selectedGeneratedTool: null,
  lastPlan: null,
  pendingRunArgs: {},
};

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
  el.innerHTML = `<strong>${type}</strong><div>${escapeHtml(text)}</div>`;
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
  renderTools();
}

async function loadGeneratedTools() {
  const payload = await request("/api/generated-tools");
  state.generatedTools = payload.tools || [];
  renderGeneratedTools();
}

function renderTools() {
  toolList.innerHTML = "";
  state.tools.forEach((tool) => {
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
  state.generatedTools.forEach((tool) => {
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
});

tabChat.addEventListener("click", () => activateTab("chat"));
tabGeneratedTools.addEventListener("click", () => {
  activateTab("generated_tools");
  loadGeneratedTools().catch((error) => addMessage("validation_error", error.message));
});

document.getElementById("refreshGeneratedTools").addEventListener("click", () => {
  loadGeneratedTools().catch((error) => addMessage("validation_error", error.message));
});

(async () => {
  try {
    await loadHealth();
    await loadModels();
    await loadTools();
    await loadGeneratedTools();
    activateTab("chat");
  } catch (error) {
    addMessage("validation_error", error.message);
  }
})();
