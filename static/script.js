document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("qr-form");
  const qrTypeInput = document.getElementById("qr-type-input");
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabPanels = document.querySelectorAll(".tab-panel");
  const tabGlider = document.getElementById("tab-glider");

  const fillColorPicker = document.getElementById("fill-color");
  const fillColorHex = document.getElementById("fill-color-hex");
  const backColorPicker = document.getElementById("back-color");
  const backColorHex = document.getElementById("back-color-hex");
  const backColorContainer = document.getElementById("back-color-container");
  const transparentBgCheckbox = document.getElementById("transparent-bg");

  const logoInput = document.getElementById("logo-input");
  const fileLabel = document.getElementById("file-label");
  const boxSizeInput = document.getElementById("box-size");
  const rangeValueDisplay = document.getElementById("range-value-display");

  const btnGenerate = document.getElementById("btn-generate");
  const btnText = btnGenerate.querySelector(".btn-text");
  const resultContainer = document.getElementById("result-container");
  const qrImage = document.getElementById("qr-image");
  const downloadBtn = document.getElementById("download-btn");
  const copyBtn = document.getElementById("copy-btn");

  // 1. Mover Glider
  function updateGlider(activeBtn) {
    if (!activeBtn || !tabGlider) return;
    tabGlider.style.left = `${activeBtn.offsetLeft}px`;
    tabGlider.style.width = `${activeBtn.offsetWidth}px`;
  }

  const initialActiveTab = document.querySelector(".tab-btn.active");
  if (initialActiveTab) {
    setTimeout(() => updateGlider(initialActiveTab), 50);
  }

  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const selectedTab = btn.getAttribute("data-tab");

      tabBtns.forEach((b) => b.classList.remove("active"));
      tabPanels.forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      document.getElementById(`panel-${selectedTab}`).classList.add("active");
      qrTypeInput.value = selectedTab;

      updateGlider(btn);
    });
  });

  window.addEventListener("resize", () => {
    const currentActive = document.querySelector(".tab-btn.active");
    if (currentActive) updateGlider(currentActive);
  });

  // 2. Toggle Fundo Transparente na UI
  transparentBgCheckbox.addEventListener("change", () => {
    if (transparentBgCheckbox.checked) {
      backColorContainer.classList.add("disabled");
    } else {
      backColorContainer.classList.remove("disabled");
    }
  });

  // 3. Nome do Arquivo Escolhido
  logoInput.addEventListener("change", () => {
    if (logoInput.files && logoInput.files[0]) {
      fileLabel.textContent = `Logo: ${logoInput.files[0].name}`;
      fileLabel.style.color = "#a5b4fc";
    } else {
      fileLabel.textContent = "Escolher arquivo PNG/JPG...";
      fileLabel.style.color = "var(--text-muted)";
    }
  });

  // 4. Slider de Resolução
  boxSizeInput.addEventListener("input", () => {
    const val = parseInt(boxSizeInput.value);
    if (val < 9) rangeValueDisplay.textContent = `Pequeno (${val}x)`;
    else if (val < 15) rangeValueDisplay.textContent = `Médio (${val}x)`;
    else rangeValueDisplay.textContent = `Alta Resolução (${val}x)`;
  });

  // 5. Parser de HEX
  function parseHex(value) {
    if (!value) return null;
    let clean = value.trim().replace(/[^0-9A-Fa-f]/g, "");

    if (clean.length === 3) {
      clean = clean
        .split("")
        .map((c) => c + c)
        .join("");
    }

    if (clean.length === 6) {
      return `#${clean.toUpperCase()}`;
    }
    return null;
  }

  function setupColorSync(picker, hexInput, defaultColor) {
    picker.addEventListener("input", () => {
      hexInput.value = picker.value.toUpperCase();
    });

    hexInput.addEventListener("input", () => {
      const hex = parseHex(hexInput.value);
      if (hex) picker.value = hex;
    });

    hexInput.addEventListener("blur", () => {
      const hex = parseHex(hexInput.value);
      if (hex) {
        hexInput.value = hex;
        picker.value = hex;
      } else if (!hexInput.value.trim()) {
        hexInput.value = defaultColor;
        picker.value = defaultColor;
      }
    });
  }

  setupColorSync(fillColorPicker, fillColorHex, "#000000");
  setupColorSync(backColorPicker, backColorHex, "#FFFFFF");

  // 6. Copiar Imagem para Clipboard
  copyBtn.addEventListener("click", async () => {
    if (!qrImage.src) return;

    try {
      const response = await fetch(qrImage.src);
      const blob = await response.blob();

      await navigator.clipboard.write([
        new ClipboardItem({ [blob.type]: blob }),
      ]);

      const originalHTML = copyBtn.innerHTML;
      copyBtn.innerHTML = `✓ Copiado!`;
      copyBtn.style.borderColor = "var(--success)";

      setTimeout(() => {
        copyBtn.innerHTML = originalHTML;
        copyBtn.style.borderColor = "var(--card-border)";
      }, 2000);
    } catch (err) {
      console.error("Erro ao copiar:", err);
      alert("Não foi possível copiar a imagem diretamente.");
    }
  });

  // 7. Envio do Formulário
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    btnGenerate.disabled = true;
    btnText.textContent = "Gerando QR Code...";

    const formData = new FormData(form);
    formData.set("fill_color", parseHex(fillColorHex.value) || "#000000");
    formData.set("back_color", parseHex(backColorHex.value) || "#FFFFFF");
    formData.set("transparent_bg", transparentBgCheckbox.checked);

    try {
      const response = await fetch("/api/qr", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (response.ok && data.success) {
        qrImage.src = data.image;
        downloadBtn.href = data.image;

        resultContainer.classList.remove("hidden");
        resultContainer.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });
      } else {
        alert(data.error || "Erro ao gerar o QR Code.");
      }
    } catch (error) {
      console.error("Erro na requisição:", error);
      alert("Ocorreu um erro ao conectar com o servidor.");
    } finally {
      btnGenerate.disabled = false;
      btnText.textContent = "Gerar QR Code";
    }
  });
});
