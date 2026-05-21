// ─────────────────────────────────────────────────────────────
// 1. FEDERATED SIMULATION ENGINE
// ─────────────────────────────────────────────────────────────
document.getElementById('start-btn').addEventListener('click', async () => {
    const btn    = document.getElementById('start-btn');
    const logBox = document.getElementById('console-output');

    btn.disabled  = true;
    btn.innerText = "⏳ Running FL Engine...";
    logBox.innerText = "Connecting to Flask...\nTriggering Flower Simulation Engine...\nWatch your terminal for live loss values!";

    try {
        const res  = await fetch('http://127.0.0.1:5000/run-simulation', { method: 'POST' });
        const data = await res.json();
        logBox.innerText += data.status === "success"
            ? `\n\n✅ ${data.message}`
            : `\n\n❌ ${data.message}`;
    } catch (err) {
        logBox.innerText += `\n\n❌ Network error: ${err.message}`;
    } finally {
        btn.disabled  = false;
        btn.innerText = "🚀 Start Federated Training";
    }
});


// ─────────────────────────────────────────────────────────────
// 2. VCF FILE SELECTED → dim manual inputs
// ─────────────────────────────────────────────────────────────
document.getElementById('vcfFile').addEventListener('change', function () {
    const groups   = ['manual-mutation-group', 'age-input-group', 'weight-input-group'];
    const helpText = document.getElementById('vcf-help-text');

    if (this.files.length > 0) {
        groups.forEach(id => {
            const el = document.getElementById(id);
            if (el) { el.style.opacity = "0.3"; el.style.pointerEvents = "none"; }
        });
        helpText.innerHTML   = `⚡ <strong>Armed:</strong> '${this.files[0].name}' will be fully parsed — age, weight & mutations extracted automatically.`;
        helpText.style.color = "#60a5fa";
        document.getElementById('prediction-result').innerHTML =
            `<span style="color:#64748b">Upload detected — click Calculate to run the genomic analysis.</span>`;
    } else {
        groups.forEach(id => {
            const el = document.getElementById(id);
            if (el) { el.style.opacity = "1"; el.style.pointerEvents = "auto"; }
        });
        helpText.innerHTML   = `💡 Uploading a VCF overrides all manual fields — age, weight & mutations.`;
        helpText.style.color = "#94a3b8";
    }
});


// ─────────────────────────────────────────────────────────────
// 3. DOSAGE PREDICTION FORM SUBMIT
// ─────────────────────────────────────────────────────────────
document.getElementById('predict-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const resultBox  = document.getElementById('prediction-result');
    const predictBtn = document.getElementById('predict-btn');
    const fileInput  = document.getElementById('vcfFile');

    predictBtn.disabled  = true;
    predictBtn.innerText = "⏳ Analysing...";
    resultBox.innerHTML  = `<span style="color:#94a3b8">Running genomic pipeline...</span>`;

    try {
        // ── CASE A: VCF uploaded ──────────────────────────────────────
        if (fileInput && fileInput.files.length > 0) {

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('drug', document.getElementById('drug-select').value);

            const res  = await fetch('http://127.0.0.1:5000/api/predict-vcf-upload', {
                method: 'POST', body: formData
            });
            const data = await res.json();

            if (data.status === 'success') {
                // Reflect auto-parsed values back into the (dimmed) input fields
                document.getElementById('patient-age').value    = data.auto_parsed_age;
                document.getElementById('patient-weight').value = data.auto_parsed_weight;

                // Colour the risk badge
                const riskColor = data.risk_level.includes("CRITICAL") ? "#ef4444"
                                : data.risk_level.includes("Moderate")  ? "#f59e0b"
                                : "#4ade80";

                resultBox.innerHTML = `
                    <!-- Primary: Rule-based CPIC result -->
                    <div style="margin-bottom:12px;">
                        <div style="font-size:11px; text-transform:uppercase; letter-spacing:1px;
                                    color:#64748b; margin-bottom:4px;">
                            📋 CPIC Pharmacogenomic Rule Engine
                        </div>
                        <div style="color:#4ade80; font-size:1.3rem; font-weight:bold;">
                            🎯 ${data.rule_dosage}
                        </div>
                    </div>

                    <!-- Risk & suitability row -->
                    <div style="display:flex; gap:10px; margin-bottom:10px; flex-wrap:wrap;">
                        <span style="background:#1e293b; border:1px solid ${riskColor};
                                     color:${riskColor}; padding:4px 10px; border-radius:20px;
                                     font-size:12px; font-weight:600;">
                            ${data.risk_level}
                        </span>
                        <span style="background:#1e293b; border:1px solid #475569;
                                     color:#94a3b8; padding:4px 10px; border-radius:20px;
                                     font-size:12px;">
                            ${data.suitability}
                        </span>
                    </div>

                    <!-- Clinical notes -->
                    <div style="font-size:13px; color:#cbd5e1; background:#0f172a;
                                padding:10px 12px; border-radius:6px; border-left:3px solid ${riskColor};
                                margin-bottom:10px;">
                        🩺 ${data.clinical_notes}
                    </div>

                    <!-- Detected mutations -->
                    <div style="font-size:12px; color:#94a3b8; background:#1e293b;
                                padding:8px 12px; border-radius:6px; margin-bottom:8px;">
                        🧬 <strong>Auto-Detected Genotypes:</strong><br>
                        <span style="color:#38bdf8; font-family:monospace;">${data.detected_mutations}</span>
                    </div>

                    <!-- Auto-parsed patient metadata -->
                    <div style="font-size:12px; color:#64748b; background:#0f172a;
                                padding:8px 12px; border-radius:6px; margin-bottom:10px;">
                        📋 <strong>Parsed from VCF header →</strong>
                        Age: <span style="color:#38bdf8">${data.auto_parsed_age} yrs</span>
                        &nbsp;|&nbsp;
                        Weight: <span style="color:#38bdf8">${data.auto_parsed_weight} kg</span>
                    </div>

                    <!-- Secondary: ML model comparison -->
                    <div style="font-size:12px; color:#64748b; background:#1e293b;
                                padding:8px 12px; border-radius:6px;
                                border-left:3px solid #334155;">
                        🤖 <strong>Federated ML Model (comparison):</strong>
                        <span style="color:#a78bfa">${data.ml_dosage}</span>
                        <span style="font-size:11px; color:#475569; margin-left:4px;">
                            — improves after running hospital terminals
                        </span>
                    </div>
                `;

            } else {
                resultBox.innerHTML = `<span style="color:#f87171">❌ Engine Error: ${data.message}</span>`;
            }

        // ── CASE B: Manual input (no VCF) ────────────────────────────
        } else {
            const drug     = document.getElementById('drug-select').value;
            const mutation = document.getElementById('gene-mutation').value;
            const age      = document.getElementById('patient-age').value;
            const weight   = document.getElementById('patient-weight').value;

            const res  = await fetch('http://127.0.0.1:5000/predict-dosage', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ drug, mutation, age, weight })
            });
            const data = await res.json();

            resultBox.innerHTML = data.status === "success"
                ? `<span style="color:#4ade80; font-weight:bold;">${data.result}</span>`
                : `<span style="color:#ef4444">❌ ${data.message}</span>`;
        }

    } catch (err) {
        resultBox.innerHTML = `<span style="color:#ef4444">❌ Network Error: Could not reach Flask server.</span>`;
    } finally {
        predictBtn.disabled  = false;
        predictBtn.innerText = "Calculate Optimal Dosage";
    }
});
