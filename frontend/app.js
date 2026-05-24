// ─────────────────────────────────────────────────────────────
// GENIDOSE FRONTEND CONTROLLER
// ─────────────────────────────────────────────────────────────

// Stores last successful backend response for PDF generation
let lastResult = null;


// ─────────────────────────────────────────────────────────────
// 1. FEDERATED LEARNING SIMULATION
// ─────────────────────────────────────────────────────────────
document.getElementById('start-btn').addEventListener('click', async () => {

    const btn    = document.getElementById('start-btn');
    const logBox = document.getElementById('console-output');

    btn.disabled  = true;
    btn.innerText = "⏳ Running FL Engine...";

    logBox.innerText =
        "Connecting to Flask...\n" +
        "Triggering Flower Simulation Engine...\n" +
        "Watch terminal for live training logs...\n";

    try {

        const res = await fetch('http://127.0.0.1:5000/run-simulation', {
            method: 'POST'
        });

        const data = await res.json();

        if (data.status === "success") {
            logBox.innerText += `\n✅ ${data.message}`;
        } else {
            logBox.innerText += `\n❌ ${data.message}`;
        }

    } catch (err) {

        logBox.innerText += `\n❌ Network Error: ${err.message}`;

    } finally {

        btn.disabled  = false;
        btn.innerText = "🚀 Start Federated Training";
    }
});


// ─────────────────────────────────────────────────────────────
// 2. VCF FILE SELECTED
// ─────────────────────────────────────────────────────────────
document.getElementById('vcfFile').addEventListener('change', function () {

    const groups = [
        'manual-mutation-group',
        'age-input-group',
        'weight-input-group'
    ];

    const helpText = document.getElementById('vcf-help-text');

    if (this.files.length > 0) {

        groups.forEach(id => {
            const el = document.getElementById(id);

            if (el) {
                el.style.opacity = "0.3";
                el.style.pointerEvents = "none";
            }
        });

        helpText.innerHTML =
            `⚡ <strong>VCF Detected:</strong> '${this.files[0].name}' will be fully parsed automatically.`;

        helpText.style.color = "#60a5fa";

        document.getElementById('prediction-result').innerHTML =
            `<span style="color:#64748b">
                Upload detected — click Calculate to begin genomic analysis.
            </span>`;

    } else {

        groups.forEach(id => {

            const el = document.getElementById(id);

            if (el) {
                el.style.opacity = "1";
                el.style.pointerEvents = "auto";
            }
        });

        helpText.innerHTML =
            `💡 Uploading a VCF overrides manual age, weight & mutation fields.`;

        helpText.style.color = "#94a3b8";
    }
});


