const statusText = document.getElementById("statusText");
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const processBtn = document.getElementById("processBtn");
const progress = document.getElementById("progress");
const results = document.getElementById("results");
const lastOutputPath = document.getElementById("lastOutputPath");

const llmModelPath = document.getElementById("llmModelPath");
const logoPath = document.getElementById("logoPath");
const settingsForm = document.getElementById("settingsForm");

const firmForm = document.getElementById("firmForm");
const firmName = document.getElementById("firmName");
const ustId = document.getElementById("ustId");
const steuerNr = document.getElementById("steuerNr");
const strasse = document.getElementById("strasse");
const plz = document.getElementById("plz");
const ort = document.getElementById("ort");
const land = document.getElementById("land");
const zahlungsart = document.getElementById("zahlungsart");
const iban = document.getElementById("iban");
const bic = document.getElementById("bic");

function setStatus(text) {
  statusText.textContent = text;
}

async function loadSettings() {
  try {
    const res = await fetch("/api/settings");
    const data = await res.json();
    llmModelPath.value = data.llm_model_path || "";
    logoPath.value = data.logo_path || "";
    if (data.last_output_path) {
      lastOutputPath.textContent = `Letzter Ausgabeordner: ${data.last_output_path}`;
    }
  } catch (e) {
    console.warn("Konnte Einstellungen nicht laden", e);
  }
}

async function saveSettings(evt) {
  evt.preventDefault();
  const payload = {
    llm_model_path: llmModelPath.value,
    logo_path: logoPath.value,
  };
  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  setStatus("Einstellungen gespeichert");
}

async function loadFirm() {
  try {
    const res = await fetch("/api/firmendaten");
    const d = await res.json();
    firmName.value = d.name || "";
    ustId.value = d.umsatzsteuer_id || "";
    steuerNr.value = d.steuernummer || "";
    strasse.value = (d.anschrift && d.anschrift.strasse) || "";
    plz.value = (d.anschrift && d.anschrift.plz) || "";
    ort.value = (d.anschrift && d.anschrift.ort) || "";
    land.value = (d.anschrift && d.anschrift.land) || "DE";
    zahlungsart.value = (d.zahlung && d.zahlung.zahlungsart) || "SEPA";
    iban.value = (d.zahlung && d.zahlung.iban) || "";
    bic.value = (d.zahlung && d.zahlung.bic) || "";
  } catch (e) {
    console.warn("Konnte Firmendaten nicht laden", e);
  }
}

async function saveFirm(evt) {
  evt.preventDefault();
  const payload = {
    name: firmName.value,
    umsatzsteuer_id: ustId.value,
    steuernummer: steuerNr.value,
    anschrift: {
      strasse: strasse.value,
      plz: plz.value,
      ort: ort.value,
      land: land.value,
    },
    zahlung: {
      zahlungsart: zahlungsart.value,
      iban: iban.value,
      bic: bic.value,
    },
  };
  await fetch("/api/firmendaten", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  setStatus("Firmendaten gespeichert");
}

function setupDropzone() {
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
    }
  });

  dropzone.addEventListener("click", () => fileInput.click());
}

async function processFile() {
  const file = fileInput.files && fileInput.files[0];
  if (!file) {
    setStatus("Bitte zuerst eine Datei auswählen.");
    return;
  }

  results.innerHTML = "";
  progress.hidden = false;
  setStatus("Verarbeitung gestartet...");

  const fd = new FormData();
  fd.append("file", file);

  try {
    const res = await fetch("/api/process", { method: "POST", body: fd });
    const data = await res.json();

    progress.hidden = true;
    setStatus("Verarbeitung abgeschlossen.");

    const items = [
      ["Rohtext", data.files?.raw_text],
      ["Canonical JSON", data.files?.canonical_json],
      ["XRechnung XML", data.files?.xrechnung_xml],
      ["ZUGFeRD XML", data.files?.zugferd_xml],
      ["ZUGFeRD PDF/A-3", data.files?.zugferd_pdf],
    ];

    items.forEach(([label, path]) => {
      if (!path) return;
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.textContent = label;
      a.href = path;
      a.target = "_blank";
      li.appendChild(a);
      results.appendChild(li);
    });

    if (data.output_directory) {
      lastOutputPath.textContent = `Letzter Ausgabeordner: ${data.output_directory}`;
    }
  } catch (e) {
    progress.hidden = true;
    setStatus("Fehler bei der Verarbeitung.");
    console.error(e);
  }
}

settingsForm.addEventListener("submit", saveSettings);
firmForm.addEventListener("submit", saveFirm);
processBtn.addEventListener("click", processFile);

setupDropzone();
loadSettings();
loadFirm();