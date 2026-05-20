// 🚀 1. FEDERATED SIMULATION ENGINE CONTROLLER
document.getElementById('start-btn').addEventListener('click', async () => {
    const btn    = document.getElementById('start-btn');
    const logBox = document.getElementById('console-output');

    btn.disabled  = true;
    btn.innerText = "⏳ Running FL Engine...";
    logBox.innerText = "Connecting to Flask container...\nTriggering Flower Simulation Engine...\nCheck your taskbar/desktop for the live Matplotlib Plot window!";

    try {
        const response = await fetch('http://127.0.0.1:5000/run-simulation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        logBox.innerText += data.status === "success"
            ? `\n\n✅ Success: ${data.message}`
            : `\n\n❌ Error: ${data.message}`;
    } catch (err) {
        logBox.innerText += `\n\n❌ Network failure: ${err.message}`;
    } finally {
        btn.disabled  = false;
        btn.innerText = "🚀 Start Federated Training";
    }
});


// 🧬 2. VCF FILE SELECTED — hide manual inputs, show auto-parse notice
document.getElementById('vcfFile').addEventListener('change', function () {
    const mutationGroup = document.getElementById('manual-mutation-group');
    const ageGroup      = document.getElementById('age-input-group');
    const weightGroup   = document.getElementById('weight-input-group');
    const helpText      = document.getElementById('vcf-help-text');
    const autoInfo      = document.getElementById('auto-parsed-info');

    if (this.files.length > 0) {
        // Disable and dim the manual fields — they'll be filled from the VCF
        mutationGroup.style.opacity      = "0.3";
        mutationGroup.style.pointerEvents = "none";
        ageGroup.style.opacity           = "0.3";
        ageGroup.style.pointerEvents     = "none";
        weightGroup.style.opacity        = "0.3";
        weightGroup.style.pointerEvents  = "none";

        helpText.innerHTML = `⚡ <strong>Armed:</strong> '${this.files[0].name}' will be fully parsed — age, weight & mutations extracted automatically.`;
        helpText.style.color = "#60a5fa";

        // Clear any previously shown auto-parse results
        if (autoInfo) autoInfo.innerHTML = "";
    } else {
        // Restore manual input mode
        mutationGroup.style.opacity      = "1";
        mutationGroup.style.pointerEvents = "auto";
        ageGroup.style.opacity           = "1";
        ageGroup.style.pointerEvents     = "auto";
        weightGroup.style.opacity        = "1";
        weightGroup.style.pointerEvents  = "auto";

        helpText.innerHTML   = `💡 Uploading a VCF file overrides all manual fields (age, weight, mutations).`;
        helpText.style.color = "#94a3b8";
    }
});


// 🔮 3. CLINICAL DOSAGE PREDICTION CONTROLLER
document.getElementById('predict-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const resultBox = document.getElementById('prediction-result');
    const predictBtn = document.getElementById('predict-btn');
    const fileInput  = document.getElementById('vcfFile');

    const drug   = document.getElementById('drug-select').value;
    const mutation = document.getElementById('gene-mutation').value;
    const age    = document.getElementById('patient-age').value;
    const weight = document.getElementById('patient-weight').value;

    predictBtn.disabled  = true;
    predictBtn.innerText = "⏳ Computing Dosing Matrix...";
    resultBox.innerText  = "Processing pipeline request...";
    resultBox.style.color = "#cbd5e1";

    try {
        // 🧬 CASE A: VCF uploaded → Full auto-parse pipeline (age + weight + mutations from file)
        if (fileInput && fileInput.files.length > 0) {
            console.log("📁 VCF detected — routing to auto-parse engine endpoint...");

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('drug', drug);
            // ✅ We do NOT send age or weight — the backend reads them from the VCF

            const response = await fetch('http://127.0.0.1:5000/api/predict-vcf-upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.status === 'success') {
                // ✅ Show the auto-parsed age/weight back in the input fields so user can see
                if (data.auto_parsed_age !== undefined) {
                    document.getElementById('patient-age').value    = data.auto_parsed_age;
                    document.getElementById('patient-weight').value = data.auto_parsed_weight;
                }

                resultBox.innerHTML = `
                    <div style="color:#4ade80; font-weight:bold; margin-bottom:8px;">
                        🎯 ${data.result}
                    </div>
                    <div style="font-size:13px; color:#94a3b8; background:#1e293b; padding:10px;
                                border-radius:6px; border-left:3px solid #3b82f6; margin-bottom:6px;">
                        🧬 <strong>Auto-Detected Mutations:</strong> ${data.detected_mutations}
                    </div>
                    <div style="font-size:12px; color:#64748b; background:#0f172a; padding:8px;
                                border-radius:4px;">
                        📋 <strong>Auto-Parsed from VCF →</strong>
                        Age: <span style="color:#38bdf8">${data.auto_parsed_age} yrs</span> &nbsp;|&nbsp;
                        Weight: <span style="color:#38bdf8">${data.auto_parsed_weight} kg</span>
                    </div>
                `;
            } else {
                resultBox.innerHTML = `<span style="color:#f87171">❌ Engine Error: ${data.message}</span>`;
            }

        // 📋 CASE B: No file → Manual input fallback
        } else {
            const response = await fetch('http://127.0.0.1:5000/predict-dosage', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ drug, mutation, age, weight })
            });
            const data = await response.json();

            if (data.status === "success") {
                resultBox.innerHTML = `<span style="color:#4ade80; font-weight:bold;">${data.result}</span>`;
            } else {
                resultBox.innerHTML = `<span style="color:#ef4444">❌ Error: ${data.message}</span>`;
            }
        }
    } catch (err) {
        resultBox.innerHTML = `<span style="color:#ef4444">❌ Network Error: Could not reach Flask server.</span>`;
    } finally {
        predictBtn.disabled  = false;
        predictBtn.innerText = "Calculate Optimal Dosage";
    }
});