// ─────────────────────────────────────────────────────────────
// 3. MAIN DOSAGE PREDICTION
// ─────────────────────────────────────────────────────────────
document.getElementById('predict-form').addEventListener('submit', async (e) => {

    e.preventDefault();

    const resultBox  = document.getElementById('prediction-result');
    const predictBtn = document.getElementById('predict-btn');
    const fileInput  = document.getElementById('vcfFile');

    predictBtn.disabled  = true;
    predictBtn.innerText = "⏳ Analysing...";

    resultBox.innerHTML =
        `<span style="color:#94a3b8">
            Running pharmacogenomic pipeline...
        </span>`;

    try {

        // ─────────────────────────────────────────────
        // CASE A — VCF Upload Mode
        // ─────────────────────────────────────────────
        if (fileInput && fileInput.files.length > 0) {

            const formData = new FormData();

            formData.append('file', fileInput.files[0]);
            formData.append(
                'drug',
                document.getElementById('drug-select').value
            );

            const res = await fetch(
                'http://127.0.0.1:5000/api/predict-vcf-upload',
                {
                    method: 'POST',
                    body: formData
                }
            );

            const data = await res.json();

            if (data.status === 'success') {

                // Save for PDF generation
                lastResult = data;

                // Reflect parsed values into disabled inputs
                document.getElementById('patient-age').value =
                    data.auto_parsed_age;

                document.getElementById('patient-weight').value =
                    data.auto_parsed_weight;

                // Risk color logic
                let riskColor = "#4ade80";

                if (data.risk_level.toUpperCase().includes("CRITICAL")) {
                    riskColor = "#ef4444";
                }
                else if (
                    data.risk_level.toUpperCase().includes("HIGH") ||
                    data.risk_level.toUpperCase().includes("MODERATE")
                ) {
                    riskColor = "#f59e0b";
                }

                // Render result card
                resultBox.innerHTML = `

                    <!-- CPIC Result -->
                    <div style="margin-bottom:12px;">

                        <div style="
                            font-size:11px;
                            text-transform:uppercase;
                            letter-spacing:1px;
                            color:#64748b;
                            margin-bottom:4px;
                        ">
                            📋 CPIC Pharmacogenomic Rule Engine
                        </div>

                        <div style="
                            color:#4ade80;
                            font-size:1.35rem;
                            font-weight:bold;
                        ">
                            🎯 ${data.rule_dosage}
                        </div>

                    </div>


                    <!-- Risk -->
                    <div style="
                        display:flex;
                        gap:10px;
                        margin-bottom:10px;
                        flex-wrap:wrap;
                    ">

                        <span style="
                            background:#1e293b;
                            border:1px solid ${riskColor};
                            color:${riskColor};
                            padding:4px 10px;
                            border-radius:20px;
                            font-size:12px;
                            font-weight:600;
                        ">
                            ${data.risk_level}
                        </span>

                        <span style="
                            background:#1e293b;
                            border:1px solid #475569;
                            color:#94a3b8;
                            padding:4px 10px;
                            border-radius:20px;
                            font-size:12px;
                        ">
                            ${data.suitability}
                        </span>

                    </div>


                    <!-- Clinical Notes -->
                    <div style="
                        font-size:13px;
                        color:#cbd5e1;
                        background:#0f172a;
                        padding:10px 12px;
                        border-radius:6px;
                        border-left:3px solid ${riskColor};
                        margin-bottom:10px;
                    ">
                        🩺 ${data.clinical_notes}
                    </div>


                    <!-- Genotypes -->
                    <div style="
                        font-size:12px;
                        color:#94a3b8;
                        background:#1e293b;
                        padding:8px 12px;
                        border-radius:6px;
                        margin-bottom:8px;
                    ">

                        🧬 <strong>Auto-Detected Genotypes:</strong><br>

                        <span style="
                            color:#38bdf8;
                            font-family:monospace;
                        ">
                            ${data.detected_mutations}
                        </span>

                    </div>


                    <!-- Parsed Metadata -->
                    <div style="
                        font-size:12px;
                        color:#64748b;
                        background:#0f172a;
                        padding:8px 12px;
                        border-radius:6px;
                        margin-bottom:10px;
                    ">

                        📋 <strong>Parsed from VCF →</strong>

                        Age:
                        <span style="color:#38bdf8">
                            ${data.auto_parsed_age} yrs
                        </span>

                        &nbsp;|&nbsp;

                        Weight:
                        <span style="color:#38bdf8">
                            ${data.auto_parsed_weight} kg
                        </span>

                    </div>


                    <!-- FL Model -->
                    <div style="
                        font-size:12px;
                        color:#64748b;
                        background:#1e293b;
                        padding:8px 12px;
                        border-radius:6px;
                        border-left:3px solid #334155;
                        margin-bottom:14px;
                    ">

                        🤖 <strong>Federated ML Model:</strong>

                        <span style="color:#a78bfa">
                            ${data.ml_dosage}
                        </span>

                    </div>


                    <!-- PDF Button -->
                    <button id="downloadBtn"
                        style="
                            width:100%;
                            padding:10px;
                            background:#0ea5c9;
                            color:#fff;
                            border:none;
                            border-radius:8px;
                            font-size:13px;
                            font-weight:600;
                            cursor:pointer;
                            letter-spacing:0.5px;
                        ">
                        ⬇ Download Clinical Report (PDF)
                    </button>
                `;

                // Attach PDF event
                const downloadBtn = document.getElementById('downloadBtn');

                downloadBtn.addEventListener('click', async () => {

                    downloadBtn.disabled  = true;
                    downloadBtn.innerText = "⏳ Generating PDF...";

                    try {

                        const res = await fetch(
                            'http://127.0.0.1:5000/download_report',
                            {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify(lastResult)
                            }
                        );

                        const blob = await res.blob();

                        const url = window.URL.createObjectURL(blob);

                        const a = document.createElement('a');

                        a.href = url;
                        a.download = 'genidose_report.pdf';

                        document.body.appendChild(a);

                        a.click();

                        a.remove();

                        window.URL.revokeObjectURL(url);

                    } catch (err) {

                        alert("PDF generation failed: " + err.message);

                    } finally {

                        downloadBtn.disabled  = false;
                        downloadBtn.innerText =
                            "⬇ Download Clinical Report (PDF)";
                    }
                });

            } else {

                resultBox.innerHTML =
                    `<span style="color:#f87171">
                        ❌ Engine Error: ${data.message}
                    </span>`;
            }

        }

        // ─────────────────────────────────────────────
        // CASE B — Manual Entry Mode
        // ─────────────────────────────────────────────
        else {

            const drug     = document.getElementById('drug-select').value;
            const mutation = document.getElementById('gene-mutation').value;
            const age      = document.getElementById('patient-age').value;
            const weight   = document.getElementById('patient-weight').value;

            const res = await fetch(
                'http://127.0.0.1:5000/predict-dosage',
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        drug,
                        mutation,
                        age,
                        weight
                    })
                }
            );

            const data = await res.json();

            if (data.status === "success") {

                resultBox.innerHTML =
                    `<span style="color:#4ade80; font-weight:bold;">
                        ${data.result}
                    </span>`;

            } else {

                resultBox.innerHTML =
                    `<span style="color:#ef4444">
                        ❌ ${data.message}
                    </span>`;
            }
        }

    } catch (err) {

        resultBox.innerHTML =
            `<span style="color:#ef4444">
                ❌ Network Error: Could not reach Flask server.
            </span>`;

    } finally {

        predictBtn.disabled  = false;
        predictBtn.innerText = "Calculate Optimal Dosage";
    }
});